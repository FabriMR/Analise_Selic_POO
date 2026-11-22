# Selic Analytics & Dashboard (BCB SGS 4390)

**Stack:** Python 3.10+ | Pandas | NumPy | Plotly | Streamlit | Arquitetura Orientada a Objetos (SOLID)

Aplicação analítica e dashboard interativo para extração, tratamento e visualização da série histórica oficial da **Taxa Selic efetiva acumulada no mês** ([Série SGS 4390 — Banco Central do Brasil](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes)), cobrindo o período de **janeiro de 1995 a outubro de 2026** (382 competências mensais).

O projeto combina engenharia de dados em **Pandas**, modelagem **Orientada a Objetos** orientada pelos princípios **SOLID**, visualizações interativas em **Plotly** e interface web em **Streamlit**, permitindo analisar ciclos monetários, capitalização composta e simulações de rentabilidade em renda fixa pós-fixada.

## Principais Funcionalidades

- **Extração Resiliente em 3 Camadas:** Consulta automatizada à [API JSON do SGS/BCB](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes/resource/449efbb5-366b-4907-820f-8143a63733e1) em janelas de 10 anos, com fallback transparente para o arquivo CSV local (`selic_sgs_4390.csv`) e base histórica integrada em memória.
- **Pipeline ETL e Engenharia Financeira (Pandas):** Conversão segura de tipos, tratamento de valores ausentes e inconsistências, desduplicação cronológica, cálculo de capitalização composta anual e móvel (12 meses), média móvel de 6 meses e classificação automática em 4 regimes de política monetária.
- **Indicadores Polimórficos (KPIs):** Geração de 7 métricas estatísticas e financeiras, incluindo Selic vigente, acumulado em 12 meses, extremos históricos, volatilidade (desvio-padrão) e simulador de capital corrigido em Reais (`R$`).
- **5 Visualizações Interativas (Plotly):**
  1. Série temporal mensal (`% a.m.`) com média móvel de 6 meses.
  2. Taxa efetiva acumulada por ano (`% a.a.`) por capitalização composta.
  3. Gráfico de rosca com distribuição histórica dos regimes monetários.
  4. Boxplot comparativo de dispersão e *outliers* por década.
  5. Histograma de frequências com violino marginal.
- **Validação Automatizada:** Suíte de testes integrada (`--test`) que verifica herança, integridade do pipeline, ordenação temporal, agrupamentos, indicadores e geração dos gráficos.

## Arquitetura do Sistema (POO & SOLID)

O código em `app.py` foi estruturado com separação estrita de responsabilidades e baixo acoplamento:

| Componente | Tipo | Princípio SOLID | Responsabilidade |
| :--- | :--- | :--- | :--- |
| `FonteDados` | Classe Abstrata (`ABC`) | **OCP** e **DIP** | Define o contrato `obter_dados()` e encapsula metadados da fonte. |
| `FonteDadosBCB` | Herda de `FonteDados` | **LSP** e **SRP** | Implementa a ingestão em 3 camadas para a Série SGS 4390. |
| `Indicador` | Classe Abstrata (`ABC`) | **OCP** e **LSP** | Interface polimórfica com `formatar_valor()` e `classificar_cenario()`. |
| `IndicadorEstatistico` | Herda de `Indicador` | **LSP** | Formatação e diagnóstico para métricas em `% a.m.` e `p.p.`. |
| `IndicadorFinanceiro` | Herda de `Indicador` | **LSP** | Formatação e diagnóstico para taxas compostas (`% a.a.`) e valores em `R$`. |
| `AnalisadorSelic` | Domínio / ETL | **SRP** | Higienização, enriquecimento, filtros, `groupby` e cálculo de estatísticas. |
| `VisualizadorSelic` | Camada de Visão | **SRP** | Construção dos 5 gráficos interativos em Plotly. |
| `DashboardSelic` | Orquestração UI | **DIP** | Recebe dependências via `__init__` e renderiza a aplicação Streamlit. |

## Estrutura do Repositório

```text
.
├── app.py                    # Aplicação principal (POO, ETL Pandas, Plotly e Streamlit)
├── selic_sgs_4390.csv        # Base histórica oficial no formato CSV do SGS/BCB
├── requirements.txt          # Dependências do projeto
├── iniciar_dashboard.bat     # Inicializador automático para Windows (detecta Python e abre o painel)
└── README.md                 # Documentação técnica do repositório
```

## Dicionário de Dados

| Variável | Tipo | Descrição |
| :--- | :--- | :--- |
| `data` | `datetime64[ns]` | Data de competência mensal (`dd/mm/aaaa`). |
| `taxa_mensal` | `float64` | Taxa Selic efetiva acumulada no mês (`% a.m.`). |
| `fator_mensal` | `float64` | Fator de capitalização mensal: `1 + (taxa_mensal / 100)`. |
| `taxa_anualizada_equivalente` | `float64` | Equivalência anual composta de 12 meses (`% a.a.`). |
| `selic_acumulada_12m` | `float64` | Retorno composto móvel nos últimos 12 meses (`% a.a.`). |
| `media_movel_6m` | `float64` | Média móvel aritmética de 6 meses (`% a.m.`). |
| `regime_monetario` | `string` | Classificação em Expansionista (`< 0,50%`), Moderado (`0,50%–0,84%`), Contracionista (`0,85%–1,14%`) ou Fortemente Contracionista (`>= 1,15%`). |

## Como Executar

### Opção 1: Inicialização Automática (Windows)

Dê dois cliques no arquivo `iniciar_dashboard.bat`. O script detecta automaticamente a instalação do Python, instala as dependências do `requirements.txt`, executa a suíte de validação e abre o dashboard no navegador.

### Opção 2: Via Terminal (Windows, Linux ou macOS)

```bash
# 1. Clonar o repositório
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd SEU_REPOSITORIO

# 2. Instalar as dependências
python -m pip install -r requirements.txt

# 3. Executar a suíte de testes automatizados (opcional)
python app.py --test

# 4. Iniciar o dashboard interativo
python -m streamlit run app.py
```

*(No Windows, caso o comando `python` não seja reconhecido no terminal, substitua `python` por `py` nos comandos acima.)*

## Limitações Conhecidas

A Série SGS 4390 expressa a taxa **nominal** bruta acumulada no mês. A análise isolada desta série não desconta a inflação oficial (IPCA) para apuração do juro real *ex-post*, nem incorpora alíquotas de Imposto de Renda aplicáveis a títulos privados ou públicos.

## Fonte de Dados e Referências

- **Banco Central do Brasil (Portal de Dados Abertos):** [Taxa de juros — Selic acumulada no mês (Série SGS 4390)](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes)
- **API SGS/BCB (JSON):** [Recurso JSON Série 4390](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes/resource/449efbb5-366b-4907-820f-8143a63733e1)
- **API SGS/BCB (CSV):** [Recurso CSV Série 4390](https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes/resource/db8e4db8-4f47-438f-a19c-756ca140b6ee)
- **Conceito Oficial:** [Taxa Selic — Banco Central do Brasil](https://www.bcb.gov.br/controleinflacao/taxaselic)
- **Referências Históricas:** [Tabela Selic Mensal (SGS 4390) — eCalculo](https://www.ecalculo.net.br/tabelas/selic) | [Indicadores Selic — Organizesee](https://www.organizesee.com.br/indicadores/selic)