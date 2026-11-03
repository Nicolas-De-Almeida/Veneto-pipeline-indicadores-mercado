"""Dashboard de indicadores de mercado (Streamlit).
Como rodar (na raiz do projeto, com o .venv ativo e depois de rodar o pipeline):
    streamlit run dashboard/app.py
Streamlit executa este arquivo do começo ao fim a cada clique do usuário.
Por isso o que é pesado (ler o banco) fica em cache."""
import sys
from pathlib import Path

# O Streamlit coloca a pasta dashboard/ (e não a raiz) no caminho de imports;
# sem esta linha, `from src import ...` não seria encontrado.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import inspect
import os 

import streamlit as st

from dashboard import componentes, dados, graficos, tema
from dashboard import formatos as fmt 
from src import config, load 
CAMINHO_LOGO = Path(__file__).resolve().parent / "assets" / "logo.png"

_USA_WIDTH = "width" in inspect.signature(st.plotly_chart).parameters


def _html(texto: str) -> None:
    st.markdown(texto, unsafe_allow_html=True)


def _mostrar(figura) -> None:
    if _USA_WIDTH:
        st.plotly_chart(figura, width="stretch", config=graficos.CONFIG_PLOTLY)
    else:
        st.plotly_chart(figura, use_container_width=True, config=graficos.CONFIG_PLOTLY)


def _caixa():
    """Painel com borda (versões antigas do Streamlit não têm `border`)."""
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


@st.cache_data(show_spinner=False)
def _carregar(caminho: str, assinatura: float):
    """Lê o banco. `assinatura` (hora de modificação do arquivo) invalida o cache
    quando o pipeline roda de novo, sem precisar reiniciar o dashboard."""
    conn = load.conectar(caminho)
    try:
        return dados.ler_dados(conn), load.ler_ultima_execucao(conn)
    finally:
        conn.close()


def _seletor_periodo() -> None:
    """Botões 1M | 6M | 12M | 3A | 5A. O valor fica em st.session_state['periodo']."""
    opcoes = list(dados.PERIODOS)
    if hasattr(st, "segmented_control"):
        st.segmented_control("Período", opcoes, default=dados.PERIODO_PADRAO,
                             key="periodo", label_visibility="collapsed")
    else:
        st.radio("Período", opcoes, index=opcoes.index(dados.PERIODO_PADRAO),
                 key="periodo", horizontal=True, label_visibility="collapsed")


def main() -> None:
    st.set_page_config(page_title="Indicadores de Mercado · Vêneto Family Office", layout="wide")
    # CSS em uma linha só, evita que o markdown interprete recuos/linhas em branco.
    _html("<style>" + " ".join(l.strip() for l in tema.CSS.splitlines()) + "</style>")

    caminho = config.CAMINHO_BANCO
    if not caminho.exists():
        st.error("Banco de dados não encontrado. Rode primeiro o pipeline: `python3 -m src.pipeline`")
        st.stop()
    brutos, ultima_execucao = _carregar(str(caminho), os.path.getmtime(caminho))

    # O botão de período aparece DEPOIS do cabeçalho, mas o cabeçalho precisa
    # dos dados; por isso lê a escolha direto do session_state.
    periodo = st.session_state.get("periodo") or dados.PERIODO_PADRAO
    try:
        painel = dados.construir_painel(brutos, periodo, ultima_execucao)
    except ValueError as erro:
        st.error(str(erro))
        st.stop()

    _html(componentes.cabecalho(painel, componentes.logo_base64(CAMINHO_LOGO)))

    esquerda, direita = st.columns([1, 1])
    with esquerda:
        _seletor_periodo()
    with direita:
        _html(componentes.nota_periodo(periodo))

    _html(componentes.cartoes(painel.cartoes))

    # Desempenho comparado 
    with _caixa():
        _html(componentes.cabecalho_painel(
            "DESEMPENHO COMPARADO", "Quanto rendeu R$ 100",
            "Evolução de um investimento hipotético, com base inicial igual a 100.",
        ))
        _mostrar(graficos.fig_comparativo(painel))
        nota = f"Base 100 em {fmt.data_br(painel.comparativo.index[0])} · Valores nominais"
        if painel.ipca_pontos is None:
            nota += " · IPCA do período ainda não divulgado"
        _html(componentes.rodape_painel(nota))

    # Juros reais e câmbio
    col_juros, col_cambio = st.columns(2)
    with col_juros, _caixa():
        j = painel.juros
        _html(componentes.cabecalho_painel(
            "JUROS REAIS", "CDI 12 meses vs. IPCA 12 meses", "Rendimento acima da inflação.",
            "GANHO REAL", fmt.percentual(j.ganho_real, 2), "", ouro=True,
        ))
        _mostrar(graficos.fig_juros_reais(painel))
        ate = f" até {j.mes_ref}" if j.mes_ref else ""
        _html(componentes.rodape_painel(
            f"Ganho real: (1 + CDI) / (1 + IPCA) − 1, ambos acumulados em 12 meses{ate}"
        ))
    with col_cambio, _caixa():
        _html(componentes.cabecalho_painel(
            "CÂMBIO", "Dólar PTAX venda (R$)", "Reais por dólar dos Estados Unidos.",
            "ÚLTIMO", painel.cartoes[2].valor,
        ))
        _mostrar(graficos.fig_cambio(painel))
        _html(componentes.rodape_painel("Cotação PTAX de venda, divulgada pelo Banco Central"))

    # Ibovespa
    with _caixa():
        r = painel.resumo_ibovespa
        _html(componentes.cabecalho_painel(
            "RENDA VARIÁVEL", "Ibovespa (pontos)",
            "Fechamento diário e volume negociado (fonte: Yahoo Finance).",
            r.rotulo, r.valor, r.variacao_dia, r.tom,
        ))
        _mostrar(graficos.fig_ibovespa(painel))
        notas = ["Passe o cursor sobre o gráfico para consultar os valores."]
        if painel.ibovespa["volume"].isna().any():
            notas.append("Dias sem barra de volume: o Yahoo não informou o dado.")
        for dia in painel.ibovespa.loc[painel.ibovespa["divergente"], "data"]:
            b3 = config.DIAS_DIVERGENTES_IBOVESPA.get(dia.date())
            if b3 is None:
                continue
            if dados.OCULTAR_DIVERGENTES_PADRAO:
                notas.append(
                    f"{fmt.data_br(dia)}: N/A, pois o Yahoo difere da B3 neste dia (B3: {fmt.numero(b3, 2)})."
                )
            else:
                notas.append(f"○ {fmt.data_br(dia)}: o Yahoo difere da B3 (B3: {fmt.numero(b3, 2)}).")
        _html(componentes.rodape_painel(" ".join(notas)))

    # Dados completos
    with st.expander("Ver e baixar os dados do período"):
        st.dataframe(painel.tabela, hide_index=True)
        st.download_button(
            "Baixar CSV", data=dados.csv_bytes(painel.tabela),
            file_name="indicadores_mercado.csv", mime="text/csv",
        )

    _html(componentes.rodape(tema.AUTOR, tema.FONTES))


main()
