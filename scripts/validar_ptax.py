"""Validação da série 1 do SGS contra a API oficial da PTAX (Olinda).

Objetivo: provar que a série 1 do SGS é a PTAX de venda, comparando os valores
das duas fontes nas mesmas datas.

Como rodar (na raiz do projeto, com o .venv ativo):
    python3 -m scripts.validar_ptax
"""

from datetime import datetime, timedelta

import requests

from src.config import SERIES_SGS
from src.extract_sgs import baixar_serie_sgs

# API oficial da PTAX do Banco Central (serviço Olinda).
URL_PTAX = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarDia(dataCotacao=@dataCotacao)"
)

# Datas de anos diferentes e todas em dia útil (a PTAX não existe em feriado
# nem fim de semana).
DATAS_VALIDACAO = ["26/10/2026", "15/03/2023", "04/08/2025"]

# A PTAX traz 5 casas decimais e o SGS traz 4, então aceitamos uma diferença
# de arredondamento menor que meio décimo de milésimo.
TOLERANCIA = 0.00005


def data_para_formato_ptax(data_br: str) -> str:
    """Converte 'dd/mm/aaaa' para 'mm-dd-aaaa', o formato que a API da PTAX exige."""
    dia, mes, ano = data_br.split("/")
    return f"{mes}-{dia}-{ano}"


def valores_batem(valor_sgs: float, valor_ptax: float, tolerancia: float = TOLERANCIA) -> bool:
    """Diz se dois valores são iguais, a menos de diferença de arredondamento."""
    return abs(valor_sgs - valor_ptax) < tolerancia


def buscar_sgs(data_br: str) -> float:
    """Busca o dólar da série 1 numa data, usando o nosso extrator real.

    A API do SGS exige data_final MAIOR que data_inicial (recusa janela de um
    dia só). Por isso pedimos o dia anterior junto e filtramos a data certa.
    """
    dia = datetime.strptime(data_br, "%d/%m/%Y").date()
    tabela = baixar_serie_sgs(SERIES_SGS["dolar_ptax"], dia - timedelta(days=1), dia)
    if tabela.empty or data_br not in tabela["data"].values:
        raise ValueError(f"A série 1 não tem valor em {data_br} (feriado ou fim de semana?)")
    linha = tabela[tabela["data"] == data_br]
    return float(linha.iloc[0]["valor"])  # a API entrega texto; convertemos aqui


def buscar_ptax(data_br: str) -> float:
    """Busca a cotação de venda na API oficial da PTAX."""
    url = f"{URL_PTAX}?@dataCotacao='{data_para_formato_ptax(data_br)}'&$format=json"
    resposta = requests.get(url, timeout=30)
    resposta.raise_for_status()
    return resposta.json()["value"][0]["cotacaoVenda"]


def main() -> None:
    """Compara as duas fontes em cada data e imprime o veredito."""
    todas_iguais = True
    for data in DATAS_VALIDACAO:
        valor_sgs = buscar_sgs(data)
        valor_ptax = buscar_ptax(data)
        bateu = valores_batem(valor_sgs, valor_ptax)
        todas_iguais = todas_iguais and bateu
        print(f"{data} | SGS: {valor_sgs} | PTAX: {valor_ptax} | {'IGUAIS' if bateu else 'DIFERENTES'}")
    print("Série 1 validada." if todas_iguais else "ATENÇÃO: houve divergência, revisar o código da série.")


if __name__ == "__main__":
    main()