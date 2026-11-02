"""Etapa de CARREGAMENTO: grava os dados já limpos num banco SQLite.

Uma tabela por série: cdi, ipca, dolar_ptax (data, valor) e ibovespa
(data, fechamento, volume, parcial, divergente). Datas são guardadas como
texto 'AAAA-MM-DD'. Só entram datas REAIS, não fiz para feriados ou algo do tipo(ainda)."""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src import config

TABELAS_SGS = tuple(config.SERIES_SGS) # ('cdi', 'ipca', 'dolar_ptax')
TABELA_IBOVESPA = "ibovespa"
TABELAS = TABELAS_SGS + (TABELA_IBOVESPA,)

def conectar(caminho=None) -> sqlite3.Connection:
    """Abre (ou cria) o banco. Só usar ':memory:' para rodar os testes."""
    caminho = config.CAMINHO_BANCO if caminho is None else caminho
    if str(caminho) != ":memory:":
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(caminho))

def criar_tabelas(conn: sqlite3.Connection) -> None:
    """Cria a tabelas se ainda não existirem(pode rodar quantas vezes quiser)."""
    with conn: # 'with' = transação; ou grava tudo, ou nada
        for tabela in TABELAS_SGS:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {tabela} ("
                "data TEXT PRIMARY KEY, valor REAL NOT NULL)"
            )
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {TABELA_IBOVESPA} ("
            "data TEXT PRIMARY KEY, fechamento REAL NOT NULL, volume INTEGER, "
            "parcial INTEGER NOT NULL, divergente INTEGER NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS metadados ("
            "chave TEXT PRIMARY KEY, valor TEXT NOT NULL)"
        )

def _validar_tabela(tabela: str, permitidas: tuple) -> None:
    # Nome da tabela não pode ir como pâramentro, só nome fixos das listas
    if tabela not in permitidas:
        raise ValueError(f"Tabela inválida: {tabela!r}. Use uma de {permitidas}.")


def _texto_data(datas: pd.Series) -> list:
    return [d.strftime("%Y-%m-%d") for d in pd.to_datetime(datas)]


def salvar_serie_sgs(conn, tabela: str, df: pd.DataFrame, nome_valor: str) -> int:
    """Grava uma série do SGS (colunas 'data' e `nome_valor`). Devolve o número de linhas.
    Usa INSERT OR REPLACE; e se a data já existe, atualiza. Rodar duas vezes
    com os mesmos dados não duplica nada."""
    _validar_tabela(tabela, TABELAS_SGS)
    if df is None or df.empty:
        raise ValueError(f"Nada para gravar em {tabela}: tabela vazia.")
    if df[nome_valor].isna().any():
        raise ValueError(f"{tabela}: há valores vazios; não gravo dado incompleto.")
    linhas = list(zip(_texto_data(df["data"]), df[nome_valor].astype(float)))
    with conn:
        conn.executemany(f"INSERT OR REPLACE INTO {tabela} (data, valor) VALUES (?, ?)", linhas)
    return len(linhas)


def salvar_ibovespa(conn, df: pd.DataFrame) -> int:
    """Grava o Ibovespa tratado (data, fechamento, volume, parcial, divergente)."""
    if df is None or df.empty:
        raise ValueError("Nada para gravar em ibovespa, tabela vazia.")
    if df["fechamento"].isna().any():
        raise ValueError("ibovespa há fechamento vazio; não grava dado incompleto.")
    linhas = [
        (
            data,
            float(f),
            None if pd.isna(v) else int(v),  # volume vazio -> NULL no banco
            int(bool(p)),
            int(bool(d)),
        )
        for data, f, v, p, d in zip(
            _texto_data(df["data"]), df["fechamento"], df["volume"], df["parcial"], df["divergente"]
        )
    ]
    with conn:
        conn.executemany(
            f"INSERT OR REPLACE INTO {TABELA_IBOVESPA} "
            "(data, fechamento, volume, parcial, divergente) VALUES (?, ?, ?, ?, ?)",
            linhas,
        )
    return len(linhas)
 
 
def ler_tabela(conn, tabela: str) -> pd.DataFrame:
    """Lê uma tabela inteira, ordenada por data, com os tipos de volta ao normal."""
    _validar_tabela(tabela, TABELAS)
    df = pd.read_sql_query(f"SELECT * FROM {tabela} ORDER BY data", conn)
    df["data"] = pd.to_datetime(df["data"])
    if tabela == TABELA_IBOVESPA:
        df["volume"] = df["volume"].astype("Int64")
        df["parcial"] = df["parcial"].astype(bool)
        df["divergente"] = df["divergente"].astype(bool)
    return df
 
 
def ultima_data(conn, tabela: str):
    """Data mais recente gravada (ou None se vazia)."""
    _validar_tabela(tabela, TABELAS)
    (maxima,) = conn.execute(f"SELECT MAX(data) FROM {tabela}").fetchone()
    return None if maxima is None else pd.Timestamp(maxima)
 
 
def registrar_execucao(conn, momento: datetime | None = None) -> str:
    """Guarda quando o pipeline rodou pela última vez (o dashboard vai mostrar isso)."""
    momento = momento or datetime.now()
    texto = momento.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO metadados (chave, valor) VALUES ('ultima_execucao', ?)",
            (texto,),
        )
    return texto
 
 
def ler_ultima_execucao(conn):
    """Devolve o momento da última execução, ou None se nunca rodou."""
    linha = conn.execute("SELECT valor FROM metadados WHERE chave = 'ultima_execucao'").fetchone()
    return None if linha is None else datetime.strptime(linha[0], "%Y-%m-%d %H:%M:%S")