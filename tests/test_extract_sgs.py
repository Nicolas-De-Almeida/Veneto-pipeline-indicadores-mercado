"""Testes da extração do SGS (sem acessar a internet)."""

from datetime import date

import pytest
import requests

from src.extract_sgs import baixar_serie_sgs, calcular_periodo, montar_parametros


class RespostaFalsa:
    """Imita a resposta do `requests` com os dados que quisermos."""

    def __init__(self, dados, status=200):
        self._dados = dados
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._dados


def test_montar_parametros_usa_formato_de_data_da_api():
    params = montar_parametros(date(2026, 1, 5), date(2026, 10, 29))
    assert params == {
        "formato": "json",
        "dataInicial": "05/01/2026",
        "dataFinal": "29/10/2026",
    }


def test_calcular_periodo_cobre_cinco_anos():
    inicio, fim = calcular_periodo(date(2026, 10, 29), anos=5)
    assert inicio == date(2021, 10, 29)
    assert fim == date(2026, 10, 29)


def test_baixar_serie_devolve_dados_brutos(monkeypatch):
    dados = [{"data": "27/10/2026", "valor": "0.050788"}]
    monkeypatch.setattr(
        "src.extract_sgs.requests.get",
        lambda url, params=None, timeout=None: RespostaFalsa(dados),
    )
    df = baixar_serie_sgs(12, date(2026, 10, 1), date(2026, 10, 28))
    assert list(df.columns) == ["data", "valor"]
    assert df.loc[0, "valor"] == "0.050788"  # ainda texto: a conversão é na etapa T


def test_tenta_novamente_apos_falha_temporaria(monkeypatch):
    chamadas = []

    def get_falso(url, params=None, timeout=None):
        chamadas.append(1)
        if len(chamadas) == 1:
            raise requests.ConnectionError("falha temporária")
        return RespostaFalsa([{"data": "02/01/2026", "valor": "0.05"}])

    monkeypatch.setattr("src.extract_sgs.requests.get", get_falso)
    monkeypatch.setattr("src.extract_sgs.time.sleep", lambda segundos: None)

    df = baixar_serie_sgs(12, date(2026, 1, 1), date(2026, 1, 31))
    assert len(chamadas) == 2
    assert len(df) == 1


def test_falha_definitiva_levanta_erro_claro(monkeypatch):
    chamadas = []

    def get_falso(url, params=None, timeout=None):
        chamadas.append(1)
        return RespostaFalsa([], status=500)

    monkeypatch.setattr("src.extract_sgs.requests.get", get_falso)
    monkeypatch.setattr("src.extract_sgs.time.sleep", lambda segundos: None)

    with pytest.raises(RuntimeError):
        baixar_serie_sgs(12, date(2026, 1, 1), date(2026, 1, 31), tentativas=3)
    assert len(chamadas) == 3


def test_janela_maior_que_dez_anos_e_recusada():
    with pytest.raises(ValueError):
        baixar_serie_sgs(1, date(2010, 1, 1), date(2026, 1, 1))


def test_data_inicial_posterior_a_final_e_recusada():
    with pytest.raises(ValueError):
        baixar_serie_sgs(1, date(2026, 2, 1), date(2026, 1, 1))