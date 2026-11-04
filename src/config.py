"""Configurações centrais do pipeline: códigos das séries e parâmetros."""

from datetime import date
from pathlib import Path


# Códigos das séries do SGS (Banco Central).
SERIES_SGS = {
    "cdi": 12,         # CDI diário, em % ao dia (validado no SGS: fonte Cetip/B3)
    "ipca": 433,       # IPCA, variação % mensal (validado no SGS: fonte IBGE)
    "dolar_ptax": 1,   # Dólar venda, R$/US$ (validado contra a API oficial da PTAX)
}

# Quantos anos de histórico o pipeline coleta.
ANOS_HISTORICO = 5

# Endereço base da API do SGS; {codigo} é substituído pelo código da série.
URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

# Ticker do Ibovespa no Yahoo Finance (via biblioteca yfinance).
TICKER_IBOVESPA = "^BVSP"

# Atualização incremental: a cada execução o pipeline baixa só o que falta, começando alguns dias ANTES da última data já gravada. A sobra serve para
# corrigir dados que mudam depois: o Ibovespa gravado como "parcial" (pregão aberto) e valores revisados pela fonte. 30 dias também cobre o IPCA, que é
# mensal e tem data no dia 1.
MARGEM_INCREMENTAL_DIAS = 30

# Dias úteis por ano usados para anualizar o CDI diário (convenção do mercado).
DIAS_UTEIS_ANO = 252

# Dias em que o Yahoo difere da B3 (conferido manualmente): data -> fechamento B3.
DIAS_DIVERGENTES_IBOVESPA = {date(2023, 11, 10): 120568.14} # hmm

# Banco fica na raiz do projeto.
CAMINHO_BANCO = Path(__file__).resolve().parent.parent / "data" / "mercado.db"


# CDI e IPCA acumulados em 12 meses precisam de 12 meses ANTES do começo da
# janela mostrada; por isso baixei 1 ano extra só dessas duas séries.
ANOS_EXTRAS_12M = 1
SERIES_COM_ANO_EXTRA = ("cdi", "ipca")