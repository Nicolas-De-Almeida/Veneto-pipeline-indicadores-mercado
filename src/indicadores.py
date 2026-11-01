"""CÁLCULOS feitos na hora de montar o dashboard (não vão para o banco).
Regra de ouro: taxas percentuais se COMPÕEM (multiplicam), nunca se somam.
"""
import pandas as pd

from src import config


def cdi_anualizado(taxa_diaria_pct: float) -> float:
    """Taxa diária (% ao dia) -> % ao ano: (1+d)^252 - 1."""
    return ((1 + taxa_diaria_pct / 100) ** config.DIAS_UTEIS_ANO - 1) * 100


def ganho_real(retorno_nominal_pct: float, inflacao_pct: float) -> float:
    """Ganho acima da inflação: (1+nominal)/(1+inflação) - 1."""
    return ((1 + retorno_nominal_pct / 100) / (1 + inflacao_pct / 100) - 1) * 100

def variacao_percentual(valor_final: float, valor_inicial: float) -> float:
    """Variação simples entre dois valores, em %."""
    if valor_inicial == 0:
        raise ValueError("Valor inicial zero: variação indefinida.")
    return (valor_final / valor_inicial - 1) * 100


def base100(serie: pd.Series) -> pd.Series:
    """Reescala para que o primeiro valor válido seja 100."""
    validos = serie.dropna()
    if validos.empty:
        raise ValueError("Série sem valores.")
    return serie / validos.iloc[0] * 100


def indice_taxa_base100(taxas_pct: pd.Series) -> pd.Series:
    """Transforma taxas (% por período) em índice acumulado; primeira linha = 100."""
    if taxas_pct.empty:
        raise ValueError("Série de taxas vazia.")
    fatores = 1 + taxas_pct.astype(float) / 100
    fatores.iloc[0] = 1.0
    return fatores.cumprod() * 100


def cdi_acumulado_12m(cdi: pd.DataFrame) -> pd.DataFrame:
    """CDI acumulado nos 12 meses até cada data (composto).

    Entrada: colunas 'data', 'cdi' (% ao dia). Datas sem 12 meses de
    histórico anterior ficam fora (NaN removido)."""
    cdi = cdi.sort_values("data").reset_index(drop=True)
    indice = (1 + cdi["cdi"] / 100).cumprod()
    base = pd.DataFrame({"data": cdi["data"], "indice": indice})

    # Para cada data t, acha o índice em t - 12 meses (ou o dia útil anterior).
    alvo = pd.DataFrame({"data": base["data"], "alvo": base["data"] - pd.DateOffset(months=12)})
    passado = pd.merge_asof(
        alvo.sort_values("alvo"),
        base.rename(columns={"data": "data_passada", "indice": "indice_passado"}),
        left_on="alvo",
        right_on="data_passada",
        direction="backward",
    ).sort_values("data")

    resultado = pd.DataFrame(
        {
            "data": base["data"].values,
            "cdi_12m_pct": (base["indice"].values / passado["indice_passado"].values - 1) * 100,
        }
    )
    return resultado.dropna().reset_index(drop=True)


def ipca_acumulado_12m(ipca: pd.DataFrame) -> pd.DataFrame:
    """IPCA acumulado em 12 meses (composto) a cada mês.
    Entrada: 'data' (sempre dia 1 do mês de referência) e 'ipca' (% no mês).
    Meses faltando no meio deixam as janelas afetadas vazias (não inventa)."""
    if not (ipca["data"].dt.day == 1).all():
        raise ValueError("Datas do IPCA devem ser o dia 1 de cada mês.")
    serie = ipca.sort_values("data").set_index("data")["ipca"].asfreq("MS")
    fatores = 1 + serie / 100
    acumulado = fatores.rolling(12, min_periods=12).apply(lambda x: x.prod(), raw=True) - 1
    saida = (acumulado * 100).dropna().rename("ipca_12m_pct").reset_index()
    return saida


def ipca_indice_base100(ipca: pd.DataFrame, data_inicio) -> pd.DataFrame:
    """Índice do IPCA com base 100 em `data_inicio`.
    Linha âncora em `data_inicio` ( = 100); cada mês entra na data do FIM do mês
    (a inflação do mês só está completa ali). Meses antes do início são ignorados."""
    data_inicio = pd.Timestamp(data_inicio)
    mes_inicio = data_inicio.replace(day=1)
    meses = ipca[ipca["data"] >= mes_inicio].sort_values("data")
    if meses.empty:
        raise ValueError("IPCA sem meses a partir da data de início.")
    fim_mes = meses["data"] + pd.offsets.MonthEnd(0)
    indice = 100 * (1 + meses["ipca"] / 100).cumprod()
    ancora = pd.DataFrame({"data": [data_inicio], "indice": [100.0]})
    resto = pd.DataFrame({"data": fim_mes.values, "indice": indice.values})
    return pd.concat([ancora, resto], ignore_index=True)


def alinhar_series(series: dict) -> pd.DataFrame:
    """Põe várias séries no mesmo calendário (união das datas).
    Cada série é DataFrame 'data' + 'valor'. Preenche buracos com o último
    valor conhecido (forward fill), mas NUNCA depois do último dado real de
    cada série: ali fica vazio, para não fingir dados que não existem."""
    colunas = {}
    for nome, df in series.items():
        colunas[nome] = df.set_index("data")["valor"].sort_index()
    calendario = sorted(set().union(*[c.index for c in colunas.values()]))
    saida = pd.DataFrame(index=pd.DatetimeIndex(calendario, name="data"))
    for nome, s in colunas.items():
        r = s.reindex(saida.index).ffill()
        r[r.index > s.index.max()] = float("nan")
        saida[nome] = r
    return saida


def base100_comum(largo: pd.DataFrame) -> pd.DataFrame:
    """Reescala todas as colunas para 100 na 1ª data em que TODAS têm valor."""
    completas = largo.dropna()
    if completas.empty:
        raise ValueError("Nenhuma data em que todas as séries têm valor.")
    return largo / completas.iloc[0] * 100


def recortar_janela(df: pd.DataFrame, inicio, fim=None) -> pd.DataFrame:
    """Mantém só as linhas entre `inicio` e `fim` (inclusive). 'data' em coluna ou índice."""
    datas = df["data"] if "data" in df.columns else df.index.to_series()
    mascara = datas >= pd.Timestamp(inicio)
    if fim is not None:
        mascara &= datas <= pd.Timestamp(fim)
    return df[mascara.values]