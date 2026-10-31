"""Extração (E) do Ibovespa via yfinance (dados do Yahoo Finance)."""

import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from src.config import TICKER_IBOVESPA


def _selecionar_colunas(tabela: pd.DataFrame) -> pd.DataFrame:
    """Fica só com data, fechamento e volume, com nomes em português.
    Mantemos o volume porque ele ajuda a identificar dias incompletos
    (volume zero) na etapa de transformação.
    """
    return pd.DataFrame(
        {
            "data": tabela.index,  # no yfinance a data fica no índice da tabela
            "fechamento": tabela["Close"].to_numpy(),
            "volume": tabela["Volume"].to_numpy(),
        }
    )


def baixar_ibovespa( data_inicial: date, data_final: date, tentativas: int = 3, espera: float = 2.0) -> pd.DataFrame:
    """Baixa o Ibovespa diário e devolve (data, fechamento, volume), SEM tratamento.
    A data continua com fuso horário e nada é filtrado ou convertido aqui:
    Papel da etapa de transformação.
    """
    if data_inicial > data_final:
        raise ValueError("data_inicial não pode ser posterior à data_final")

    # O parâmetro `end` do yfinance é EXCLUSIVO (o último dia não vem na
    # resposta). Somamos 1 dia para que a data_final entre na consulta.
    fim_exclusivo = data_final + timedelta(days=1)
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            tabela = yf.Ticker(TICKER_IBOVESPA).history(
                start=data_inicial.isoformat(), end=fim_exclusivo.isoformat()
            )
            # Quando falha, o yfinance às vezes não dá erro: devolve uma tabela
            # vazia. Tratamos isso como falha para tentar de novo.
            if tabela.empty:
                raise ValueError("O Yahoo Finance devolveu uma tabela vazia")
            return _selecionar_colunas(tabela)
        except Exception as erro:  # a biblioteca lança vários tipos de erro
            ultimo_erro = erro
            if tentativa < tentativas:
                time.sleep(espera * tentativa)

    raise RuntimeError(
        f"Falha ao baixar o Ibovespa após {tentativas} tentativas"
    ) from ultimo_erro