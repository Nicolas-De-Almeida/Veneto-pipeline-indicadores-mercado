import pandas as pd

from dashboard import formatos as fmt


def test_numero_padrao_brasileiro():
    assert fmt.numero(1234.5, 2) == "1.234,50"
    assert fmt.numero(167921.796875, 0) == "167.922"
    assert fmt.numero(0.050788, 4) == "0,0508"
    assert fmt.numero(-3.456, 2) == "-3,46"
    assert fmt.numero(1234567.891, 1) == "1.234.567,9"


def test_numero_vazio_vira_nd():
    assert fmt.numero(None) == "N/D"
    assert fmt.numero(float("nan")) == "N/D"
    assert fmt.numero(pd.NA) == "N/D"


def test_percentual_com_e_sem_sinal():
    assert fmt.percentual(4.58) == "4,58%"
    assert fmt.percentual(2.05, 2, com_sinal=True) == "+2,05%"
    assert fmt.percentual(-0.5, 2, com_sinal=True) == "-0,50%"
    assert fmt.percentual(None) == "N/D"


def test_datas_em_portugues():
    assert fmt.data_br("2026-10-30") == "30/10/2026"
    assert fmt.mes_ano("2026-09-01") == "set/2026"
    assert fmt.mes_ano_curto("2021-10-29") == "out de 21"
    assert fmt.mes_ano("2026-12-01") == "dez/2026"


def test_rotulos_eixo_inclui_primeira_e_ultima():
    datas = pd.bdate_range("2021-11-01", "2026-10-30")
    pos, textos = fmt.rotulos_eixo(datas, 6)
    assert len(pos) == len(textos) == 6
    assert pos[0] == datas[0] and pos[-1] == datas[-1]
    assert textos[0] == "nov de 21" and textos[-1] == "out de 26"


def test_rotulos_eixo_poucas_datas_e_vazio():
    pos, textos = fmt.rotulos_eixo(pd.to_datetime(["2026-01-05", "2026-01-06"]), 6)
    assert len(pos) == 2
    assert fmt.rotulos_eixo([], 6) == ([], [])
