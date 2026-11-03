from datetime import date, datetime

import pandas as pd
import pytest

from dashboard import dados as d
from src import load

HOJE = date(2026, 11, 3)


def _dados(parcial_hoje=False):
    """Base sintética: ~2 anos de dias úteis, IPCA mensal, e um dia divergente."""
    dias = pd.bdate_range("2024-11-01", "2026-10-30")
    cdi = pd.DataFrame({"data": dias, "valor": 0.05})
    dolar = pd.DataFrame({"data": dias, "valor": [5.0 + 0.001 * i for i in range(len(dias))]})
    ibov = pd.DataFrame(
        {
            "data": dias,
            "fechamento": [100_000.0 + 10 * i for i in range(len(dias))],
            "volume": pd.array([1_000_000] * len(dias), dtype="Int64"),
            "parcial": False,
            "divergente": False,
        }
    )
    ibov.loc[100, "volume"] = pd.NA  # um dia sem volume
    ibov.loc[200, "divergente"] = True
    if parcial_hoje:
        extra = pd.DataFrame(
            {
                "data": [pd.Timestamp("2026-11-03")],
                "fechamento": [ibov["fechamento"].iloc[-1] + 500],
                "volume": pd.array([pd.NA], dtype="Int64"),
                "parcial": [True],
                "divergente": [False],
            }
        )
        ibov = pd.concat([ibov, extra], ignore_index=True)
    ipca = pd.DataFrame({"data": pd.date_range("2024-11-01", "2026-09-01", freq="MS"), "valor": 0.4})
    return {"cdi": cdi, "ipca": ipca, "dolar_ptax": dolar, "ibovespa": ibov}


def test_inicio_do_periodo():
    assert d.inicio_do_periodo("2026-10-30", "12M") == pd.Timestamp("2025-10-30")
    assert d.inicio_do_periodo("2026-10-30", "5A") == pd.Timestamp("2021-10-30")
    with pytest.raises(ValueError):
        d.inicio_do_periodo("2026-10-30", "7D")


def test_dados_ate_e_data_mais_antiga_das_series_diarias():
    dados = _dados()
    dados["cdi"] = dados["cdi"].iloc[:-3]  # CDI atrasado 3 dias
    p = d.construir_painel(dados, "12M")
    assert p.dados_ate == dados["cdi"]["data"].max()


def test_cartao_cdi_anualiza_composto():
    p = d.construir_painel(_dados(), "12M")
    cdi = p.cartoes[0]
    assert cdi.titulo == "CDI" and cdi.unidade == "a.a."
    assert cdi.valor == "13,42%"  # (1,0005^252 - 1) = 13,42%
    assert cdi.detalhe == "0,0500% ao dia"
    assert cdi.referencia == "Ref.: 30/10/2026"


def test_cartao_ipca_mostra_mes_de_referencia():
    p = d.construir_painel(_dados(), "12M")
    ipca = p.cartoes[1]
    assert ipca.referencia == "Ref.: set/2026"
    assert ipca.valor == "4,91%"  # 1,004^12 - 1
    assert "set/2026" in ipca.detalhe


def test_cartao_dolar_variacao_no_periodo():
    p = d.construir_painel(_dados(), "12M")
    dolar = p.cartoes[2]
    assert dolar.valor.startswith("R$ ") and dolar.tom == "positivo"
    assert dolar.detalhe.startswith("+") and dolar.detalhe.endswith("no período")


def test_variacao_depende_do_periodo():
    longo = d.construir_painel(_dados(), "5A").cartoes[3].detalhe
    curto = d.construir_painel(_dados(), "1M").cartoes[3].detalhe
    assert longo != curto


def test_dia_parcial_so_no_cartao_nunca_nos_graficos():
    p = d.construir_painel(_dados(parcial_hoje=True), "12M", ultima_execucao=datetime(2026, 11, 3, 13, 46))
    ibov = p.cartoes[3]
    assert ibov.referencia == "Ref.: 03/11/2026 · parcial 13:46"
    assert p.resumo_ibovespa.rotulo == "PARCIAL · 13:46"
    assert pd.Timestamp("2026-11-03") not in set(p.ibovespa["data"])
    assert pd.Timestamp("2026-11-03") not in set(p.comparativo.index)
    assert p.dados_ate == pd.Timestamp("2026-10-30")  # "dados até" ignora o parcial


def test_parcial_sem_horario_quando_execucao_foi_outro_dia():
    p = d.construir_painel(_dados(parcial_hoje=True), "12M", ultima_execucao=datetime(2026, 11, 2, 9, 0))
    assert p.cartoes[3].referencia == "Ref.: 03/11/2026 · parcial"
    assert p.resumo_ibovespa.rotulo == "PARCIAL"


def test_resumo_ibovespa_fechado():
    p = d.construir_painel(_dados(), "12M")
    assert p.resumo_ibovespa.rotulo == "FECHAMENTO"
    assert p.resumo_ibovespa.variacao_dia.endswith("no dia")


