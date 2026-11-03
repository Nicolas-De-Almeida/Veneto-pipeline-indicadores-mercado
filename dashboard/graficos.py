"""Gráficos Plotly do dashboard. Cada função recebe o `Painel` e devolve uma figura.
Plotly é a biblioteca que desenha os gráficos interativos. Só  as figuras; quem as exibe é o app.py.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard import formatos as fmt
from dashboard import tema
from src import config

CONFIG_PLOTLY = {"displayModeBar": False}  # esconde a barra de ferramentas do Plotly
FONTE = "DM Sans, system-ui, sans-serif"


def _como_datetime(datas) -> list:
    return [pd.Timestamp(d).to_pydatetime() for d in datas]


def _base(fig: go.Figure, datas, altura: int, direita: int = 70) -> go.Figure:
    """Aparência comum a todos os gráficos."""
    fig.update_layout(
        height=altura,
        margin=dict(l=10, r=direita, t=10, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family=FONTE, size=12, color=tema.CINZA),
        hovermode="x unified",  # um só balão com todas as séries na data do cursor
        hoverlabel=dict(bgcolor=tema.NAVY, font=dict(color="white")),
        separators=",.",  # vírgula decimal e ponto de milhar (padrão brasileiro)
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    posicoes, textos = fmt.rotulos_eixo(datas, 6)
    fig.update_xaxes(
        showgrid=False,
        linecolor=tema.GRADE,
        tickmode="array",
        tickvals=_como_datetime(posicoes),
        ticktext=textos,
        hoverformat="%d/%m/%Y",
    )
    fig.update_yaxes(gridcolor=tema.GRADE, zeroline=False, linecolor="white")
    return fig


def _rotulo_final(fig, x, y, texto: str, cor: str) -> None:
    """Escreve o valor final da série, à direita da última ponta da linha."""
    fig.add_annotation(
        x=pd.Timestamp(x).to_pydatetime(), y=y, text=f"<b>{texto}</b>", showarrow=False,
        xanchor="left", xshift=8, font=dict(color=cor, size=12),
    )


def _linha(x, y, nome: str, cor: str, largura: float = 3, tracejada: bool = False,
           formato: str = ",.1f", sufixo: str = "") -> go.Scatter:
    return go.Scatter(
        x=x, y=y, mode="lines", name=nome,
        line=dict(color=cor, width=largura, dash="dash" if tracejada else "solid"),
        hovertemplate=f"%{{y:{formato}}}{sufixo}<extra>{nome}</extra>",
    )


def fig_comparativo(painel) -> go.Figure:
    """CDI, Ibovespa, dólar e IPCA em base 100 no começo do período."""
    comp = painel.comparativo
    fig = go.Figure()
    series = [
        ("cdi", "CDI acumulado", tema.OURO, False),
        ("ibovespa", "Ibovespa", tema.NAVY, False),
        ("dolar", "Dólar", tema.AZUL, False),
    ]
    for coluna, nome, cor, tracejada in series:
        fig.add_trace(_linha(comp.index, comp[coluna], nome, cor, 3, tracejada))
        valido = comp[coluna].dropna()  # a série pode acabar antes das outras
        if not valido.empty:
            _rotulo_final(fig, valido.index[-1], valido.iloc[-1], fmt.numero(valido.iloc[-1], 1), cor)

    datas = list(comp.index)
    if painel.ipca_pontos is not None:
        ip = painel.ipca_pontos
        fig.add_trace(_linha(ip["data"], ip["indice"], "IPCA acumulado", tema.CINZA, 2.5, True))
        _rotulo_final(fig, ip["data"].iloc[-1], ip["indice"].iloc[-1], fmt.numero(ip["indice"].iloc[-1], 1), tema.CINZA)
    return _base(fig, datas, altura=420)


def fig_juros_reais(painel) -> go.Figure:
    """CDI acumulado em 12 meses contra IPCA acumulado em 12 meses."""
    j = painel.juros
    fig = go.Figure()
    fig.add_trace(_linha(j.cdi_12m["data"], j.cdi_12m["cdi_12m_pct"], "CDI 12 meses",
                         tema.OURO, 3, formato=".2f", sufixo="%"))
    fig.add_trace(_linha(j.ipca_12m["data"], j.ipca_12m["ipca_12m_pct"], "IPCA 12 meses",
                         tema.CINZA, 2.5, True, formato=".2f", sufixo="%"))
    datas = list(j.cdi_12m["data"]) + list(j.ipca_12m["data"])
    fig = _base(fig, datas, altura=280, direita=20)
    fig.update_yaxes(ticksuffix="%", tickformat=".0f")
    return fig


def fig_cambio(painel) -> go.Figure:
    """Dólar PTAX de venda ao longo do período."""
    c = painel.cambio
    fig = go.Figure()
    fig.add_trace(_linha(c["data"], c["valor"], "PTAX venda", tema.NAVY, 2.5, formato=".4f"))
    fig = _base(fig, c["data"], altura=280, direita=20)
    fig.update_yaxes(tickprefix="R$ ", tickformat=".2f")
    return fig


def fig_ibovespa(painel) -> go.Figure:
    """Fechamento do Ibovespa (linha) e volume (barras embaixo)."""
    df = painel.ibovespa
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22], vertical_spacing=0.04)
    fig.add_trace(
        _linha(df["data"], df["fechamento"], "Ibovespa", tema.NAVY, 2.5, formato=",.0f"), row=1, col=1
    )
    # Volume vazio (NA) vira NaN, o Plotly não desenha barra naquele dia.
    fig.add_trace(
        go.Bar(
            x=df["data"], y=df["volume"].astype("float64"), name="Volume (Yahoo Finance)",
            marker_color=tema.CINZA_CLARO,
            hovertemplate="%{y:,.0f}<extra>Volume (Yahoo Finance)</extra>",
        ),
        row=2, col=1,
    )
    divergentes = df[df["divergente"] & df["fechamento"].notna()]
    if not divergentes.empty:
        b3 = [config.DIAS_DIVERGENTES_IBOVESPA.get(d.date()) for d in divergentes["data"]]
        fig.add_trace(
            go.Scatter(
                x=divergentes["data"], y=divergentes["fechamento"], mode="markers",
                name="Yahoo difere da B3", customdata=b3,
                marker=dict(symbol="circle-open", size=12, line=dict(width=2, color=tema.OURO)),
                hovertemplate="Yahoo: %{y:,.0f} · B3: %{customdata:,.2f}<extra>Difere da B3</extra>",
            ),
            row=1, col=1,
        )
    fig = _base(fig, df["data"], altura=440, direita=20)
    fig.update_yaxes(tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(showticklabels=False, showgrid=False, row=2, col=1)
    return fig
