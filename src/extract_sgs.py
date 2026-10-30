"""Extração (E) das séries do Banco Central via API do SGS."""

import time
from datetime import date

import pandas as pd
import requests

from src.config import ANOS_HISTORICO, URL_SGS

# A API recusa consultas com janela maior que 10 anos. Usamos 3650 dias
# como limite conservador (anos bissextos têm 1 ou 2 dias a mais).
LIMITE_JANELA_DIAS = 3650


def calcular_periodo(hoje: date | None = None, anos: int = ANOS_HISTORICO) -> tuple[date, date]:
    """Devolve (data_inicial, data_final) cobrindo os últimos `anos`."""
    hoje = hoje or date.today()
    inicio = (pd.Timestamp(hoje) - pd.DateOffset(years=anos)).date()
    return inicio, hoje


def montar_parametros(data_inicial: date, data_final: date) -> dict:
    """Monta os parâmetros da URL. A API exige datas no formato dd/mm/aaaa."""
    return {
        "formato": "json",
        "dataInicial": data_inicial.strftime("%d/%m/%Y"),
        "dataFinal": data_final.strftime("%d/%m/%Y"),
    }


def baixar_serie_sgs(
    codigo: int,
    data_inicial: date,
    data_final: date,
    tentativas: int = 3,
    espera: float = 2.0,
) -> pd.DataFrame:
    """Baixa uma série do SGS e devolve os dados BRUTOS (colunas data e valor, em texto).

    Convertemos tipos só na etapa de transformação, para manter a extração simples.
    Se a API falhar (erro de rede, HTTP de erro ou resposta que não é JSON),
    tentamos de novo `tentativas` vezes, esperando um pouco mais a cada vez.
    """
    if data_inicial > data_final:
        raise ValueError("data_inicial não pode ser posterior à data_final")
    if (data_final - data_inicial).days > LIMITE_JANELA_DIAS:
        raise ValueError("A API do SGS não aceita janelas maiores que 10 anos")

    url = URL_SGS.format(codigo=codigo)
    params = montar_parametros(data_inicial, data_final)
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, params=params, timeout=30)
            resposta.raise_for_status()  # transforma HTTP 4xx/5xx em exceção
            return pd.DataFrame(resposta.json())
        except (requests.RequestException, ValueError) as erro:
            ultimo_erro = erro
            if tentativa < tentativas:
                time.sleep(espera * tentativa)

    raise RuntimeError(
        f"Falha ao baixar a série {codigo} após {tentativas} tentativas"
    ) from ultimo_erro