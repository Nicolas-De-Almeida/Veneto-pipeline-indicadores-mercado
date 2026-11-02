from datetime import date, datetime

import pandas as pd
import pytest

from src import load
from src.transform import converter_serie_sgs, tratar_ibovespa


@pytest.fixture
def conn():
    c = load.connectar(":memory:")
    load.criar_tabelas(c)
    yield c
    c.close()


def _cdi():
    return pd.DataFrame(
        {"data": pd.to_datetime(["2026-10-28", "2026-10-29"]), "cdi": [0.050788, 0.050788]}
    )


def _ibov():
    return pd.DataFrame(
        {
            "data": pd.to_datetime(["2026-10-29", "2026-10-30"]),
            "fechamento": [204000.0, 167921.796875],
            "volume": pd.array([8_000_000, pd.NA], dtype="Int64"),
            "parcial": [False, True],
            "divergente": [False, False],
        }
    )


def test_criar_tabelas_e_idempotente(conn):
    load.criar_tabelas(conn)  # segunda vez não pode dar erro
    nomes = {l[0] for l in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"cdi", "ipca", "dolar_ptax", "ibovespa", "metadados"} <= nomes



def test_salvar_e_ler_serie_sgs(conn):
    assert load.salvar_serie_sgs(conn, "cdi", _cdi(), "cdi") == 2
    r = load.ler_tabela(conn, "cdi")
    assert list(r["data"]) == list(pd.to_datetime(["2026-10-28", "2026-10-29"]))
    assert r["valor"].iloc[0] == pytest.approx(0.050788)
 

def test_salvar_duas_vezes_nao_duplica(conn):
    load.salvar_serie_sgs(conn, "cdi", _cdi(), "cdi")
    load.salvar_serie_sgs(conn, "cdi", _cdi(), "cdi")
    assert len(load.ler_tabela(conn, "cdi")) == 2


def test_salvar_atualiza_valor_de_data_existente(conn):
    load.salvar_serie_sgs(conn, "cdi", _cdi(), "cdi")
    novo = _cdi().iloc[:1].copy()
    novo["cdi"] = 0.1
    load.salvar_serie_sgs(conn, "cdi", novo, "cdi")
    r = load.ler_tabela(conn, "cdi")
    assert len(r) == 2 and r["valor"].iloc[0] == pytest.approx(0.1)


def test_tabela_invalida_gera_erro(conn):
    with pytest.raises(ValueError):
        load.salvar_serie_sgs(conn, "cdi; DROP TABLE cdi", _cdi(), "cdi")
    with pytest.raises(ValueError):
        load.ler_tabela(conn, "ibovespa_errado")


def test_serie_vazia_ou_com_nulo_gera_erro(conn):
    with pytest.raises(ValueError):
        load.salvar_serie_sgs(conn, "cdi", _cdi().iloc[0:0], "cdi")
    ruim = _cdi()
    ruim.loc[0, "cdi"] = float("nan")
    with pytest.raises(ValueError):
        load.salvar_serie_sgs(conn, "cdi", ruim, "cdi")


def test_ibovespa_volume_vazio_vira_null_e_volta_como_na(conn):
    load.salvar_ibovespa(conn, _ibov())
    bruto = conn.execute("SELECT volume FROM ibovespa ORDER BY data").fetchall()
    assert bruto == [(8_000_000,), (None,)]  # NULL de verdade no banco
    r = load.ler_tabela(conn, "ibovespa")
    assert r["volume"].isna().tolist() == [False, True]


def test_ibovespa_flags_ida_e_volta(conn):
    load.salvar_ibovespa(conn, _ibov())
    r = load.ler_tabela(conn, "ibovespa")
    assert r["parcial"].tolist() == [False, True]
    assert r["divergente"].tolist() == [False, False]
    assert r["parcial"].dtype == bool


def test_ibovespa_vazio_ou_sem_fechamento_gera_erro(conn):
    with pytest.raises(ValueError):
        load.salvar_ibovespa(conn, _ibov().iloc[0:0])
    ruim = _ibov()
    ruim.loc[0, "fechamento"] = float("nan")
    with pytest.raises(ValueError):
        load.salvar_ibovespa(conn, ruim)


def test_ultima_data(conn):
    assert load.ultima_data(conn, "cdi") is None
    load.salvar_serie_sgs(conn, "cdi", _cdi(), "cdi")
    assert load.ultima_data(conn, "cdi") == pd.Timestamp("2026-10-29")


def test_execucao_registrada(conn):
    assert load.ler_ultima_execucao(conn) is None
    load.registrar_execucao(conn, datetime(2026, 11, 3, 15, 30, 5))
    assert load.ler_ultima_execucao(conn) == datetime(2026, 11, 3, 15, 30, 5)
    load.registrar_execucao(conn, datetime(2026, 11, 4, 9, 0, 0))  # sobrescreve
    assert load.ler_ultima_execucao(conn) == datetime(2026, 11, 4, 9, 0, 0)


def test_connectar_cria_pasta_e_arquivo(tmp_path):
    caminho = tmp_path / "subpasta" / "teste.db"
    c = load.connectar(caminho)
    load.criar_tabelas(c)
    c.close()
    assert caminho.exists()


def test_fluxo_transform_para_load_para_leitura(conn):
    """Do dado bruto (texto) até ler de volta do banco."""
    bruto = pd.DataFrame({"data": ["28/10/2026", "29/10/2026"], "valor": ["0.050788", "0.050788"]})
    load.salvar_serie_sgs(conn, "cdi", converter_serie_sgs(bruto, "cdi"), "cdi")
    ibov = pd.DataFrame(
        {
            "data": pd.to_datetime(["2026-10-30"]).tz_localize("America/Sao_Paulo"),
            "fechamento": [167921.796875],
            "volume": [0],
        }
    )
    load.salvar_ibovespa(conn, tratar_ibovespa(ibov, hoje=date(2026, 10, 30)))
    r = load.ler_tabela(conn, "ibovespa")
    assert r["parcial"].iloc[0] and r["volume"].isna().iloc[0]
    assert len(load.ler_tabela(conn, "cdi")) == 2