def test_comparativo_comeca_em_100_e_alinha_as_series():
    p = d.construir_painel(_dados(), "12M")
    primeira = p.comparativo.iloc[0]
    assert list(primeira) == pytest.approx([100, 100, 100])
    assert set(p.comparativo.columns) == {"cdi", "ibovespa", "dolar"}
    assert not p.comparativo.isna().any().any()


def test_comparativo_cdi_composto_bate_com_calculo_manual():
    p = d.construir_painel(_dados(), "12M")
    n = len(p.comparativo) - 1  # dias de rendimento após a data-base
    assert p.comparativo["cdi"].iloc[-1] == pytest.approx(100 * 1.0005**n)


def test_serie_que_acaba_antes_fica_vazia_no_fim_do_comparativo():
    dados = _dados()
    dados["dolar_ptax"] = dados["dolar_ptax"].iloc[:-2]  # dólar atrasado 2 dias
    p = d.construir_painel(dados, "12M")
    assert p.comparativo["dolar"].iloc[-1] != p.comparativo["dolar"].iloc[-1]  # NaN
    assert not pd.isna(p.comparativo["cdi"].iloc[-1])


def test_ipca_pontos_ancora_em_100_na_data_base():
    p = d.construir_painel(_dados(), "12M")
    assert p.ipca_pontos["indice"].iloc[0] == 100
    assert p.ipca_pontos["data"].iloc[0] == p.comparativo.index[0]
    assert p.ipca_pontos["indice"].iloc[-1] > 100


def test_ipca_pontos_ausente_quando_periodo_nao_tem_mes_divulgado():
    p = d.construir_painel(_dados(), "1M")  # out/2026 ainda não saiu
    assert p.ipca_pontos is None


def test_ganho_real_compara_o_mesmo_periodo():
    p = d.construir_painel(_dados(), "12M")
    ipca_12m = 1.004**12 - 1
    # CDI de 12 meses até 30/09/2026: dias úteis da janela (30/09/2025, 30/09/2026]
    dias = pd.bdate_range("2024-11-01", "2026-10-30")
    janela = [x for x in dias if pd.Timestamp("2025-09-30") < x <= pd.Timestamp("2026-09-30")]
    cdi_12m = 1.0005 ** len(janela) - 1
    esperado = ((1 + cdi_12m) / (1 + ipca_12m) - 1) * 100
    assert p.juros.ganho_real == pytest.approx(esperado, abs=0.01)
    assert p.juros.mes_ref == "set/2026"


def test_juros_reais_nunca_mostra_menos_de_12_meses():
    p = d.construir_painel(_dados(), "1M")  # período curto, mas o gráfico não se limita a ele
    assert len(p.juros.cdi_12m) > 200  # todo o CDI 12m disponível (~1 ano), não só ~22 dias


def test_ipca_12m_fica_no_fim_do_mes():
    p = d.construir_painel(_dados(), "12M")
    assert (p.juros.ipca_12m["data"].dt.is_month_end).all()


def test_ibovespa_painel_mantem_volume_vazio():
    p = d.construir_painel(_dados(), "5A", ocultar_divergentes=False)
    assert p.ibovespa["volume"].isna().sum() == 1
    assert p.ibovespa["divergente"].sum() == 1
    assert not p.ibovespa["fechamento"].isna().any()  # com marcação, o valor aparece


def test_padrao_e_mostrar_dia_divergente_como_na():
    assert d.OCULTAR_DIVERGENTES_PADRAO is True
    dados = _dados()
    dia = dados["ibovespa"].loc[200, "data"]
    p = d.construir_painel(dados, "5A")  # sem passar nada: usa o padrão
    assert p.ibovespa.loc[p.ibovespa["data"] == dia, "fechamento"].isna().all()
    assert pd.isna(p.comparativo.loc[dia, "ibovespa"])  # buraco também no comparativo
    assert not pd.isna(p.comparativo.loc[dia, "cdi"])  # as outras séries seguem normais


def test_nao_ocultar_mantem_valor_e_marca():
    dados = _dados()
    dia = dados["ibovespa"].loc[200, "data"]
    p = d.construir_painel(dados, "5A", ocultar_divergentes=False)
    assert not pd.isna(p.comparativo.loc[dia, "ibovespa"])
    assert not p.ibovespa.loc[p.ibovespa["data"] == dia, "fechamento"].isna().any()
    assert p.ibovespa.loc[p.ibovespa["data"] == dia, "divergente"].all()


def test_tabela_mostra_valor_original_mesmo_no_dia_divergente():
    dados = _dados()
    dia = dados["ibovespa"].loc[200, "data"]
    t = d.construir_painel(dados, "5A").tabela
    linha = t[t["Data"] == dia].iloc[0]
    assert not pd.isna(linha["Ibovespa (pontos)"]) and linha["Difere da B3"].startswith("sim")


