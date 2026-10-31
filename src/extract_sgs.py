"""Extração (E) das séries do Banco Central via API do SGS."""

import time
from datetime import date

import pandas as pd
import requests

from src.config import ANOS_HISTORICO, URL_SGS

# A API recusa consultas com janela maior que 10 anos. Usamos 3650 dias
# como limite conservador (anos bissextos têm 1 ou 2 dias a mais).
LIMITE_JANELA_DIAS = 3650


class ErroPedidoRecusado(RuntimeError):
    """A API recusou o pedido (erro HTTP 4xx). Repetir o mesmo pedido não adianta."""


def calcular_periodo(hoje: date | None = None, anos: int = ANOS_HISTORICO) -> tuple[date, date]:
    """Devolve (data_inicial, data_final) cobrindo os últimos `anos` anos."""
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


def _motivo_da_api(resposta) -> str:
    """Lê o motivo que a API devolve no corpo da resposta, ex.: {"erro": "..."}."""
    try:
        corpo = resposta.json()
        if isinstance(corpo, dict):
            return str(corpo.get("erro", corpo))
        return str(corpo)
    except ValueError:
        return "sem detalhes"


def baixar_serie_sgs(codigo: int, data_inicial: date, data_final: date, tentativas: int = 3, espera: float = 2.0) -> pd.DataFrame:
    """Baixa uma série do SGS e devolve os dados BRUTOS (colunas data e valor, em texto).

    Converte tipos só na etapa de transformação, para manter a extração simples.

    Tratamento de falhas:
    - Pedido recusado pela API (erro 4xx): falha na hora com o motivo dela,
      porque repetir o mesmo pedido daria o mesmo erro.
    - Falha de rede, timeout, erro 5xx ou resposta que não é JSON: tenta de novo
      até `tentativas` vezes, esperando um pouco mais a cada vez.
    """
    # A API exige data_final MAIOR que data_inicial (recusa janela de um dia só).
    if data_inicial >= data_final:
        raise ValueError("data_final deve ser posterior à data_inicial (exigência da API do SGS)")
    if (data_final - data_inicial).days > LIMITE_JANELA_DIAS:
        raise ValueError("A API do SGS não aceita janelas maiores que 10 anos")

    url = URL_SGS.format(codigo=codigo)
    params = montar_parametros(data_inicial, data_final)
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, params=params, timeout=30)
            if 400 <= resposta.status_code < 500:
                raise ErroPedidoRecusado(
                    f"A API do SGS recusou o pedido da série {codigo} "
                    f"(HTTP {resposta.status_code}): {_motivo_da_api(resposta)}"
                )
            resposta.raise_for_status()  # erros 5xx viram exceção e são repetidos
            return pd.DataFrame(resposta.json())
        except (requests.RequestException, ValueError) as erro:
            ultimo_erro = erro
            if tentativa < tentativas:
                time.sleep(espera * tentativa)

    raise RuntimeError(
        f"Falha ao baixar a série {codigo} após {tentativas} tentativas"
    ) from ultimo_erro