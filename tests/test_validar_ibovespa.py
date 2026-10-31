"""Testes das funções auxiliares da validação do Ibovespa (sem internet)."""

from datetime import date

import pandas as pd

from scripts.validar_ibovespa import comparar, valores_batem


def tabela_exemplo():
    """Tabela no mesmo formato que o extrator devolve (data com fuso horário)."""
    datas = pd.DatetimeIndex(["2026-10-08", "2026-10-09"]).tz_localize("America/Sao_Paulo")
    return pd.DataFrame({"data": datas, "fechamento": [206220.0, 209067.0], "volume": [1, 1]})


def test_arredondamento_menor_que_um_ponto_e_aceito():
    assert valores_batem(206220.0, 206220.24)
    assert valores_batem(209067.0, 209066.90)


def test_diferenca_de_um_ponto_ou_mais_nao_bate():
    assert not valores_batem(206220.0, 206221.5)


def test_comparar_marca_iguais_e_diferentes():
    referencias = {date(2026, 10, 8): 206220.24, date(2026, 10, 9): 209100.00}
    resultado = comparar(tabela_exemplo(), referencias)
    assert [linha[3] for linha in resultado] == [True, False]


def test_comparar_data_ausente_nao_bate():
    resultado = comparar(tabela_exemplo(), {date(2026, 10, 10): 1.0})
    assert resultado == [(date(2026, 10, 10), None, 1.0, False)]