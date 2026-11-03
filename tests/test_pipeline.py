from datetime import date

import pandas as pd
import pytest

from src import load, pipeline

HOJE = date(2026, 11, 3)


def _sgs_falso(codigo, data_inicial, data_final, **_):
    """Imita baixar_serie_sgs; devolve texto, como a API."""
    if codigo == 433:  # IPCA mensal, dia 1
        return pd.DataFrame({"data": ["01/09/2026", "01/10/2026"], "valor": ["0.48", "0.30"]})
    return pd.DataFrame({"data": ["30/10/2026", "03/11/2026"], "valor": ["1.5", "1.6"]})


def _ibov_falso(data_inicial, data_final, **_):
    datas = pd.to_datetime(["2026-10-30", "2026-11-03"]).tz_localize("America/Sao_Paulo")
    return pd.DataFrame(
        {"data": datas, "fechamento": [205000.0, 206000.0], "volume": [9_000_000, 0]}
    )


@pytest.fixture
def falsos(monkeypatch):
    chamadas = {"sgs": [], "ibov": []}

    def sgs(codigo, ini, fim, **k):
        chamadas["sgs"].append((codigo, ini, fim))
        return _sgs_falso(codigo, ini, fim)

    def ibov(ini, fim, **k):
        chamadas["ibov"].append((ini, fim))
        return _ibov_falso(ini, fim)

    monkeypatch.setattr(pipeline, "baixar_serie_sgs", sgs)
    monkeypatch.setattr(pipeline, "baixar_ibovespa", ibov)
    return chamadas


@pytest.fixture
def conn():
    c = load.conectar(":memory:")
    yield c
    c.close()


def test_fluxo_completo_grava_tudo(conn, falsos):
    resumo = pipeline.executar(conn, hoje=HOJE)
    assert set(resumo) == {"cdi", "ipca", "dolar_ptax", "ibovespa"}
    assert resumo["cdi"]["linhas"] == 2
    assert resumo["ibovespa"]["ultima_data"] == date(2026, 11, 3)
    assert resumo["ipca"]["ultima_data"] == date(2026, 10, 1)
    assert load.ler_ultima_execucao(conn) is not None
    ibov = load.ler_tabela(conn, "ibovespa")
    assert ibov["parcial"].tolist() == [False, True]
    assert ibov["volume"].isna().tolist() == [False, True]  # volume 0 -> NULL


def test_cdi_e_ipca_pedem_um_ano_a_mais(conn, falsos):
    pipeline.executar(conn, hoje=HOJE)
    inicios = {codigo: ini for codigo, ini, _ in falsos["sgs"]}
    assert inicios[12] == date(2020, 11, 3)  # CDI: 6 anos
    assert inicios[433] == date(2020, 11, 3)  # IPCA: 6 anos
    assert inicios[1] == date(2021, 11, 3)  # dólar: 5 anos
    assert falsos["ibov"][0][0] == date(2021, 11, 3)  # Ibovespa: 5 anos


def test_rodar_duas_vezes_nao_duplica(conn, falsos):
    pipeline.executar(conn, hoje=HOJE)
    pipeline.executar(conn, hoje=HOJE)
    assert len(load.ler_tabela(conn, "cdi")) == 2
    assert len(load.ler_tabela(conn, "ibovespa")) == 2


def test_falha_numa_fonte_nao_grava_nada(conn, monkeypatch, falsos):
    def quebra(*a, **k):
        raise RuntimeError("Yahoo fora do ar")

    monkeypatch.setattr(pipeline, "baixar_ibovespa", quebra)
    with pytest.raises(RuntimeError):
        pipeline.executar(conn, hoje=HOJE)
    for tabela in load.TABELAS:
        assert load.ler_tabela(conn, tabela).empty  # nem o CDI (já baixado) foi gravado
    assert load.ler_ultima_execucao(conn) is None


def test_conexao_recebida_nao_e_fechada(conn, falsos):
    pipeline.executar(conn, hoje=HOJE)
    conn.execute("SELECT 1")  # se estivesse fechada, daria erro


def test_main_sucesso_devolve_0(monkeypatch, capsys):
    monkeypatch.setattr(
        pipeline, "executar", lambda: {"cdi": {"linhas": 2, "ultima_data": date(2026, 11, 3)}}
    )
    assert pipeline.main() == 0
    assert "cdi" in capsys.readouterr().out


def test_main_falha_devolve_1_e_explica(monkeypatch, capsys):
    def quebra():
        raise RuntimeError("API fora do ar")

    monkeypatch.setattr(pipeline, "executar", quebra)
    assert pipeline.main() == 1
    assert "API fora do ar" in capsys.readouterr().out