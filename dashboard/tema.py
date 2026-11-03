"""Identidade visual do dashboard.
Mudar a aparência = mexer só aqui e nos gráficos.
"""

# Cores 
NAVY = "#101A2E"          # azul-marinho: cabeçalho, rodapé, Ibovespa
OURO = "#A67C00"          # dourado escuro: legível sobre fundo branco (CDI)
OURO_CLARO = "#C9AA5E"    # dourado claro: textos sobre o fundo marinho
AZUL = "#2A7AB0"          # dólar
CINZA = "#6B7280"         # textos secundários e IPCA
CINZA_CLARO = "#C9CCD6"   # barras de volume
GRADE = "#E5E7EB"         # linhas de grade
POSITIVO = "#3D6B4F"      # variação positiva
NEGATIVO = "#A33B3B"      # variação negativa

# Textos fixos 
EYEBROW = "VÊNETO FAMILY OFFICE"
TITULO = "Indicadores de Mercado"
SUBTITULO = "CDI · IPCA · Dólar · Ibovespa"
AUTOR = "Nicolas De Almeida"  # ;)
FONTES = "Banco Central – SGS · IBGE · Yahoo Finance"

# Logo 
ALTURA_LOGO_PX = 56  # a logo é azul-marinho; no cabeçalho marinho ela vira branca (filtro CSS)

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=EB+Garamond:wght@400;500&display=swap');

html, body, [class*="st-"], .stApp {{ font-family: 'DM Sans', system-ui, -apple-system, sans-serif; }}
.stApp {{ background: #FFFFFF; color: {NAVY}; }}

/* some com o menu/cabeçalho padrão do Streamlit */
#MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
.block-container, [data-testid="stMainBlockContainer"] {{
    max-width: 1240px; padding-top: 1.2rem; padding-bottom: 2rem;
}}

.vf-serif {{ font-family: 'EB Garamond', Georgia, 'Times New Roman', serif; }}

/* cabeçalho */
.vf-header {{
    background: {NAVY}; color: #fff; display: flex; align-items: center;
    gap: 28px; padding: 22px 32px; border-bottom: 3px solid {OURO_CLARO}; margin-bottom: 22px;
}}
.vf-logo {{ height: {ALTURA_LOGO_PX}px; width: auto; filter: brightness(0) invert(1); }}
.vf-header-meio {{ flex: 1; border-left: 1px solid rgba(255,255,255,.18); padding-left: 28px; }}
.vf-eyebrow {{ color: {OURO_CLARO}; letter-spacing: .22em; font-size: 12px; font-weight: 500; text-transform: uppercase; }}
.vf-titulo {{ font-family: 'EB Garamond', Georgia, serif; font-size: 32px; line-height: 1.15; margin: 4px 0; }}
.vf-subtitulo {{ color: rgba(255,255,255,.75); font-size: 14px; }}
.vf-status {{ text-align: right; border-left: 1px solid rgba(255,255,255,.18); padding-left: 28px; }}
.vf-status-rotulo {{ color: {OURO_CLARO}; letter-spacing: .2em; font-size: 12px; font-weight: 500; }}
.vf-status-data {{ font-weight: 700; font-size: 15px; margin-top: 6px; }}
.vf-status-nota {{ color: rgba(255,255,255,.7); font-size: 13px; }}

.vf-nota-periodo {{ text-align: right; color: {CINZA}; font-size: 14px; padding-top: 8px; }}
.vf-nota-periodo b {{ color: {NAVY}; }}

/* cartões  */
.vf-cartoes {{ display: grid; grid-template-columns: repeat(4, 1fr); border-top: 1px solid {GRADE};
    border-bottom: 1px solid {GRADE}; margin: 14px 0 24px 0; }}
.vf-cartao {{ padding: 18px 22px; border-right: 1px solid {GRADE}; }}
.vf-cartao:last-child {{ border-right: none; }}
.vf-cartao-titulo {{ font-weight: 700; font-size: 15px; display: flex; justify-content: space-between; }}
.vf-cartao-ponto {{ color: {OURO}; }}
.vf-cartao-valor {{ font-family: 'EB Garamond', Georgia, serif; font-size: 38px; line-height: 1.2; margin-top: 6px; }}
.vf-cartao-unidade {{ font-family: 'DM Sans', sans-serif; font-size: 14px; color: {CINZA}; margin-left: 4px; }}
.vf-cartao-detalhe {{ font-size: 14px; color: {CINZA}; margin-top: 2px; }}
.vf-positivo {{ color: {POSITIVO}; font-weight: 700; }}
.vf-negativo {{ color: {NEGATIVO}; font-weight: 700; }}
.vf-cartao-ref {{ font-size: 12px; color: {CINZA}; margin-top: 8px; opacity: .85; }}

/* painéis */
.vf-painel-cab {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 4px; }}
.vf-painel-eyebrow {{ color: {CINZA}; letter-spacing: .2em; font-size: 12px; font-weight: 500; text-transform: uppercase; }}
.vf-painel-titulo {{ font-family: 'EB Garamond', Georgia, serif; font-size: 24px; margin: 4px 0 2px; }}
.vf-painel-sub {{ color: {CINZA}; font-size: 14px; }}
.vf-painel-dir {{ text-align: right; border-left: 1px solid {GRADE}; padding-left: 18px; min-width: 130px; }}
.vf-painel-dir-rotulo {{ color: {CINZA}; letter-spacing: .15em; font-size: 10px; text-transform: uppercase; }}
.vf-painel-dir-valor {{ font-family: 'EB Garamond', Georgia, serif; font-size: 26px; }}
.vf-ouro {{ color: {OURO}; }}
.vf-rodape-painel {{ color: {CINZA}; font-size: 13px; border-top: 1px solid {GRADE}; padding-top: 8px; margin-top: 4px; }}

/* rodapé */
.vf-rodape {{ background: {NAVY}; color: #fff; display: flex; justify-content: space-between;
    align-items: flex-end; gap: 20px; padding: 24px 32px; margin-top: 26px; }}
.vf-rodape-rotulo {{ color: {OURO_CLARO}; letter-spacing: .2em; font-size: 12px; font-weight: 500; }}
.vf-rodape-texto {{ color: rgba(255,255,255,.8); font-size: 14px; margin-top: 6px; }}
.vf-rodape-autor b {{ color: #fff; }}

[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 0 !important; border-color: #D9DCE3 !important; }}

@media (max-width: 900px) {{
    .vf-cartoes {{ grid-template-columns: repeat(2, 1fr); }}
    .vf-header, .vf-rodape {{ flex-direction: column; align-items: flex-start; }}
    .vf-status {{ text-align: left; border-left: none; padding-left: 0; }}
}}
"""
