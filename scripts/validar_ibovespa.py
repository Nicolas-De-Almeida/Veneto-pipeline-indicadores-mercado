"""Validação do Ibovespa do yfinance contra fechamentos divulgados na imprensa.

Objetivo: conferir que o fechamento que o Yahoo Finance entrega bate com o
fechamento oficial da B3 em algumas datas, como fiz com o dólar.

Como rodar (na raiz do projeto, com o .venv ativo):
    python3 -m scripts.validar_ibovespa
"""

from datetime import date

import pandas as pd

from src.extract_ibovespa import baixar_ibovespa

# Fechamentos de referência, em pontos, da série histórica do Ibovespa no site da B3 
# (tabela "IBovespa - 2026"), conferidos manualmente em 31/10/2026.
FECHAMENTOS_REFERENCIA = {
    date(2026, 7, 14): 176641.10,
    date(2026, 8, 14): 166934.20,
    date(2026, 9, 14): 185500.88,
    date(2026, 10, 5): 206911.89,
    date(2026, 10, 6): 205835.29,
    date(2026, 10, 7): 204302.33,
    date(2026, 10, 8): 206220.24,
    date(2026, 10, 9): 209066.90,
    date(2026, 10, 13): 206887.52,
    date(2026, 10, 14): 206505.98,
    date(2026, 10, 15): 204324.26,
    date(2026, 10, 16): 205430.33,
    date(2026, 10, 19): 205079.25,
    date(2026, 10, 20): 208295.98,
    date(2026, 10, 21): 206495.23,
    date(2026, 10, 22): 204120.12,
    date(2026, 10, 23): 205082.56,

    # Dias com volume zero no Yahoo, conferidos na série histórica da B3
    date(2022, 1, 5): 101005.64,
    date(2022, 2, 4): 112244.94,
    date(2022, 3, 2): 115173.61,
    date(2022, 4, 19): 115056.66,
    date(2023, 3, 20): 100922.89,
    date(2023, 3, 23): 97926.34,
    date(2023, 3, 24): 98829.27,
    date(2023, 12, 26): 133532.92,
    date(2024, 7, 1): 124718.07,
}


# Dias em que o Yahoo difere da B3 por mais que o arredondamento. Ficam fora da
# lista acima para não esconder o problema: o script os mostra à parte.
DIVERGENCIAS_CONHECIDAS = {
    date(2023, 11, 10): 120568.14,  # o Yahoo entrega 120636 (cerca de 68 pontos a mais)
}

# O Yahoo entrega o fechamento arredondado em pontos inteiros e a referência
# tem duas casas decimais; por isso aceitamos diferença menor que 1 ponto.
TOLERANCIA_PONTOS = 1.0


def valores_batem(valor_yahoo: float, valor_referencia: float, tolerancia: float = TOLERANCIA_PONTOS) -> bool:
    """Diz se os dois fechamentos são iguais, a menos de arredondamento."""
    return abs(valor_yahoo - valor_referencia) < tolerancia


def fechamento_por_dia(tabela: pd.DataFrame) -> dict:
    """Transforma a tabela do extrator em {data: fechamento}."""
    dias = tabela["data"].dt.date  # a data vem com fuso; aqui só o dia interessa
    return dict(zip(dias, tabela["fechamento"]))


def comparar(tabela: pd.DataFrame, referencias: dict) -> list:
    """Compara cada referência com o fechamento da tabela.

    Devolve uma lista de (data, valor_yahoo ou None, valor_referencia, bateu).
    """
    yahoo = fechamento_por_dia(tabela)
    resultado = []
    for dia, referencia in sorted(referencias.items()):
        valor = yahoo.get(dia)
        bateu = valor is not None and valores_batem(valor, referencia)
        resultado.append((dia, valor, referencia, bateu))
    return resultado


def main() -> None:
    """Baixa o período das referências e imprime o veredito de cada data."""
    todas = {**FECHAMENTOS_REFERENCIA, **DIVERGENCIAS_CONHECIDAS}
    datas = sorted(todas)
    tabela = baixar_ibovespa(datas[0], datas[-1])

    todas_iguais = True
    for dia, valor, referencia, bateu in comparar(tabela, FECHAMENTOS_REFERENCIA):
        todas_iguais = todas_iguais and bateu
        print(f"{dia} | Yahoo: {valor} | Referência: {referencia} | {'IGUAIS' if bateu else 'DIFERENTES'}")

    print("--- Divergências conhecidas ---")
    for dia, valor, referencia, bateu in comparar(tabela, DIVERGENCIAS_CONHECIDAS):
        diferenca = None if valor is None else round(valor - referencia, 2)
        estado = "AGORA BATE (revisar esta lista)" if bateu else "CONTINUA DIVERGINDO"
        print(f"{dia} | Yahoo: {valor} | B3: {referencia} | diferença: {diferenca} | {estado}")

    if todas_iguais:
        print("Ibovespa conferido, com as divergências conhecidas acima.")
    else:
        print("ATENÇÃO: houve divergência nova, revisar.")

if __name__ == "__main__":
    main()