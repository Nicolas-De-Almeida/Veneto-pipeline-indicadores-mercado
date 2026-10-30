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