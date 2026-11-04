"""Pipeline ETL: baixa (Extract), limpa (Transform) e grava no SQLite (Load).

Como rodar (na raiz do projeto):
    python3 -m src.pipeline              # incremental: baixa só o que falta
    python3 -m src.pipeline --completo   # baixa todo o histórico de novo"""
import sys
from datetime import date, timedelta

from src import config, load
from src.extract_ibovespa import baixar_ibovespa
from src.extract_sgs import baixar_serie_sgs, calcular_periodo
from src.transform import converter_serie_sgs, tratar_ibovespa


def _anos_da_serie(nome: str) -> int:
    """CDI e IPCA pedem 1 ano a mais (para o acumulado 12m valer desde o início)."""
    extra = config.ANOS_EXTRAS_12M if nome in config.SERIES_COM_ANO_EXTRA else 0
    return config.ANOS_HISTORICO + extra

def _inicio_da_busca(conn, tabela: str, inicio_completo: date, completo: bool) -> date:
    """Data em que a busca desta tabela começa.
    - Modo completo ou tabela vazia (primeira execução): o histórico inteiro.
    - Senão: `MARGEM_INCREMENTAL_DIAS` antes da última data gravada, mas nunca
      antes do início do histórico. Baixar alguns dias repetidos é seguro porque
      a gravação é INSERT OR REPLACE (atualiza, não duplica)."""
    if completo:
        return inicio_completo
    ultima = load.ultima_data(conn, tabela)
    if ultima is None:
        return inicio_completo
    return max(inicio_completo, ultima.date() - timedelta(days=config.MARGEM_INCREMENTAL_DIAS))

def executar(conn=None, hoje: date | None = None, completo: bool = False) -> dict:
    """Roda o pipeline e devolve um resumo por tabela.

    Primeiro BAIXA e LIMPA tudo; só depois grava. Assim, se qualquer fonte
    falhar, nada é gravado e o banco não fica com dados pela metade.
    `conn` é opcional (os testes passam um banco em memória); se não vier,
    abre o banco padrão e fecha no final."""
    hoje = hoje or date.today()
    abrimos_aqui = conn is None
    if abrimos_aqui:
        conn = load.conectar()
    try:
        load.criar_tabelas(conn)

        # 1) Extrair + transformar (sem tocar no banco, ou grava tudo, ou nada)
        series = {}
        for nome, codigo in config.SERIES_SGS.items():
            inicio, fim = calcular_periodo(hoje, _anos_da_serie(nome))
            inicio = _inicio_da_busca(conn, nome, inicio, completo)
            bruto = baixar_serie_sgs(codigo, inicio, fim)
            series[nome] = converter_serie_sgs(bruto, nome)

        inicio, fim = calcular_periodo(hoje, config.ANOS_HISTORICO)
        inicio = _inicio_da_busca(conn, load.TABELA_IBOVESPA, inicio, completo)
        ibovespa = tratar_ibovespa(baixar_ibovespa(inicio, fim), hoje=hoje)

        # 2) Carregar
        resumo = {}
        for nome, df in series.items():
            resumo[nome] = {"linhas": load.salvar_serie_sgs(conn, nome, df, nome)}
        resumo[load.TABELA_IBOVESPA] = {"linhas": load.salvar_ibovespa(conn, ibovespa)}
        load.registrar_execucao(conn)

        for tabela, info in resumo.items():
            info["ultima_data"] = load.ultima_data(conn, tabela).date()
            info["total"] = load.contar_linhas(conn, tabela)
        return resumo
    finally:
        if abrimos_aqui:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada: imprime o resumo. Devolve 0 se deu certo, 1 se falhou."""
    argumentos = sys.argv[1:] if argv is None else argv
    desconhecidos = [a for a in argumentos if a != "--completo"]
    if desconhecidos:
        print(f"Argumento desconhecido: {desconhecidos[0]}. Use apenas --completo (opcional).")
        return 1
    completo = "--completo" in argumentos

    try:
        resumo = executar(completo=completo)
    except Exception as erro:
        print(f"ERRO: o pipeline falhou e nada foi gravado. Motivo: {erro}")
        if erro.__cause__ is not None:
            print(f"Causa: {erro.__cause__}")
        return 1

    modo = "completo" if completo else "incremental"
    print(f"Pipeline concluído ({modo}). Banco: {config.CAMINHO_BANCO}")
    for tabela, info in resumo.items():
        print(
            f"  {tabela:<11} {info['linhas']:>5} linhas baixadas | "
            f"{info['total']:>5} no banco | último dado: {info['ultima_data']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())