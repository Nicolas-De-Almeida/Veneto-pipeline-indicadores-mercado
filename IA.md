# IA.md — Como a IA foi usada neste projeto

> Relatório gerado pelo Claude (Anthropic) ao final da conversa em que o projeto foi construído, a partir do prompt do case. Não foi editado depois de gerado.

**Nota sobre a fonte deste relatório.** A conversa foi longa e foi compactada uma vez. Da parte mais recente (de 03/11 a 04/11/2026) eu tenho as mensagens na íntegra. Da parte inicial (planejamento, decisões de transformação, primeiras versões do pipeline) eu tenho apenas um resumo e as anotações das decisões que Nicolas declarou. Os detalhes da fase inicial podem, portanto, estar menos precisos do que os da fase final.

## Em uma frase

**Uma parte do código foi escrita por mim (Claude).** Nicolas definiu os requisitos e as decisões de comportamento, leu, pesquisou, checou e aplicou os arquivos, rodou os testes e o dashboard no próprio Mac, reportou problemas com saídas de terminal e capturas de tela, e fez os commits.

## 1. Como fui direcionada

- **Contexto e restrições dados desde o início.** O case (prazo 05/11/2026), as quatro séries (CDI, IPCA, dólar PTAX, Ibovespa), os 5 anos de histórico, SQLite com uma tabela por série, Streamlit + Plotly, repositório público no GitHub com commits incrementais, README e este IA.md.
- **Restrições de método explícitas e repetidas:** testes para tudo, código organizado e comentado, qualidade profissional, e a instrução "não suponha nada, eu preciso de certezas". Também pediu explicações simples e lentas (nunca tinha usado Streamlit, Plotly nem SQLite) e sempre com o local de cada arquivo. Em 03/11 pediu que o código viesse em trechos (quando o arquivo já existe) ou inteiro (quando é novo), em vez de .zip, para conferir mais fácil.
- **Planejamento antes do código, em parte.** Nicolas quis desenhar o dashboard no Figma (wireframe e mockup colorido) antes de fechar as decisões da transformação. Também pediu o custo, no código, de decidir manter 11 meses anteriores para os indicadores de 12 meses, antes de decidir. 
- **Instruções curtas e informais, com evidência anexada.** As mensagens costumam ser curtas, mas vêm com saída de terminal ou captura de tela. Os pedidos de ajuste visual vieram numerados (primeiro, segundo, terceiro, quarto), com o problema descrito.
- **Verificação própria.** Nicolas disse que revisa cada arquivo antes de commitar e testou tudo no Mac (de 64 para 121 e depois 136 testes passando; clone limpo do GitHub; execução do pipeline e do dashboard). Os erros de transcrição que apareceram em arquivos aplicados por ele (`connectar` no lugar de `conectar`; uma linha `datas = ...` faltando em `transform.py`) indicam que o código passava por cópia manual, e que ele rodava os testes para achá-los.
- **Outros artefatos.** Também produzi, em momento anterior, um guia de estudo em documento separado.

## 2. Pedidos principais

1. **Construir o pipeline ETL.** Baixar CDI (SGS 12), IPCA (SGS 433), dólar PTAX venda (SGS 1) e Ibovespa (yfinance, `^BVSP`), limpar e gravar em SQLite, uma tabela por série, com testes e explicação passo a passo.
2. **Definir as regras de tratamento de dados.** Dia em que o Yahoo difere da B3 aparece como N/A nos gráficos; preenchimento de dias sem dado só na montagem do gráfico (o banco guarda os dados originais); mostrar o valor parcial do Ibovespa; volume ausente como NA, com o rótulo "Volume (Yahoo Finance)"; manter 11 meses anteriores para os indicadores de 12 meses.
3. **Construir o dashboard em Streamlit + Plotly** na identidade visual da Vêneto (azul-marinho e dourado, títulos com serifa), com a logo própria de Nicolas, com base no wireframe e no mockup feitos por ele no Figma.
4. **Corrigir o layout e a exibição** depois de testar: cabeçalho e rodapé de ponta a ponta, espaço em branco no topo, texto sobreposto no expansor, "None" na tabela, menu da tabela, balão do gráfico mostrando só o mês. Também investigar por que os cartões não mostravam o dado de 03/11.
5. **Fechar a entrega:** atualização incremental (o bônus), `requirements.txt` com versões fixas, teste do zero em um clone limpo, README (com instruções para Windows marcadas como não testadas e capturas do dashboard) e este IA.md.

## 3. Correções e questionamentos

- **Rejeitou a entrega em .zip.** Pediu trechos com o local de colagem ou arquivo inteiro com o caminho. Motivo declarado: ficar mais fácil conferir. Passei a entregar assim.
- **Rejeitou esconder o menu da tabela.** Eu tinha escondido a barra de ferramentas da tabela de dados; ele pediu de volta, e eu a reativei e acrescentei um espaçamento.
- **Apontou bugs visuais que eu introduzi ou não previ,** por captura de tela: o texto do expansor sobreposto a nomes de ícones (causado por uma regra de fonte minha, ampla demais); o espaço em branco no topo da página, que persistiu depois da primeira correção; valores "None" na tabela; cabeçalho e rodapé sem ocupar a largura total.
- **Questionou por que os dados paravam em 30/10.** A suspeita de bug foi investigada com consultas ao banco e às APIs. O banco e o pipeline estavam corretos (dólar e Ibovespa de 03/11 estavam gravados; o CDI só publica com um dia útil de atraso e 02/11 foi feriado). Os cartões mostraram 03/11 depois de reiniciar o dashboard.
- **Encontrou o balão do gráfico mostrando "nov de 26"** em vez de "03/11/2026" no último ponto. Foi erro meu na configuração dos rótulos do eixo; corrigi e ele confirmou.
- **Conferiu por conta própria os fechamentos do Ibovespa de 26 a 30/10 contra o site da B3** (disse que os números batem) e as decisões sobre dias divergentes.
- **Fase inicial (pelo resumo):** ao pedir "não suponha nada", fez com que eu pedisse o código dos extratores em vez de supor suas assinaturas. Houve também um caso em que a primeira versão do dashboard tratava o dia divergente com um padrão diferente da decisão dele (N/A nos gráficos); isso foi corrigido para respeitar a decisão.

