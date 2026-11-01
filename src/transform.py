"""Etapa de TRANSFORMAÇÃO: limpa os dados brutos antes de irem ao banco.

Aqui só arruma o formato (texto -> número/data) e se marcam casos
especiais. 
Cálculos (acumulado 12 meses, base 100...) vão ficar em indicadores.py.
"""
from datetime import date

import pandas as pd

from src import config

def converter_serie_sgs(bruto: pd.DataFrame, nome_valor: str = "valor") -> pd.DataFrame:
    """Converte a tabela bruta do SGS (tudo texto) em data real + número.

    Entrada: colunas 'data' (dd/mm/aaaa) e 'valor' (texto).
    Saída: colunas 'data' (datetime) e `nome_valor` (float), ordenada, sem
    datas repetidas (fica a última), índice 0..n-1.
    Qualquer valor que não converte, gera erro: melhor parar do que gravar lixo."""

    if bruto is None or bruto.empty:
        raise ValueError("Tabela do SGS vazia: nada para transformar.")
    if not {"data", "valor"} <= set(bruto.columns):
        raise ValueError("Tabela do SGS precisa das colunas 'data' e 'valor'.")

    datas = pd.to_datetime(bruto["data"], format="%d/%m/%Y", errors="raise")
    valores = pd.to_numeric(bruto["valor"], errors="raise").astype(float)
    # O pandas converte texto vazio ("") em NaN sem avisar; aqui isso é erro.
    if valores.isna().any():
        raise ValueError("Valor vazio/ausente na série do SGS.")

    limpo = pd.DataFrame({"data": datas, nome_valor: valores})
    limpo = limpo.sort_values("data").drop_duplicates("data", keep="last")
    return limpo.reset_index(drop=True)

def tratar_ibovespa(
    bruto: pd.DataFrame,
    hoje: date | None = None,
    dias_divergentes: dict | None = None,
) -> pd.DataFrame:
    """Limpa a tabela do Ibovespa vinda do Yahoo.

    - tira o fuso horário SEM converter (o dia continua o dia do pregão);
    - volume 0 vira vazio (Yahoo usa 0 quando não tem o dado);
    - remove linhas sem fechamento;
    - coluna 'parcial': True se a data é hoje (pregão pode estar aberto);
    - coluna 'divergente': True nos dias em que Yahoo difere da B3."""

    if bruto is None or bruto.empty:
        raise ValueError("Tabela do Ibovespa vazia: nada para transformar.")
    if not {"data", "fechamento", "volume"} <= set(bruto.columns):
        raise ValueError("Tabela do Ibovespa precisa de 'data', 'fechamento' e 'volume'.")

    if hoje is None:
        hoje = date.today()
    if dias_divergentes is None:
        dias_divergentes = config.DIAS_DIVERGENTES_IBOVESPA

    datas = pd.to_datetime(bruto["data"])
    if datas.dt.tz is not None:
        datas = datas.dt.tz_localize(None) # remove o fuso mantendo o horário local
    datas = datas.dt.normalize()

    volume = pd.to_numeric(bruto["volume"], errors="raise")
    volume = volume.where(volume != 0).astype("Int64")

    limpo = pd.DataFrame(
        {
            "data": datas,
            "fechamento": pd.to_numeric(bruto["fechamento"], errors="raise").astype(float),
            "volume": volume,
        }
    )
    limpo = limpo.dropna(subset=["fechamento"])
    limpo["parcial"] = limpo["data"].dt.date == hoje
    limpo["divergente"] = limpo["data"].dt.date.isin(set(dias_divergentes))
    limpo = limpo.sort_values("data").drop_duplicates("data", keep="last")
    return limpo.reset_index(drop=True)