import pandas as pd
import pytest

from src import indicadores as ind


def test_cdi_anualizado_valor_conferido():
    # 0,050788% ao dia -> 13,65% ao ano (CDI anualizado, série 4389 do BCB)
    assert ind.cdi_anualizado(0.050788) == pytest.approx(13.65, abs=0.01)


def test_ganho_real_valor_conferido():
    assert ind.ganho_real(13.65, 4.58) == pytest.approx(8.67, abs=0.01)


def test_ganho_real_nao_e_subtracao():
    assert ind.ganho_real(13.65, 4.58) != pytest.approx(13.65 - 4.58, abs=0.01)


def test_variacao_percentual():
    assert ind.variacao_percentual(110, 100) == pytest.approx(10)
    with pytest.raises(ValueError):
        ind.variacao_percentual(1, 0)


def test_base100_primeiro_valor_valido_e_100():
    s = pd.Series([None, 50.0, 100.0])
    r = ind.base100(s)
    assert r.iloc[1] == 100 and r.iloc[2] == 200
    with pytest.raises(ValueError):
        ind.base100(pd.Series([None, None], dtype=float))


def test_indice_taxa_base100_primeira_linha_100():
    r = ind.indice_taxa_base100(pd.Series([5.0, 10.0, 10.0]))
    assert list(r) == pytest.approx([100, 110, 121])


def _cdi_constante(dias=400, taxa=0.05):
    datas = pd.bdate_range("2025-01-01", periods=dias)
    return pd.DataFrame({"data": datas, "cdi": taxa})


def test_cdi_12m_sem_historico_suficiente_fica_fora():
    r = ind.cdi_acumulado_12m(_cdi_constante())
    assert r["data"].min() >= pd.Timestamp("2026-01-01")


def test_cdi_12m_composto_igual_ao_calculo_manual():
    cdi = _cdi_constante()
    r = ind.cdi_acumulado_12m(cdi)
    ultima = r["data"].iloc[-1]
    # conta os dias da janela (t-12 meses, t] e compõe 0,05% ao dia
    janela = cdi[(cdi["data"] > ultima - pd.DateOffset(months=12)) & (cdi["data"] <= ultima)]
    esperado = (1.0005 ** len(janela) - 1) * 100
    assert r["cdi_12m_pct"].iloc[-1] == pytest.approx(esperado, abs=0.01)
    # composto rende mais que a soma simples dos mesmos dias
    assert r["cdi_12m_pct"].iloc[-1] > 0.05 * len(janela)


def _ipca(meses, valor=1.0, inicio="2025-01-01"):
    return pd.DataFrame({"data": pd.date_range(inicio, periods=meses, freq="MS"), "ipca": valor})


def test_ipca_12m_constante_1pct():
    r = ind.ipca_acumulado_12m(_ipca(12))
    assert len(r) == 1
    assert r["ipca_12m_pct"].iloc[0] == pytest.approx(12.6825, abs=1e-3)


def test_ipca_12m_poucos_meses_vazio():
    assert ind.ipca_acumulado_12m(_ipca(11)).empty


def test_ipca_12m_mes_faltando_nao_inventa():
    df = _ipca(14).drop(index=5).reset_index(drop=True)
    r = ind.ipca_acumulado_12m(df)
    assert r.empty  # toda janela de 12 meses contém o buraco


def test_ipca_12m_exige_dia_1():
    df = _ipca(12)
    df["data"] = df["data"] + pd.Timedelta(days=4)
    with pytest.raises(ValueError):
        ind.ipca_acumulado_12m(df)


def test_ipca_indice_ancora_e_fim_de_mes():
    r = ind.ipca_indice_base100(_ipca(3), "2025-01-15")
    assert r["indice"].iloc[0] == 100
    assert r["data"].iloc[0] == pd.Timestamp("2025-01-15")
    assert r["data"].iloc[1] == pd.Timestamp("2025-01-31")
    assert r["indice"].iloc[-1] == pytest.approx(100 * 1.01**3)


def test_ipca_indice_sem_meses_gera_erro():
    with pytest.raises(ValueError):
        ind.ipca_indice_base100(_ipca(2), "2030-01-01")


def _s(datas, valores):
    return pd.DataFrame({"data": pd.to_datetime(datas), "valor": valores})


def test_alinhar_preenche_buracos_mas_nao_depois_do_ultimo_dado():
    a = _s(["2026-01-01", "2026-01-02", "2026-01-05"], [1, 2, 3])
    b = _s(["2026-01-01", "2026-01-03"], [10, 30])
    r = ind.alinhar_series({"a": a, "b": b})
    assert r.loc["2026-01-02", "b"] == 10  # preenchido
    assert r.loc["2026-01-03", "a"] == 2  # preenchido
    assert pd.isna(r.loc["2026-01-05", "b"])  # b acabou em 01-03: não inventa


def test_alinhar_nao_preenche_antes_do_primeiro_dado():
    a = _s(["2026-01-01", "2026-01-02"], [1, 2])
    b = _s(["2026-01-02"], [5])
    r = ind.alinhar_series({"a": a, "b": b})
    assert pd.isna(r.loc["2026-01-01", "b"])


def test_base100_comum_comeca_quando_todas_existem():
    a = _s(["2026-01-01", "2026-01-02"], [1, 2])
    b = _s(["2026-01-02"], [5])
    r = ind.base100_comum(ind.alinhar_series({"a": a, "b": b}))
    assert r.loc["2026-01-02", "a"] == 100 and r.loc["2026-01-02", "b"] == 100


def test_base100_comum_sem_data_comum_gera_erro():
    largo = pd.DataFrame({"a": [1.0, None], "b": [None, 2.0]})
    with pytest.raises(ValueError):
        ind.base100_comum(largo)


def test_recortar_janela_inclusivo():
    df = _s(["2026-01-01", "2026-01-02", "2026-01-03"], [1, 2, 3])
    r = ind.recortar_janela(df, "2026-01-02", "2026-01-03")
    assert list(r["valor"]) == [2, 3]
    assert len(ind.recortar_janela(df, "2026-01-02")) == 2