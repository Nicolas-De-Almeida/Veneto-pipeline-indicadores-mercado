"""Prepara TUDO que o dashboard mostra.
Fluxo: ler as tabelas do SQLite -----> construir_painel(...) ----> a tela só exibe."""
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from dashboard import formatos as fmt
from src import config
from src import indicadores as ind
from src import load

# Quantos meses cada botão de período cobre.
PERIODOS = {"1M": 1, "6M": 6, "12M": 12, "3A": 36, "5A": 60}
PERIODO_PADRAO = "5A"

# O gráfico de juros reais compara IPCA (mensal) com CDI; num período curto
# teria 1 ou 2 pontos de IPCA. Por isso ele nunca mostra menos que 12 meses.
JANELA_MINIMA_JUROS_REAIS_MESES = 12

# Dias em que o Yahoo difere da B3 (lista em config.py). True = aparecem como
# N/A (buraco) nos gráficos; False = aparecem com o valor do Yahoo e uma marcação.
OCULTAR_DIVERGENTES_PADRAO = True


@dataclass
class Cartao:
    titulo: str
    valor: str
    unidade: str
    detalhe: str
    referencia: str  # de quando é o dado: cada cartão tem a sua data
    tom: str = "neutro"  # 'positivo', 'negativo' ou 'neutro' (cor do detalhe)


@dataclass
class ResumoIbovespa:
    rotulo: str  # 'FECHAMENTO' ou 'PARCIAL · hh:mm'
    valor: str
    variacao_dia: str
    tom: str


@dataclass
class JurosReais:
    cdi_12m: pd.DataFrame  # data, cdi_12m_pct (diário)
    ipca_12m: pd.DataFrame  # data (fim do mês), ipca_12m_pct (mensal)
    ganho_real: float | None
    mes_ref: str | None


@dataclass
class Painel:
    periodo: str
    inicio: pd.Timestamp
    dados_ate: pd.Timestamp
    ultima_execucao: datetime | None
    cartoes: list
    comparativo: pd.DataFrame  # índice = data; colunas cdi, ibovespa, dolar (base 100)
    ipca_pontos: pd.DataFrame | None  # data, indice (base 100)
    juros: JurosReais
    cambio: pd.DataFrame  # data, valor
    ibovespa: pd.DataFrame  # data, fechamento, volume, divergente (sem dia parcial)
    resumo_ibovespa: ResumoIbovespa
    tabela: pd.DataFrame  # todos os dados do período, para ver/baixar


def ler_dados(conn) -> dict:
    """Lê as quatro tabelas do banco: {nome_da_tabela: DataFrame}."""
    return {tabela: load.ler_tabela(conn, tabela) for tabela in load.TABELAS}


def inicio_do_periodo(ultima_data, periodo: str) -> pd.Timestamp:
    """Data em que começa o período escolhido (ex.: '12M' = 12 meses antes da última data)."""
    if periodo not in PERIODOS:
        raise ValueError(f"Período inválido: {periodo!r}. Use um de {list(PERIODOS)}.")
    return pd.Timestamp(ultima_data) - pd.DateOffset(months=PERIODOS[periodo])


def _tom(valor) -> str:
    if valor is None or pd.isna(valor) or valor == 0:
        return "neutro"
    return "positivo" if valor > 0 else "negativo"


def _primeiro_no_periodo(df: pd.DataFrame, inicio: pd.Timestamp) -> pd.Series:
    """Primeira linha do período (ou a primeira que existir, se o histórico for mais curto)."""
    dentro = df[df["data"] >= inicio]
    return (dentro if not dentro.empty else df).iloc[0]


def _validar(dados: dict) -> None:
    for tabela in load.TABELAS:
        if tabela not in dados or dados[tabela].empty:
            raise ValueError(
                f"A tabela '{tabela}' está vazia. Rode o pipeline: python3 -m src.pipeline"
            )


def _horario_parcial(ultima_data, ultima_execucao) -> str:
    """' hh:mm' se a execução do pipeline foi no mesmo dia do dado parcial; senão vazio."""
    if ultima_execucao is not None and ultima_execucao.date() == pd.Timestamp(ultima_data).date():
        return " " + ultima_execucao.strftime("%H:%M")
    return ""


