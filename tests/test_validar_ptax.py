"""Testes das funções auxiliares da validação da PTAX (sem internet)."""

from datetime import date

import pandas as pd
import pytest

from scripts.validar_ptax import buscar_sgs, data_para_formato_ptax, valores_batem



def test_data_para_formato_ptax_troca_dia_e_mes():
    assert data_para_formato_ptax("15/03/2023") == "03-15-2023"


def test_valores_iguais_batem():
    assert valores_batem(5.5007, 5.50070)


def test_diferenca_de_arredondamento_e_aceita():
    assert valores_batem(5.5007, 5.50072)


def test_valores_diferentes_nao_batem():
    assert not valores_batem(5.5007, 5.5113)


def test_buscar_sgs_pede_janela_de_dois_dias_e_filtra_a_data(monkeypatch):
    pedidos = []

    def baixar_falso(codigo, data_inicial, data_final):
        pedidos.append((data_inicial, data_final))
        return pd.DataFrame(
            [
                {"data": "25/10/2026", "valor": "5.4000"},
                {"data": "26/10/2026", "valor": "5.5007"},
            ]
        )

    monkeypatch.setattr("scripts.validar_ptax.baixar_serie_sgs", baixar_falso)

    assert buscar_sgs("26/10/2026") == 5.5007
    assert pedidos == [(date(2026, 10, 25), date(2026, 10, 26))]


def test_buscar_sgs_sem_valor_na_data_levanta_erro(monkeypatch):
    monkeypatch.setattr(
        "scripts.validar_ptax.baixar_serie_sgs",
        lambda codigo, inicio, fim: pd.DataFrame([{"data": "25/10/2026", "valor": "5.4"}]),
    )
    with pytest.raises(ValueError):
        buscar_sgs("26/10/2026")