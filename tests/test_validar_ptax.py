"""Testes das funções auxiliares da validação da PTAX (sem internet)."""

from scripts.validar_ptax import data_para_formato_ptax, valores_batem


def test_data_para_formato_ptax_troca_dia_e_mes():
    assert data_para_formato_ptax("15/03/2023") == "03-15-2023"


def test_valores_iguais_batem():
    assert valores_batem(5.5007, 5.50070)


def test_diferenca_de_arredondamento_e_aceita():
    assert valores_batem(5.5007, 5.50072)


def test_valores_diferentes_nao_batem():
    assert not valores_batem(5.5007, 5.5113)