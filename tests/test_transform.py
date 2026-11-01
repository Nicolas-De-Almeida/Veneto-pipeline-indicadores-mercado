from datetime import date

import pandas as pd
import pytest

from src.transform import converter_serie_sgs, tratar_ibovespa


def _sgs(linhas):
    return pd.DataFrame(linhas, columns=["data", "valor"])


def test_sgs_converte_data_e_valor():
    r = converter_serie_sgs(_sgs([["28/10/2026", "0.050788"]]), "cdi")
    assert r["data"].iloc[0] == pd.Timestamp(2026, 10, 28)
    assert r["cdi"].iloc[0] == pytest.approx(0.050788)
    assert r["cdi"].dtype == float


def test_sgs_data_dia_mes_nao_se_confunde():
    # 03/11 deve ser 3 de novembro, não 11 de março
    r = converter_serie_sgs(_sgs([["03/11/2026", "1"]]))
    assert r["data"].iloc[0] == pd.Timestamp(2026, 11, 3)


def test_sgs_ordena_e_remove_duplicadas_mantendo_ultima():
    r = converter_serie_sgs(_sgs([["02/01/2026", "2"], ["01/01/2026", "1"], ["02/01/2026", "3"]]))
    assert list(r["valor"]) == [1.0, 3.0]
    assert list(r.index) == [0, 1]


def test_sgs_vazia_gera_erro():
    with pytest.raises(ValueError):
        converter_serie_sgs(pd.DataFrame(columns=["data", "valor"]))


def test_sgs_valor_invalido_gera_erro():
    with pytest.raises(ValueError):
        converter_serie_sgs(_sgs([["01/01/2026", "abc"]]))


def test_sgs_valor_vazio_gera_erro():
    with pytest.raises(ValueError):
        converter_serie_sgs(_sgs([["01/01/2026", ""]]))


def test_sgs_data_invalida_gera_erro():
    with pytest.raises(ValueError):
        converter_serie_sgs(_sgs([["31/02/2026", "1"]]))


def test_sgs_sem_colunas_esperadas_gera_erro():
    with pytest.raises(ValueError):
        converter_serie_sgs(pd.DataFrame({"x": [1]}))


def _ibov():
    datas = pd.to_datetime(
        ["2026-10-28", "2026-10-29", "2026-10-30"]
    ).tz_localize("America/Sao_Paulo")
    return pd.DataFrame(
        {
            "data": datas,
            "fechamento": [205000.0, 204000.0, 167921.796875],
            "volume": [9_000_000, 8_000_000, 0],
        }
    )


def test_ibov_remove_fuso_sem_mudar_o_dia():
    r = tratar_ibovespa(_ibov(), hoje=date(2026, 11, 5))
    assert r["data"].dt.tz is None
    assert list(r["data"].dt.date) == [date(2026, 10, 28), date(2026, 10, 29), date(2026, 10, 30)]


def test_ibov_volume_zero_vira_vazio():
    r = tratar_ibovespa(_ibov(), hoje=date(2026, 11, 5))
    assert r["volume"].isna().tolist() == [False, False, True]
    assert r["volume"].iloc[0] == 9_000_000


def test_ibov_marca_parcial_so_no_dia_de_hoje():
    r = tratar_ibovespa(_ibov(), hoje=date(2026, 10, 30))
    assert r["parcial"].tolist() == [False, False, True]


def test_ibov_marca_divergente_pelo_dicionario():
    r = tratar_ibovespa(_ibov(), hoje=date(2026, 11, 5), dias_divergentes={date(2026, 10, 29): 1.0})
    assert r["divergente"].tolist() == [False, True, False]
    assert r["fechamento"].iloc[1] == 204000.0  # valor original mantido


def test_ibov_divergencia_padrao_vem_do_config():
    bruto = pd.DataFrame(
        {
            "data": pd.to_datetime(["2023-11-10"]).tz_localize("America/Sao_Paulo"),
            "fechamento": [120568.0],
            "volume": [1],
        }
    )
    assert tratar_ibovespa(bruto, hoje=date(2026, 11, 5))["divergente"].iloc[0]


def test_ibov_remove_fechamento_nulo():
    bruto = _ibov()
    bruto.loc[1, "fechamento"] = float("nan")
    r = tratar_ibovespa(bruto, hoje=date(2026, 11, 5))
    assert len(r) == 2


def test_ibov_vazia_gera_erro():
    with pytest.raises(ValueError):
        tratar_ibovespa(pd.DataFrame(columns=["data", "fechamento", "volume"]))


def test_ibov_colunas_faltando_gera_erro():
    with pytest.raises(ValueError):
        tratar_ibovespa(pd.DataFrame({"data": [1]}))