## 4. Divisão das decisões

**Decididas por Nicolas:**
- Streamlit + Plotly; SQLite com uma tabela por série.
- Prazo, escopo, repositório público e commits incrementais; a intenção de enviar antes do último dia.
- Dia divergente da B3 como N/A nos gráficos; forward fill só na montagem do gráfico; mostrar o Ibovespa parcial; volume ausente como NA; manter 11 meses anteriores nos indicadores de 12 meses; o rótulo "Volume (Yahoo Finance)".
- A identidade visual (wireframe e mockup no Figma, logo própria) e as críticas ao mockup (linhas finas, cores apagadas).
- Pesquisar a B3 para confirmar os dias divergentes e de volume zero; os valores de referência foram conferidos manualmente por ele.
- Trazer de volta o menu da tabela; manter o gráfico do câmbio com a regra atual de datas; o formato de entrega do código (trechos).
- O texto final do README (ele disse ter feito mudanças na minha versão) e quais commits fazer e com qual mensagem.
- Pipeline "tudo ou nada" (baixa e limpa tudo antes de gravar, para não deixar o banco pela metade)

**Sugeridas por mim e aceitas, pelo que consta na conversa, com alterações:**
- A estrutura de pastas (`src/`, `scripts/`, `dashboard/`, `tests/`) e a divisão em extrair, transformar e carregar.
- `INSERT OR REPLACE` para rodar várias vezes sem duplicar.
- Baixar 6 anos de CDI e IPCA para os acumulados de 12 meses valerem desde o início da janela de 5 anos.
- As fórmulas financeiras (CDI anualizado com 252 dias úteis, IPCA 12 meses por produtório, ganho real sobre os mesmos 12 meses) e a regra de que o IPCA acumulado do gráfico usa pontos no fim de cada mês.
- As regras do cabeçalho e dos cartões ("Dados até" como a data mais antiga entre as últimas das séries, "Ref." em cada cartão, "N/A" para dado ausente e "—" para fonte sem linha no dia).
- A regra do dia parcial (data igual à de hoje).
- A atualização incremental com margem de 30 dias e o argumento `--completo`.
- A organização da bateria de testes e do README.
- A correção dos rótulos do eixo para o balão mostrar a data completa.

## 5. Pontos de atenção

- **O dashboard nunca foi executado por mim com o Streamlit e o Plotly reais.** No meu ambiente a instalação desses pacotes foi bloqueada, então testei com versões falsas deles. Todo o resultado visual foi validado apenas por Nicolas, no Mac. A correção do balão do gráfico se baseia no meu conhecimento do comportamento do Plotly, não em um teste meu; ele confirmou o resultado.
- **Os testes não acessam a internet.** Os extratores e o incremental foram testados com downloads falsos. O comportamento real foi visto apenas nas execuções de Nicolas.
- **Descrição imprecisa minha sobre o fim dos gráficos.** Eu disse que os gráficos terminam na última data em que todas as séries têm dado. Nos prints finais, o dólar e o Ibovespa aparecem até 03/11 enquanto o cabeçalho diz "Dados até 30/10": cada série vai até a sua última data real, e só o cabeçalho usa a data mais antiga.
- **Regra do dia parcial é simples demais.** Uma linha com a data de hoje é sempre marcada como parcial, sem saber se o pregão já fechou. Em 03/11, às 19:39 (depois do fechamento), o cartão mostrou "parcial 19:39"; o horário é o da execução do pipeline, não o da cotação. No dia seguinte o valor era o mesmo (165.529). O fechamento de 03/11 não foi comparado com a B3.
- **Validação do Ibovespa por amostragem.** Foram conferidas algumas datas (inclusive dias de volume zero) e os dias de 26 a 30/10; não todos os dias. Há um dia divergente conhecido (10/11/2023), cujo valor da B3 foi digitado à mão em `config.py`. Outros dias divergentes podem existir. O Yahoo também arredonda alguns fechamentos.
- **Conferência das fórmulas.** Em fase anterior os resultados foram comparados com séries de referência do SGS (4389 para o CDI anualizado e 13522 para o IPCA em 12 meses). Na ocasião li errado o comentário de uma delas; o erro foi corrigido. Vale refazer a conferência dos números finais mostrados nos cartões (por exemplo, CDI de 13,65% a.a. e IPCA de 4,58% em 12 meses) contra uma fonte independente.
- **`yfinance` não é uma API oficial.** Pode mudar ou falhar, e emite avisos de depreciação com o pandas 3.
- **Windows e Linux não foram testados.** O README traz instruções para Windows marcadas como não testadas.
- **Possíveis erros de transcrição.** Como o código era checado e copiado para os arquivos, a rodada de testes (136 passando no clone limpo) é a principal garantia. Convém rodar `python3 -m pytest -q` e o teste do zero de novo se algo for alterado.