def construir_painel(
    dados: dict,
    periodo: str = PERIODO_PADRAO,
    ultima_execucao: datetime | None = None,
    ocultar_divergentes: bool = OCULTAR_DIVERGENTES_PADRAO,
) -> Painel:
    """Monta tudo o que a tela precisa para o período escolhido.

    `ocultar_divergentes`: se True (padrão), o dia em que o Yahoo difere da B3
    vira "sem dado" (buraco no gráfico). Se False, o valor aparece com marcação.
    """
    _validar(dados)
    cdi = dados["cdi"].rename(columns={"valor": "cdi"})
    ipca = dados["ipca"].rename(columns={"valor": "ipca"})
    dolar = dados["dolar_ptax"]
    ibov_todo = dados["ibovespa"]
    # O dia parcial (pregão ainda aberto) aparece só no cartão, nunca nos gráficos.
    ibov = ibov_todo[~ibov_todo["parcial"]].reset_index(drop=True)
    if ibov.empty:
        raise ValueError("O Ibovespa só tem dia parcial; rode o pipeline após o fechamento.")

    # "Dados até": a data mais antiga entre as últimas das séries diárias.
    # Até ela, TODAS as séries têm dado; cada cartão mostra a própria data.
    dados_ate = min(cdi["data"].max(), dolar["data"].max(), ibov["data"].max())
    inicio = inicio_do_periodo(dados_ate, periodo)

    # Cartões
    ipca_12m = ind.ipca_acumulado_12m(ipca)
    cdi_dia = float(cdi["cdi"].iloc[-1])
    cartao_cdi = Cartao(
        "CDI",
        fmt.numero(ind.cdi_anualizado(cdi_dia), 2) + "%",
        "a.a.",
        f"{fmt.numero(cdi_dia, 4)}% ao dia",
        f"Ref.: {fmt.data_br(cdi['data'].iloc[-1])}",
    )

    if ipca_12m.empty:
        cartao_ipca = Cartao("IPCA 12 meses", fmt.SEM_DADO, "", "histórico insuficiente", "Ref.: —")
    else:
        mes = fmt.mes_ano(ipca_12m["data"].iloc[-1])
        cartao_ipca = Cartao(
            "IPCA 12 meses",
            fmt.percentual(ipca_12m["ipca_12m_pct"].iloc[-1], 2),
            "",
            f"acumulado até {mes}",
            f"Ref.: {mes}",
        )

    dolar_ultimo = float(dolar["valor"].iloc[-1])
    var_dolar = ind.variacao_percentual(dolar_ultimo, float(_primeiro_no_periodo(dolar, inicio)["valor"]))
    cartao_dolar = Cartao(
        "Dólar PTAX venda",
        "R$ " + fmt.numero(dolar_ultimo, 4),
        "",
        f"{fmt.percentual(var_dolar, 2, True)} no período",
        f"Ref.: {fmt.data_br(dolar['data'].iloc[-1])}",
        _tom(var_dolar),
    )

    ibov_ultimo = ibov_todo.iloc[-1]  # pode ser o dia parcial
    var_ibov = ind.variacao_percentual(
        float(ibov_ultimo["fechamento"]), float(_primeiro_no_periodo(ibov, inicio)["fechamento"])
    )
    ref_ibov = f"Ref.: {fmt.data_br(ibov_ultimo['data'])}"
    if bool(ibov_ultimo["parcial"]):
        ref_ibov += " · parcial" + _horario_parcial(ibov_ultimo["data"], ultima_execucao)
    cartao_ibov = Cartao(
        "Ibovespa",
        fmt.numero(ibov_ultimo["fechamento"], 0),
        "pontos",
        f"{fmt.percentual(var_ibov, 2, True)} no período",
        ref_ibov,
        _tom(var_ibov),
    )

    # Comparativo base 100
    indice_cdi = pd.DataFrame(
        {"data": cdi["data"], "valor": ind.indice_taxa_base100(cdi["cdi"]).to_numpy()}
    )
    ibov_serie = ibov[["data", "fechamento", "divergente"]]
    if ocultar_divergentes:
        ibov_serie = ibov_serie[~ibov_serie["divergente"]]
    series = {
        "cdi": ind.recortar_janela(indice_cdi, inicio),
        "ibovespa": ind.recortar_janela(
            ibov_serie[["data", "fechamento"]].rename(columns={"fechamento": "valor"}), inicio
        ),
        "dolar": ind.recortar_janela(dolar[["data", "valor"]], inicio),
    }
    largo = ind.alinhar_series(series)
    completas = largo.dropna()
    if completas.empty:
        raise ValueError("Não há data em que CDI, Ibovespa e dólar tenham dado no período.")
    inicio_comum = completas.index[0]
    comparativo = ind.base100_comum(largo).loc[inicio_comum:].copy()
    if ocultar_divergentes:
        # O preenchimento (forward fill) taparia o buraco; aqui o dia volta a ser N/A.
        dias = pd.DatetimeIndex(ibov.loc[ibov["divergente"], "data"])
        comparativo.loc[comparativo.index.intersection(dias), "ibovespa"] = float("nan")

    try:
        ipca_pontos = ind.ipca_indice_base100(ipca, inicio_comum)
        ipca_pontos = ipca_pontos[ipca_pontos["data"] <= dados_ate].reset_index(drop=True)
        if len(ipca_pontos) < 2:  # só a linha-âncora: não há mês para desenhar
            ipca_pontos = None
    except ValueError:  # nenhum IPCA divulgado dentro do período
        ipca_pontos = None

    # Juros reais
    cdi_12m = ind.cdi_acumulado_12m(cdi)
    ipca_12m_fim = ipca_12m.assign(data=ipca_12m["data"] + pd.offsets.MonthEnd(0))
    inicio_juros = min(
        inicio, dados_ate - pd.DateOffset(months=JANELA_MINIMA_JUROS_REAIS_MESES)
    )
    ganho = None
    mes_ref = None
    if not ipca_12m.empty and not cdi_12m.empty:
        # Compara o MESMO período: CDI de 12 meses até o fim do mês do último IPCA.
        fim_do_mes = ipca_12m_fim["data"].iloc[-1]
        cdi_ate_la = cdi_12m[cdi_12m["data"] <= fim_do_mes]
        if not cdi_ate_la.empty:
            ganho = ind.ganho_real(
                float(cdi_ate_la["cdi_12m_pct"].iloc[-1]), float(ipca_12m["ipca_12m_pct"].iloc[-1])
            )
            mes_ref = fmt.mes_ano(ipca_12m["data"].iloc[-1])
    juros = JurosReais(
        cdi_12m[cdi_12m["data"] >= inicio_juros].reset_index(drop=True),
        ipca_12m_fim[ipca_12m_fim["data"] >= inicio_juros].reset_index(drop=True),
        ganho,
        mes_ref,
    )

    # Câmbio e Ibovespa
    cambio = dolar[dolar["data"] >= inicio].reset_index(drop=True)
    ibov_painel = ibov[ibov["data"] >= inicio][["data", "fechamento", "volume", "divergente"]].copy()
    if ocultar_divergentes:
        ibov_painel["fechamento"] = ibov_painel["fechamento"].where(~ibov_painel["divergente"])
    ibov_painel = ibov_painel.reset_index(drop=True)

    penultimo = ibov_todo["fechamento"].iloc[-2] if len(ibov_todo) > 1 else None
    var_dia = None if penultimo is None else ind.variacao_percentual(
        float(ibov_ultimo["fechamento"]), float(penultimo)
    )
    rotulo = "FECHAMENTO"
    if bool(ibov_ultimo["parcial"]):
        hora = _horario_parcial(ibov_ultimo["data"], ultima_execucao)
        rotulo = "PARCIAL" + (f" ·{hora}" if hora else "")
    resumo = ResumoIbovespa(
        rotulo,
        fmt.numero(ibov_ultimo["fechamento"], 0),
        fmt.percentual(var_dia, 2, True) + " no dia" if var_dia is not None else fmt.SEM_DADO,
        _tom(var_dia),
    )

    return Painel(
        periodo, inicio, dados_ate, ultima_execucao,
        [cartao_cdi, cartao_ipca, cartao_dolar, cartao_ibov],
        comparativo, ipca_pontos, juros, cambio, ibov_painel, resumo,
        _montar_tabela(cdi, dolar, ibov_todo, inicio),
    )


