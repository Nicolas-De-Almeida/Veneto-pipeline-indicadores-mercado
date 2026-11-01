from datetime import date

"""Configurações centrais do pipeline: códigos das séries e parâmetros."""

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

# Dias úteis por ano usados para anualizar o CDI diário (convenção do mercado).
DIAS_UTEIS_ANO = 252

# Dias em que o Yahoo difere da B3 (conferido manualmente): data -> fechamento B3.
DIAS_DIVERGENTES_IBOVESPA = {date(2023, 11, 10): 120568.14} # hmm