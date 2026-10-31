"""Testes da extração do Ibovespa (sem acessar a internet)."""

from datetime import date

import pandas as pd
import pytest

from src.extract_ibovespa import baixar_ibovespa


def tabela_yahoo(datas, fechamentos, volumes):
    """Monta uma tabela no mesmo formato que o yfinance devolveu no teste real."""
    indice = pd.DatetimeIndex(datas, name="Date").tz_localize("America/Sao_Paulo")
    return pd.DataFrame(
        {
            "Open": fechamentos,
            "High": fechamentos,
            "Low": fechamentos,
            "Close": fechamentos,
            "Volume": volumes,
            "Dividends": 0.0,
            "Stock Splits": 0.0,
        },
        index=indice,
    )


def instalar_ticker_falso(monkeypatch, respostas):
    """Troca o yf.Ticker por um falso que devolve `respostas`, uma por chamada.

    Cada item da lista é uma tabela (resposta normal) ou uma exceção (falha).
    Depois do último item, a última resposta se repete.
    Devolve a lista de chamadas feitas, para os testes inspecionarem.
    """
    chamadas = []

    class TickerFalso:
        def __init__(self, simbolo):
            self.simbolo = simbolo

        def history(self, **parametros):
            chamadas.append(parametros)
            resposta = respostas[min(len(chamadas) - 1, len(respostas) - 1)]
            if isinstance(resposta, Exception):
                raise resposta
            return resposta

    monkeypatch.setattr("src.extract_ibovespa.yf.Ticker", TickerFalso)
    return chamadas


def test_devolve_data_fechamento_e_volume(monkeypatch):
    tabela = tabela_yahoo(["2026-10-28", "2026-10-29"], [170000.0, 171000.0], [100, 200])
    instalar_ticker_falso(monkeypatch, [tabela])

    resultado = baixar_ibovespa(date(2026, 10, 28), date(2026, 10, 29))

    assert list(resultado.columns) == ["data", "fechamento", "volume"]
    assert resultado["fechamento"].tolist() == [170000.0, 171000.0]
    assert resultado["volume"].tolist() == [100, 200]


def test_data_final_entra_na_consulta_somando_um_dia(monkeypatch):
    tabela = tabela_yahoo(["2026-10-29"], [170000.0], [100])
    chamadas = instalar_ticker_falso(monkeypatch, [tabela])

    baixar_ibovespa(date(2026, 10, 1), date(2026, 10, 29))

    assert chamadas[0]["start"] == "2026-10-01"
    assert chamadas[0]["end"] == "2026-10-30"  # `end` é exclusivo no yfinance


def test_tenta_novamente_apos_falha_temporaria(monkeypatch):
    monkeypatch.setattr("src.extract_ibovespa.time.sleep", lambda segundos: None)
    tabela = tabela_yahoo(["2026-10-29"], [170000.0], [100])
    chamadas = instalar_ticker_falso(monkeypatch, [ConnectionError("falha"), tabela])

    resultado = baixar_ibovespa(date(2026, 10, 1), date(2026, 10, 29))

    assert len(chamadas) == 2
    assert len(resultado) == 1


def test_tabela_vazia_e_tratada_como_falha(monkeypatch):
    monkeypatch.setattr("src.extract_ibovespa.time.sleep", lambda segundos: None)
    chamadas = instalar_ticker_falso(monkeypatch, [tabela_yahoo([], [], [])])

    with pytest.raises(RuntimeError):
        baixar_ibovespa(date(2026, 10, 1), date(2026, 10, 29), tentativas=3)
    assert len(chamadas) == 3


def test_data_inicial_posterior_a_final_e_recusada():
    with pytest.raises(ValueError):
        baixar_ibovespa(date(2026, 2, 1), date(2026, 1, 1))



