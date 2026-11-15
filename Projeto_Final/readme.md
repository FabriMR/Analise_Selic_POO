# Sistema de Análise de Dados e Dashboard Interativo: Taxa Selic Acumulada no Mês (Série SGS 4390 - BCB)

**Curso:** Ciência de Dados e Inteligência Artificial (CDIA)  
**Disciplina:** Programação Orientada a Objetos  
**Tema:** Economia — Análise da Política Monetária Brasileira, Capitalização Composta e Ciclos da Taxa Selic Efetiva Mensal (1995–2026)

## 1. Justificativa da Escolha do Tema e Definição do Problema (Etapa 1)

A **Taxa Selic** (Sistema Especial de Liquidação e de Custódia) é o instrumento primário de política monetária do [Banco Central do Brasil (BCB)](https://www.bcb.gov.br/controleinflacao/taxaselic). Enquanto a "Selic Meta" reflete o alvo anual definido pelo Comitê de Política Monetária (Copom), a **Taxa Selic acumulada no mês** ([Série SGS 4390 do Portal de Dados Abertos do BCB](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes)) expressa o rendimento efetivo mensal das operações compromissadas de um dia útil lastreadas em títulos públicos federais.

Compreender o comportamento histórico dessa série é indispensável para apoiar a tomada de decisão financeira de famílias, empresas e gestores públicos, pois ela determina diretamente o custo de oportunidade do capital, a remuneração de títulos pós-fixados (como o Tesouro Selic e CDBs atrelados ao CDI) e o índice oficial de atualização monetária e juros em obrigações legais.

### Problema Investigado e Objetivos da Análise
O problema central investigado consiste em mensurar como os diferentes regimes monetários (expansionistas, moderados e contracionistas) afetam a rentabilidade acumulada e a volatilidade mensal da economia brasileira desde a consolidação do Plano Real (1995–2026).

### Perguntas de Pesquisa Respondidas pelo Sistema
1. **Como os ciclos da Taxa Selic acumulada no mês impactam a decisão entre tomada de crédito e alocação em Renda Fixa pós-fixada?**
2. **Quais foram os períodos históricos de maior e menor aperto monetário no Brasil pós-Plano Real, e qual foi a amplitude entre o piso e o teto da série?**
3. **Qual é a divergência real gerada pelo efeito dos juros compostos anuais em comparação à simples soma linear das taxas mensais ao longo de diferentes décadas?**

## 2. Identificação e Descrição da Fonte Pública de Dados (Etapa 2)

Os dados utilizados neste projeto provêm oficialmente do **Sistema Gerenciador de Séries Temporais (SGS)**, mantido pelo Departamento de Operações do Mercado Aberto (Demab) do Banco Central do Brasil:

* **Conjunto de Dados Oficial:** [Taxa de juros - Selic acumulada no mês (Série 4390) — Portal de Dados Abertos do BCB](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes)
* **Endpoint Oficial JSON (API SGS):** [Recurso JSON Série SGS 4390](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes/resource/449efbb5-366b-4907-820f-8143a63733e1) (`https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json`)
* **Endpoint Oficial CSV (API SGS):** [Recurso CSV Série SGS 4390](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes/resource/db8e4db8-4f47-438f-a19c-756ca140b6ee) (`https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=csv`)
* **Referência Histórica Complementar:** [Tabela Histórica Selic Mensal e Fator Acumulado (SGS 4390) — eCalculo](https://www.ecalculo.net.br/tabelas/selic) e [Indicadores Selic e CDI (SGS 432 e 4390) — Organizesee](https://www.organizesee.com.br/indicadores/selic)
* **Periodicidade e Unidade:** Mensal, expressa em percentual ao mês (`% a.m.`), sob licença aberta *Open Data Commons Open Database License (ODbL)*.

## 3. Descrição das Variáveis Utilizadas (Etapa 2)

A base bruta retornada pela API do Banco Central contém duas colunas nativas (`data` e `valor`). Durante o pipeline de engenharia de atributos na classe `AnalisadorSelic`, o DataFrame é enriquecido com variáveis analíticas e financeiras:

| Variável / Coluna | Tipo de Dado (Pandas) | Origem | Descrição Técnica |
| :--- | :--- | :--- | :--- |
| `data` | `datetime64[ns]` | Nativa (SGS 4390) | Data de referência do primeiro dia de cada mês de competência (`dd/mm/aaaa`). |
| `valor` / `taxa_mensal` | `float64` | Nativa (SGS 4390) | Taxa Selic efetiva acumulada no mês, expressa em `% a.m.`. |
| `ano` | `int64` | Derivada | Ano civil extraído da data de competência (1995 a 2026). |
| `mes_num` / `mes_nome` | `int64` / `string` | Derivada | Número (1 a 12) e sigla em português (`Jan` a `Dez`) do mês de competência. |
| `trimestre` / `decada` | `string` | Derivada | Agrupadores temporais de trimestre (`T1` a `T4`) e década (`1990s` a `2020s`). |
| `fator_mensal` | `float64` | Derivada | Fator multiplicador unitário de capitalização mensal: $1 + (\text{taxa\_mensal} / 100)$. |
| `taxa_anualizada_equivalente` | `float64` | Derivada | Taxa anual equivalente por capitalização composta de 12 meses: $((1 + i)^ {12} - 1) \times 100$. |
| `selic_acumulada_12m` | `float64` | Derivada | Taxa acumulada móvel nos últimos 12 meses fechados via produtório móvel (`rolling(12).apply(np.prod)`). |
| `media_movel_6m` | `float64` | Derivada | Média móvel aritmética de 6 meses para suavização de ruídos de curto prazo. |
| `regime_monetario` | `string` | Derivada | Classificação do ciclo monetário em 4 faixas: Expansionista (`< 0,50%`), Moderado (`0,50% a 0,84%`), Contracionista (`0,85% a 1,14%`) e Fortemente Contracionista (`>= 1,15%`). |

## 4. Procedimentos de Tratamento e Análise dos Dados com Pandas (Etapas 2 e 4)

O processamento na classe `AnalisadorSelic` cumpre rigorosamente todos os requisitos mínimos exigidos para manipulação com Pandas:

* **Padronização e Conversão de Tipos:** Conversão de `data` para `datetime64[ns]` com `pd.to_datetime(..., format="%d/%m/%Y", errors="coerce")` e substituição de vírgulas decimais por ponto para conversão segura de `valor` em `float64` via `pd.to_numeric(..., errors="coerce")`.
* **Tratamento de Dados Ausentes e Inconsistências:** Contabilização de registros nulos (`isna().sum()`) e descarte seguro com `dropna(subset=["data", "taxa_mensal"])`, além de filtro contra taxas negativas inconsistentes (`df["taxa_mensal"] >= 0`).
* **Remoção de Duplicidades:** Auditoria de chaves duplicadas (`df.duplicated(subset=["data"]).sum()`) e desduplicação mantendo a atualização mais recente (`drop_duplicates(subset=["data"], keep="last")`).
* **Ordenação Cronológica:** Ordenação ascendente estrita por data (`sort_values(by="data", ascending=True).reset_index(drop=True)`), essencial para o cálculo correto de janelas móveis (`rolling`).
* **Seleção, Filtragem e Agrupamentos (`groupby`):** Métodos dedicados para filtragem combinada por intervalo de anos, meses e regimes monetários (`filtrar_dados`), bem como agregações por ano (`agrupar_por_ano` com produtório de fatores compostos), por regime (`agrupar_por_regime`) e sazonalidade mensal (`agrupar_sazonalidade_mensal`).
* **Cálculo de Estatísticas Descritivas:** Extração automatizada de média, mediana, desvio-padrão amostral, variância, coeficiente de variação percentual, mínimo, máximo, amplitude e quartis (Q1 = 25% e Q3 = 75%).

## 5. Arquitetura Orientada a Objetos e Princípios SOLID (Etapa 3)

O sistema foi projetado com **7 classes** (superando o requisito mínimo de 4 classes), aplicando construtores (`__init__`), encapsulamento com atributos privados/protegidos (`__` e `_`) e `@property`, abstração (`ABC`), herança, polimorfismo e princípios **SOLID**:

| Classe | Tipo / Hierarquia | Princípio SOLID Principal | Responsabilidade no Sistema |
| :--- | :--- | :--- | :--- |
| `FonteDados` | Classe Abstrata (`ABC`) | **OCP** & **DIP** | Define o contrato abstrato `obter_dados()` e encapsula metadados de origem (`nome_fonte`, `url_referencia`, `modo_extracao`). |
| `FonteDadosBCB` | Herda de `FonteDados` | **LSP** & **SRP** | Implementa polimorficamente `obter_dados()` consultando a API JSON do SGS/BCB (Série 4390), com fallback automático para CSV local (`selic_sgs_4390.csv`) e base histórica oficial. |
| `Indicador` | Classe Abstrata (`ABC`) | **OCP** & **LSP** | Superclasse que encapsula `nome`, `valor`, `unidade` e `descricao`, exigindo implementação polimórfica de `formatar_valor()` e `classificar_cenario()`. |
| `IndicadorEstatistico` | Herda de `Indicador` | **LSP** | Especializa a formatação e o diagnóstico de métricas estatísticas mensais (`% a.m.` e pontos percentuais). |
| `IndicadorFinanceiro` | Herda de `Indicador` | **LSP** | Especializa polimorficamente a formatação de taxas compostas anualizadas (`% a.a.`) e montantes monetários (`R$`). |
| `AnalisadorSelic` | Classe Concreta de Domínio | **SRP** | Executa todo o pipeline de limpeza, tipagem, enriquecimento, filtragem, agrupamentos e geração de objetos `Indicador` com Pandas. |
| `VisualizadorSelic` | Classe Concreta de Visão | **SRP** | Constrói os 5 gráficos interativos utilizando a biblioteca Plotly (`go.Figure` e `plotly.express`). |
| `DashboardSelic` | Classe Orquestradora | **DIP** | Recebe `FonteDados`, `AnalisadorSelic` e `VisualizadorSelic` via injeção de dependência no construtor e renderiza a aplicação web em Streamlit. |

## 6. Descrição dos Indicadores Desenvolvidos (Etapa 4)

O método `AnalisadorSelic.gerar_indicadores()` instancia **7 indicadores polimórficos** (superando o mínimo exigido de 5 indicadores), cujos valores no recorte recente de **2020 a outubro de 2026** (82 meses) são:

1. **Selic Mensal Vigente (10/2026):** `1,07% a.m.` — Taxa efetiva registrada no último mês fechado da série ([eCalculo - SGS 4390](https://www.ecalculo.net.br/tabelas/selic)).
2. **Selic Acumulada nos Últimos 12 Meses:** `14,23% a.a.` — Produtório composto dos fatores mensais dos últimos 12 meses fechados: $(\prod_{t=1}^{12} (1 + i_t) - 1) \times 100$.
3. **Taxa Média Mensal do Período:** `0,81% a.m.` — Média aritmética simples das taxas mensais no período filtrado (ou `1,30% a.m.` considerando toda a série 1995–2026).
4. **Pico Mensal no Período:** `1,28% a.m.` (registrado em julho e outubro de 2025 no recorte 2020–2026, e `4,26% a.m.` em março/abril de 1995 na série completa pós-Real).
5. **Mínima Mensal Histórica:** `0,13% a.m.` (registrada em fevereiro de 2021, durante o piso histórico da meta Selic de 2,00% a.a. na pandemia de COVID-19).
6. **Volatilidade Mensal (Desvio-Padrão):** `0,36 p.p.` no recorte 2020–2026 (`0,75 p.p.` na série 1995–2026), medindo o risco de variação da taxa mensal.
7. **Capital Corrigido no Período (Simulador):** `R$ 19.300,28` para um aporte inicial de `R$ 10.000,00` entre jan/2020 e out/2026 (rentabilidade acumulada de `+93,00%` no período).

## 7. Apresentação e Interpretação dos Gráficos Interativos (Etapa 5)

A classe `VisualizadorSelic` gera **5 visualizações interativas em Plotly** (cumprindo e superando os 4 tipos exigidos na Etapa 5):

1. **Gráfico de Linhas (`criar_grafico_linhas_historico`):** Plota a evolução cronológica da Taxa Selic acumulada no mês (`% a.m.`) sobreposta pela Média Móvel de 6 meses. Permite visualizar claramente a queda abrupta das taxas pós-1999, o vale histórico de 2020–2021 e a escalada contracionista de 2022–2026.
2. **Gráfico de Barras (`criar_grafico_barras_anual`):** Apresenta a Taxa Selic Efetiva Acumulada em cada ano (`% a.a.`) obtida por capitalização composta. Destaca contrastes históricos marcantes, como os `2,75% a.a.` acumulados em 2020 frente aos `14,33% a.a.` acumulados em 2025.
3. **Gráfico de Setores / Rosca (`criar_grafico_setores_regimes`):** Exibe a proporção de meses em que o Brasil operou em cada Regime de Política Monetária, demonstrando a predominância histórica de regimes contracionistas (`>= 0,85% a.m.`) na economia brasileira.
4. **Gráfico Adicional 1 — Boxplot por Década (`criar_grafico_boxplot_decadas`):** Compara a mediana, o intervalo interquartil (IQR) e os *outliers* das taxas mensais nas décadas de 1990, 2000, 2010 e 2020, comprovando a redução estrutural da dispersão após a adoção do regime de metas de inflação.
5. **Gráfico Adicional 2 — Histograma com Violino Marginal (`criar_grafico_histograma_frequencia`):** Mostra a distribuição de frequência das taxas mensais, evidenciando a concentração bimodal em torno de `0,50%–0,60% a.m.` (ciclos de estímulo) e `0,90%–1,15% a.m.` (ciclos de controle inflacionário).

## 8. Funcionamento do Dashboard em Streamlit e Como Executar (Etapa 6)

O painel web construído na classe `DashboardSelic` organiza a experiência do usuário em:
* **Cabeçalho Institucional:** Identificação do projeto, link direto para a fonte oficial no BCB e status do modo de extração (API Online ou CSV Local).
* **Barra Lateral de Filtros Interativos (`st.sidebar`):** Slider de intervalo de anos, seletor múltiplo de Regimes Monetários e campo numérico para simulação de capital inicial em Reais (`R$`).
* **Painel de KPIs (`st.metric`):** Exibição em cartões dos 7 indicadores polimórficos com *tooltips* de diagnóstico automático.
* **Abas de Visualizações Dinâmicas (`st.tabs`):** Navegação fluida entre os 5 gráficos interativos do Plotly.
* **Tabela de Dados e Estatísticas Descritivas:** Exibição lado a lado do DataFrame filtrado e da tabela de métricas estatísticas do Pandas.
* **Seção de Análise Interpretativa:** Síntese executiva respondendo às perguntas de negócio diretamente no dashboard.

### Passo a Passo para Execução e Versionamento Git/GitHub

No terminal (Prompt de Comando, PowerShell ou Git Bash), dentro da pasta onde salvou os arquivos `app.py`, `selic_sgs_4390.csv`, `requirements.txt` e `README.md`:

```bash
# 1. Instalar as bibliotecas necessárias
python -m pip install -r requirements.txt

# 2. (Opcional) Rodar a suíte de validação automatizada para verificar as classes e cálculos
python app.py --test

# 3. Iniciar o Dashboard Interativo no navegador
python -m streamlit run app.py
```

Para publicar no **GitHub** e ativar a documentação no **GitHub Pages (`gh-pages`)**:

```bash
git init
git add app.py selic_sgs_4390.csv requirements.txt README.md
git commit -m "feat: implementa sistema POO e dashboard Streamlit da Taxa Selic (SGS 4390)"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```
*(No GitHub, acesse **Settings > Pages**, selecione **Deploy from a branch** e escolha a branch `main` / `/ (root)` para que este `README.md` seja publicado automaticamente como página web do projeto).*

## 9. Principais Conclusões e Limitações da Análise (Etapa 8)

* **Conclusões:** A análise comprova que a economia brasileira operou majoritariamente sob taxas mensais superiores a `0,85% a.m.` nas últimas três décadas, tornando os títulos pós-fixados indexados à Selic instrumentos de alta resiliência patrimonial. Além disso, a capitalização composta amplia significativamente o retorno acumulado em horizontes plurianuais quando comparada a aproximações lineares.
* **Limitações:** A Série SGS 4390 expressa a taxa **nominal** acumulada no mês. Portanto, a análise isolada desta série não desconta a inflação oficial (IPCA - Série SGS 433) para apuração do juro real *ex-post*, nem incorpora alíquotas regressivas de Imposto de Renda incidentes sobre aplicações financeiras privadas.

## 10. Referências Utilizadas (Etapa 8)

* **Banco Central do Brasil (BCB):** [Conjunto de Dados — Taxa de juros - Selic acumulada no mês (Código SGS 4390)](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes).
* **Banco Central do Brasil (API SGS JSON):** [Interface JSON do serviço BCData/SGS - Série 4390](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes/resource/449efbb5-366b-4907-820f-8143a63733e1).
* **Banco Central do Brasil (API SGS CSV):** [Interface CSV do serviço BCData/SGS - Série 4390](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes/resource/db8e4db8-4f47-438f-a19c-756ca140b6ee).
* **Banco Central do Brasil — Política Monetária:** [Descrição e Conceito da Taxa Selic](https://www.bcb.gov.br/controleinflacao/taxaselic) e [Histórico das Taxas de Juros Básicas (Copom)](https://www.bcb.gov.br/controleinflacao/historicotaxasjuros).
* **eCalculo:** [Tabela de Referência da Taxa Selic Mensal e Fator Acumulado (Série SGS 4390)](https://www.ecalculo.net.br/tabelas/selic).
* **Organizesee:** [Indicadores Econômicos — Série Histórica da Taxa Selic e CDI (BCB/SGS)](https://www.organizesee.com.br/indicadores/selic).
