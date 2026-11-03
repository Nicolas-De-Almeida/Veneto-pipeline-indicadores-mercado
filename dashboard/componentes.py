"""Blocos de HTML do dashboard (cabeçalho, cartões, rodapé...).
São funções que só devolvem texto, então dá para testá-las.
1. `st.markdown` trata linhas com 4+ espaços como código e `$...$` como fórmula
   matemática. Por isso o HTML sai numa linha só e o '$' vira `&#36;`.
2. Todo texto passa por `_seguro`, que impede que algo digitado vire HTML."""
import base64
import html
from pathlib import Path

from dashboard import formatos as fmt
from dashboard import tema


def _seguro(texto) -> str:
    """Escapa HTML e protege o '$' (senão 'R$ 5,00 ... R$ 6,00' vira fórmula)."""
    return html.escape(str(texto)).replace("$", "&#36;")


def _linha_unica(texto: str) -> str:
    return "".join(linha.strip() for linha in texto.splitlines())


def logo_base64(caminho) -> str | None:
    """Lê a imagem da logo e devolve em base64 (para embutir no HTML); None se não existir."""
    caminho = Path(caminho)
    if not caminho.is_file():
        return None
    return base64.b64encode(caminho.read_bytes()).decode("ascii")


def cabecalho(painel, logo_b64: str | None) -> str:
    logo = (
        f'<img class="vf-logo" alt="Logo" src="data:image/png;base64,{logo_b64}">' if logo_b64 else ""
    )
    execucao = ""
    if painel.ultima_execucao is not None:
        execucao = (
            f'<div class="vf-status-nota">Última execução do pipeline: '
            f'{_seguro(painel.ultima_execucao.strftime("%d/%m/%Y %H:%M"))}</div>'
        )
    return _linha_unica(f"""
        <div class="vf-header"><div class="vf-header-inner">
            {logo}
            <div class="vf-header-meio">
                <div class="vf-eyebrow">{_seguro(tema.EYEBROW)}</div>
                <div class="vf-titulo">{_seguro(tema.TITULO)}</div>
                <div class="vf-subtitulo">{_seguro(tema.SUBTITULO)}</div>
            </div>
            <div class="vf-status">
                <div class="vf-status-rotulo">DADOS ATUALIZADOS</div>
                <div class="vf-status-data">Dados até {_seguro(fmt.data_br(painel.dados_ate))}</div>
                {execucao}
            </div>
        </div></div>
    """)


def nota_periodo(periodo: str) -> str:
    return (
        '<div class="vf-nota-periodo">Variações calculadas sobre o período selecionado: '
        f"<b>{_seguro(periodo)}</b></div>"
    )


def cartoes(lista) -> str:
    blocos = []
    for c in lista:
        unidade = f'<span class="vf-cartao-unidade">{_seguro(c.unidade)}</span>' if c.unidade else ""
        classe = {"positivo": "vf-positivo", "negativo": "vf-negativo"}.get(c.tom, "")
        blocos.append(f"""
            <div class="vf-cartao">
                <div class="vf-cartao-titulo"><span>{_seguro(c.titulo)}</span><span class="vf-cartao-ponto">•</span></div>
                <div class="vf-cartao-valor">{_seguro(c.valor)}{unidade}</div>
                <div class="vf-cartao-detalhe"><span class="{classe}">{_seguro(c.detalhe)}</span></div>
                <div class="vf-cartao-ref">{_seguro(c.referencia)}</div>
            </div>
        """)
    return _linha_unica('<div class="vf-cartoes">' + "".join(blocos) + "</div>")


def cabecalho_painel(
    eyebrow: str, titulo: str, subtitulo: str,
    rotulo: str = "", valor: str = "", detalhe: str = "", tom: str = "neutro", ouro: bool = False,
) -> str:
    """Topo de um painel: títulos à esquerda e, se houver, um número-chave à direita."""
    direita = ""
    if valor:
        classe_valor = "vf-painel-dir-valor" + (" vf-ouro" if ouro else "")
        classe_det = {"positivo": "vf-positivo", "negativo": "vf-negativo"}.get(tom, "")
        det = f'<div class="{classe_det}" style="font-size:14px">{_seguro(detalhe)}</div>' if detalhe else ""
        direita = f"""
            <div class="vf-painel-dir">
                <div class="vf-painel-dir-rotulo">{_seguro(rotulo)}</div>
                <div class="{classe_valor}">{_seguro(valor)}</div>
                {det}
            </div>
        """
    return _linha_unica(f"""
        <div class="vf-painel-cab">
            <div>
                <div class="vf-painel-eyebrow">{_seguro(eyebrow)}</div>
                <div class="vf-painel-titulo">{_seguro(titulo)}</div>
                <div class="vf-painel-sub">{_seguro(subtitulo)}</div>
            </div>
            {direita}
        </div>
    """)


def rodape_painel(texto: str) -> str:
    return f'<div class="vf-rodape-painel">{_seguro(texto)}</div>'


def rodape(autor: str, fontes: str) -> str:
    return _linha_unica(f"""
        <div class="vf-rodape"><div class="vf-rodape-inner">
            <div>
                <div class="vf-rodape-rotulo">FONTES</div>
                <div class="vf-rodape-texto">{_seguro(fontes)}</div>
            </div>
            <div class="vf-rodape-texto vf-rodape-autor">Case técnico desenvolvido por <b>{_seguro(autor)}</b></div>
        </div></div>
    """)
