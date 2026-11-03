"""Formatação de números e datas no padrão brasileiro (1.234,56 e dd/mm/aaaa).
Na mão, em vez de usar `locale`, porque o `locale` depende de o
computador ter o idioma instalado e daria resultados diferentes em cada máquina."""
import numpy as np
import pandas as pd

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

SEM_DADO = "N/A"


def numero(valor, casas: int = 2) -> str:
    """1234.5 -> '1.234,50'. Valor vazio vira 'N/A'."""
    if valor is None or pd.isna(valor):
        return SEM_DADO
    texto = f"{float(valor):,.{casas}f}"  # formato inglês: 1,234.50
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def percentual(valor, casas: int = 2, com_sinal: bool = False) -> str:
    """4.58 -> '4,58%'. Com `com_sinal`, positivos ganham '+': '+2,05%'."""
    if valor is None or pd.isna(valor):
        return SEM_DADO
    texto = numero(valor, casas) + "%"
    if com_sinal and float(valor) > 0:
        texto = "+" + texto
    return texto


def data_br(data) -> str:
    """Timestamp -> '30/10/2026'."""
    return pd.Timestamp(data).strftime("%d/%m/%Y")


def mes_ano(data) -> str:
    """Timestamp -> 'set/2026'."""
    data = pd.Timestamp(data)
    return f"{MESES[data.month - 1]}/{data.year}"


def mes_ano_curto(data) -> str:
    """Timestamp -> 'out de 21' (rótulo do eixo dos gráficos)."""
    data = pd.Timestamp(data)
    return f"{MESES[data.month - 1]} de {str(data.year)[2:]}"


def rotulos_eixo(datas, quantidade: int = 6):
    """Escolhe `quantidade` datas bem espaçadas (incluindo a primeira e a última)
    e devolve (posicoes, textos) para o eixo X.

    Existe porque o Plotly escreveria os meses em inglês; assim escrevemos em português."""
    unicas = pd.DatetimeIndex(pd.Series(datas).dropna().unique()).sort_values()
    if len(unicas) == 0:
        return [], []
    posicoes = np.unique(np.linspace(0, len(unicas) - 1, min(quantidade, len(unicas))).round().astype(int))
    escolhidas = [unicas[i] for i in posicoes]
    return escolhidas, [mes_ano_curto(d) for d in escolhidas]