def _texto_divergencia(data, divergente) -> str:
    """'' se o dia está normal; senão 'sim · B3: 120.568,14' (valor oficial, se conhecido)."""
    if not divergente:
        return ""
    b3 = config.DIAS_DIVERGENTES_IBOVESPA.get(pd.Timestamp(data).date())
    return "sim" if b3 is None else f"sim · B3: {fmt.numero(b3, 2)}"


def _montar_tabela(cdi, dolar, ibov_todo, inicio) -> pd.DataFrame:
    """Todos os dados REAIS do período numa tabela só (sem preencher buracos)."""
    t = cdi[["data", "cdi"]].rename(columns={"cdi": "CDI (% ao dia)"})
    t = t.merge(
        dolar[["data", "valor"]].rename(columns={"valor": "Dólar PTAX venda (R$)"}),
        on="data", how="outer",
    )
    ibov = ibov_todo.rename(
        columns={"fechamento": "Ibovespa (pontos)", "volume": "Volume (Yahoo Finance)"}
    )
    ibov["Dia parcial"] = ibov["parcial"].map({True: "sim", False: ""})
    ibov["Difere da B3"] = [
        _texto_divergencia(d, v) for d, v in zip(ibov["data"], ibov["divergente"])
    ]
    t = t.merge(
        ibov[["data", "Ibovespa (pontos)", "Volume (Yahoo Finance)", "Dia parcial", "Difere da B3"]],
        on="data", how="outer",
    )
    # Datas em que o Ibovespa não tem linha ficariam com "None" nestas duas colunas de texto.
    t[["Dia parcial", "Difere da B3"]] = t[["Dia parcial", "Difere da B3"]].fillna("")
    t = t[t["data"] >= inicio].sort_values("data").reset_index(drop=True)
    return t.rename(columns={"data": "Data"})