def test_tabela_tem_so_dados_reais_e_sinaliza():
    p = d.construir_painel(_dados(parcial_hoje=True), "12M")
    t = p.tabela
    assert t["Data"].is_monotonic_increasing
    assert t["Data"].min() >= p.inicio
    assert (t["Dia parcial"] == "sim").sum() == 1
    assert pd.Timestamp("2026-11-03") in set(t["Data"])  # a tabela mostra tudo, inclusive o parcial


def test_csv_para_excel_brasileiro():
    p = d.construir_painel(_dados(), "1M")
    bruto = d.csv_bytes(p.tabela)
    assert bruto.startswith(b"\xef\xbb\xbf")
    texto = bruto.decode("utf-8-sig")
    primeira, segunda = texto.splitlines()[:2]
    assert primeira.startswith("Data;CDI (% ao dia);Dólar PTAX venda (R$)")
    assert segunda.split(";")[0].count("/") == 2  # dd/mm/aaaa
    assert "," in segunda  # vírgula decimal


def test_tabela_vazia_gera_erro_com_instrucao():
    dados = _dados()
    dados["cdi"] = dados["cdi"].iloc[0:0]
    with pytest.raises(ValueError, match="python3 -m src.pipeline"):
        d.construir_painel(dados, "12M")


def test_so_dia_parcial_no_ibovespa_gera_erro():
    dados = _dados(parcial_hoje=True)
    dados["ibovespa"] = dados["ibovespa"][dados["ibovespa"]["parcial"]]
    with pytest.raises(ValueError, match="parcial"):
        d.construir_painel(dados, "12M")


def test_periodo_invalido_gera_erro():
    with pytest.raises(ValueError):
        d.construir_painel(_dados(), "99X")


def test_ler_dados_do_banco_em_memoria():
    conn = load.conectar(":memory:")
    load.criar_tabelas(conn)
    base = _dados(parcial_hoje=True)
    load.salvar_serie_sgs(conn, "cdi", base["cdi"].rename(columns={"valor": "cdi"}), "cdi")
    load.salvar_serie_sgs(conn, "ipca", base["ipca"].rename(columns={"valor": "ipca"}), "ipca")
    load.salvar_serie_sgs(conn, "dolar_ptax", base["dolar_ptax"].rename(columns={"valor": "dolar_ptax"}), "dolar_ptax")
    load.salvar_ibovespa(conn, base["ibovespa"])
    lido = d.ler_dados(conn)
    conn.close()
    p = d.construir_painel(lido, "12M", ultima_execucao=datetime(2026, 11, 3, 13, 46))
    assert p.cartoes[3].referencia.endswith("parcial 13:46")
    assert p.comparativo.iloc[0].tolist() == pytest.approx([100, 100, 100])


def test_tabela_mostra_valor_da_b3_no_dia_divergente_conhecido():
    from src import config

    dia, b3 = next(iter(config.DIAS_DIVERGENTES_IBOVESPA.items()))  # 10/11/2023
    base = _dados()
    base["ibovespa"].loc[200, "data"] = pd.Timestamp(dia)  # coloca o dia conhecido na base
    base["cdi"].loc[200, "data"] = pd.Timestamp(dia)
    base["dolar_ptax"].loc[200, "data"] = pd.Timestamp(dia)
    base["ibovespa"].loc[200, "divergente"] = True
    t = d.construir_painel(base, "5A").tabela
    assert t.loc[t["Data"] == pd.Timestamp(dia), "Difere da B3"].iloc[0] == "sim · B3: 120.568,14"


def test_tabela_nao_tem_valores_nulos_nas_colunas_de_texto():
    dados = _dados()
    dados["ibovespa"] = dados["ibovespa"].drop(index=50).reset_index(drop=True)  # dia sem Ibovespa
    t = d.construir_painel(dados, "5A").tabela
    assert not t["Dia parcial"].isna().any() and not t["Difere da B3"].isna().any()


def test_formatar_tabela_padrao_brasileiro_e_dois_tipos_de_vazio():
    dados = _dados()
    dia_sem_volume = dados["ibovespa"].loc[100, "data"]  # existe, mas o volume veio vazio
    dia_sem_ibov = dados["ibovespa"].loc[50, "data"]
    dados["ibovespa"] = dados["ibovespa"].drop(index=50).reset_index(drop=True)
    painel = d.construir_painel(dados, "5A")
    f = d.formatar_tabela(painel.tabela)
    por_data = f.set_index("Data")

    assert f["Data"].iloc[0].count("/") == 2  # dd/mm/aaaa, sem horário
    assert por_data.loc[dia_sem_volume.strftime("%d/%m/%Y"), "Volume (Yahoo Finance)"] == "N/A"
    linha = por_data.loc[dia_sem_ibov.strftime("%d/%m/%Y")]
    assert linha["Ibovespa (pontos)"] == "—" and linha["Volume (Yahoo Finance)"] == "—"
    assert por_data["CDI (% ao dia)"].iloc[0] == "0,0500"
    assert not f.isin(["None", "nan", "NaN", "<NA>"]).any().any()
