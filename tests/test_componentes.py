from datetime import datetime
from types import SimpleNamespace

import pandas as pd

from dashboard import componentes as c
from dashboard.dados import Cartao


def _painel(execucao=datetime(2026, 11, 2, 13, 46)):
    return SimpleNamespace(dados_ate=pd.Timestamp("2026-10-30"), ultima_execucao=execucao)


def test_html_sai_em_uma_linha_so():
    for html in (
        c.cabecalho(_painel(), None),
        c.cartoes([Cartao("CDI", "13,65%", "a.a.", "0,0508% ao dia", "Ref.: 30/10/2026")]),
        c.cabecalho_painel("EYEBROW", "Título", "Sub", "ÚLTIMO", "R$ 5,5007"),
        c.rodape("Fulano", "Fontes"),
    ):
        assert "\n" not in html


def test_cifrao_e_protegido_contra_formula():
    html = c.cartoes([Cartao("Dólar", "R$ 5,5007", "", "x", "Ref.: y")])
    assert "$" not in html and "R&#36; 5,5007" in html


def test_texto_nao_vira_html():
    html = c.cartoes([Cartao("<script>x</script>", "1", "", "d", "r")])
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_cabecalho_mostra_data_e_execucao():
    html = c.cabecalho(_painel(), None)
    assert "Dados até 30/10/2026" in html
    assert "Pipeline executado em 02/11/2026 13:46" in html
    assert "<img" not in html  # sem logo


def test_cabecalho_sem_execucao_e_com_logo():
    html = c.cabecalho(_painel(None), "QUJD")
    assert "Pipeline executado" not in html
    assert 'src="data:image/png;base64,QUJD"' in html


def test_logo_base64(tmp_path):
    assert c.logo_base64(tmp_path / "nao_existe.png") is None
    arq = tmp_path / "logo.png"
    arq.write_bytes(b"ABC")
    assert c.logo_base64(arq) == "QUJD"


def test_cartao_aplica_cor_da_variacao():
    positivo = c.cartoes([Cartao("a", "1", "", "+1%", "r", "positivo")])
    negativo = c.cartoes([Cartao("a", "1", "", "-1%", "r", "negativo")])
    assert "vf-positivo" in positivo and "vf-negativo" in negativo


def test_painel_sem_numero_chave_nao_tem_coluna_direita():
    assert "vf-painel-dir" not in c.cabecalho_painel("E", "T", "S")
    assert "vf-painel-dir" in c.cabecalho_painel("E", "T", "S", "R", "V")