def formatar_tabela(tabela: pd.DataFrame) -> pd.DataFrame:
    """Versão para EXIBIR na tela (tudo texto, no padrão brasileiro). O CSV usa a original.

    Dois "vazios" diferentes:
    - 'N/A' = a série tem o dia, mas o dado não veio (ex.: volume do Yahoo);
    - '—'   = a série não tem linha nesse dia (ex.: feriado numa das fontes).
    """
    vazio = "—"

    def numero(valor, casas):
        return vazio if pd.isna(valor) else fmt.numero(valor, casas)

    tem_ibov = tabela["Ibovespa (pontos)"].notna()
    volume = [
        vazio if not existe else fmt.numero(v, 0)  # fmt.numero devolve 'N/A' se o volume veio vazio
        for v, existe in zip(tabela["Volume (Yahoo Finance)"], tem_ibov)
    ]
    return pd.DataFrame(
        {
            "Data": tabela["Data"].dt.strftime("%d/%m/%Y"),
            "CDI (% ao dia)": [numero(v, 4) for v in tabela["CDI (% ao dia)"]],
            "Dólar PTAX venda (R$)": [numero(v, 4) for v in tabela["Dólar PTAX venda (R$)"]],
            "Ibovespa (pontos)": [numero(v, 0) for v in tabela["Ibovespa (pontos)"]],
            "Volume (Yahoo Finance)": volume,
            "Dia parcial": tabela["Dia parcial"],
            "Difere da B3": tabela["Difere da B3"],
        }
    )


def csv_bytes(tabela: pd.DataFrame) -> bytes:
    """CSV para abrir no Excel em português: separador ';', vírgula decimal, acentos corretos."""
    return tabela.to_csv(
        index=False, sep=";", decimal=",", date_format="%d/%m/%Y"
    ).encode("utf-8-sig")
