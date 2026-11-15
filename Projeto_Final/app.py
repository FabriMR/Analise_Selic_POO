"""
================================================================================
PROJETO FINAL - PROGRAMAÇÃO ORIENTADA A OBJETOS (CDIA)
Sistema de Análise de Dados e Dashboard Interativo: Taxa Selic Acumulada no Mês
================================================================================
Fonte de Dados Pública (Economia - Banco Central do Brasil):
- Portal de Dados Abertos BCB (Série SGS 4390):
  https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes
- Endpoint JSON da API SGS/BCB:
  https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json
- Endpoint CSV da API SGS/BCB:
  https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=csv

Arquitetura Orientada a Objetos e Princípios SOLID aplicados:
1. FonteDados (ABC) -> FonteDadosBCB (Herança e Polimorfismo / OCP e DIP)
2. AnalisadorSelic (Responsabilidade Única de ETL e análise Pandas / SRP)
3. Indicador (ABC) -> IndicadorEstatistico e IndicadorFinanceiro (Herança e Polimorfismo / LSP e OCP)
4. VisualizadorSelic (Geração de gráficos interativos Plotly / SRP)
5. DashboardSelic (Orquestração da interface web Streamlit com injeção de dependência / DIP)

Como executar o Dashboard:
    streamlit run app.py

Como executar a suíte de validação e testes:
    python app.py --test
================================================================================
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Importações condicionais para permitir testes automatizados mesmo em ambientes sem UI
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_DISPONIVEL = True
except ImportError:
    px = None
    go = None
    PLOTLY_DISPONIVEL = False

try:
    import streamlit as st
    STREAMLIT_DISPONIVEL = True
except ImportError:
    st = None
    STREAMLIT_DISPONIVEL = False


# ==============================================================================
# DADOS HISTÓRICOS OFICIAIS DE CONTINGÊNCIA (SÉRIE SGS 4390 - BCB: 1995 A OUT/2026)
# Caso a API do Banco Central esteja temporariamente indisponível ou sem rede,
# o sistema mantém resiliência carregando a série oficial verificada do SGS 4390.
# ==============================================================================
HISTORICO_OFICIAL_SGS_4390: Dict[int, List[float]] = {
    1995: [3.37, 3.25, 4.26, 4.26, 4.25, 4.04, 4.02, 3.84, 3.32, 3.09, 2.88, 2.78],
    1996: [2.58, 2.35, 2.22, 2.07, 2.01, 1.98, 1.93, 1.97, 1.90, 1.86, 1.80, 1.80],
    1997: [1.73, 1.67, 1.64, 1.66, 1.58, 1.61, 1.60, 1.59, 1.59, 1.67, 3.04, 2.97],
    1998: [2.67, 2.13, 2.20, 1.71, 1.63, 1.60, 1.70, 1.48, 2.49, 2.94, 2.63, 2.40],
    1999: [2.18, 2.38, 3.33, 2.35, 2.02, 1.67, 1.66, 1.57, 1.49, 1.38, 1.39, 1.60],
    2000: [1.46, 1.45, 1.45, 1.30, 1.49, 1.39, 1.31, 1.41, 1.22, 1.29, 1.22, 1.20],
    2001: [1.27, 1.02, 1.26, 1.19, 1.34, 1.27, 1.50, 1.60, 1.32, 1.53, 1.39, 1.39],
    2002: [1.53, 1.25, 1.37, 1.48, 1.41, 1.33, 1.54, 1.44, 1.38, 1.65, 1.54, 1.74],
    2003: [1.97, 1.83, 1.78, 1.87, 1.97, 1.86, 2.08, 1.77, 1.68, 1.64, 1.34, 1.37],
    2004: [1.27, 1.08, 1.38, 1.18, 1.23, 1.23, 1.29, 1.29, 1.25, 1.21, 1.25, 1.48],
    2005: [1.38, 1.22, 1.53, 1.41, 1.50, 1.59, 1.51, 1.66, 1.50, 1.41, 1.38, 1.47],
    2006: [1.43, 1.15, 1.42, 1.08, 1.28, 1.18, 1.17, 1.26, 1.06, 1.09, 1.02, 0.99],
    2007: [1.08, 0.87, 1.05, 0.94, 1.03, 0.91, 0.97, 0.99, 0.80, 0.93, 0.84, 0.84],
    2008: [0.93, 0.80, 0.84, 0.90, 0.88, 0.96, 1.07, 1.02, 1.10, 1.18, 1.02, 1.12],
    2009: [1.05, 0.86, 0.97, 0.84, 0.77, 0.76, 0.79, 0.69, 0.69, 0.69, 0.66, 0.73],
    2010: [0.66, 0.59, 0.76, 0.67, 0.75, 0.79, 0.86, 0.89, 0.85, 0.81, 0.81, 0.93],
    2011: [0.86, 0.84, 0.92, 0.84, 0.99, 0.96, 0.97, 1.07, 0.94, 0.88, 0.86, 0.91],
    2012: [0.89, 0.75, 0.82, 0.71, 0.74, 0.64, 0.68, 0.69, 0.54, 0.61, 0.55, 0.55],
    2013: [0.60, 0.49, 0.55, 0.61, 0.60, 0.61, 0.72, 0.71, 0.71, 0.81, 0.72, 0.79],
    2014: [0.85, 0.79, 0.77, 0.82, 0.87, 0.82, 0.95, 0.87, 0.91, 0.95, 0.84, 0.96],
    2015: [0.94, 0.82, 1.04, 0.95, 0.99, 1.07, 1.18, 1.11, 1.11, 1.11, 1.06, 1.16],
    2016: [1.06, 1.00, 1.16, 1.06, 1.11, 1.16, 1.11, 1.22, 1.11, 1.05, 1.04, 1.12],
    2017: [1.09, 0.87, 1.05, 0.79, 0.93, 0.81, 0.80, 0.80, 0.64, 0.64, 0.57, 0.54],
    2018: [0.58, 0.47, 0.53, 0.52, 0.52, 0.52, 0.54, 0.57, 0.47, 0.54, 0.49, 0.49],
    2019: [0.54, 0.49, 0.47, 0.52, 0.54, 0.47, 0.57, 0.50, 0.46, 0.48, 0.38, 0.37],
    2020: [0.38, 0.29, 0.34, 0.28, 0.24, 0.21, 0.19, 0.16, 0.16, 0.16, 0.15, 0.16],
    2021: [0.15, 0.13, 0.20, 0.21, 0.27, 0.31, 0.36, 0.43, 0.44, 0.49, 0.59, 0.77],
    2022: [0.73, 0.76, 0.93, 0.83, 1.03, 1.02, 1.03, 1.17, 1.07, 1.02, 1.02, 1.12],
    2023: [1.12, 0.92, 1.17, 0.92, 1.12, 1.07, 1.07, 1.14, 0.97, 1.00, 0.92, 0.89],
    2024: [0.97, 0.80, 0.83, 0.89, 0.83, 0.79, 0.91, 0.87, 0.84, 0.93, 0.79, 0.93],
    2025: [1.01, 0.99, 0.96, 1.06, 1.14, 1.10, 1.28, 1.16, 1.22, 1.28, 1.05, 1.22],
    2026: [1.16, 1.00, 1.21, 1.09, 1.07, 1.12, 1.22, 1.09, 1.08, 1.07],
}


# ==============================================================================
# ETAPA 3 - MODELAGEM ORIENTADA A OBJETOS (CLASSES, HERANÇA, POLIMORFISMO, SOLID)
# ==============================================================================

class FonteDados(ABC):
    """
    Classe Abstrata (Interface) para gerenciamento de fontes de dados.
    Aplica os princípios OCP (Open/Closed Principle) e DIP (Dependency Inversion Principle).
    """

    def __init__(self, nome_fonte: str, url_referencia: str) -> None:
        self._nome_fonte = nome_fonte
        self._url_referencia = url_referencia
        self._ultima_extracao: Optional[datetime] = None
        self._modo_extracao: str = "Não inicializado"

    @property
    def nome_fonte(self) -> str:
        """Retorna o nome oficial da fonte de dados (Encapsulamento)."""
        return self._nome_fonte

    @property
    def url_referencia(self) -> str:
        """Retorna a URL de referência da documentação oficial (Encapsulamento)."""
        return self._url_referencia

    @property
    def modo_extracao(self) -> str:
        """Retorna o modo pelo qual os dados foram obtidos (API, CSV Local ou Contingência)."""
        return self._modo_extracao

    @abstractmethod
    def obter_dados(self) -> pd.DataFrame:
        """Método abstrato polimórfico que deve retornar um DataFrame Pandas bruto."""
        pass


class FonteDadosBCB(FonteDados):
    """
    Subclasse concreta que herda de FonteDados (Herança e Polimorfismo).
    Responsável por consultar a Série 4390 (Taxa de juros - Selic acumulada no mês)
    na API do Sistema Gerenciador de Séries Temporais (SGS) do Banco Central do Brasil,
    com suporte automático a arquivo CSV local (`selic_sgs_4390.csv`) e contingência.
    """

    def __init__(
        self,
        codigo_serie: int = 4390,
        caminho_csv_local: Optional[str] = "selic_sgs_4390.csv",
    ) -> None:
        super().__init__(
            nome_fonte=f"Banco Central do Brasil - SGS Série {codigo_serie} (Selic Acumulada no Mês)",
            url_referencia="https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes",
        )
        self.__codigo_serie = codigo_serie
        self.__url_api_json = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados?formato=json"
        )
        self.__url_api_csv = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados?formato=csv"
        )
        self.__caminho_csv_local = caminho_csv_local

    @property
    def codigo_serie(self) -> int:
        """Propriedade encapsulada para leitura do código da série SGS."""
        return self.__codigo_serie

    @property
    def url_api_json(self) -> str:
        """Propriedade encapsulada para leitura do endpoint JSON da API BCB."""
        return self.__url_api_json

    @property
    def url_api_csv(self) -> str:
        """Propriedade encapsulada para leitura do endpoint CSV da API BCB."""
        return self.__url_api_csv

    def obter_dados(self) -> pd.DataFrame:
        """
        Implementação polimórfica para obtenção dos dados da Série 4390.
        Tenta:
        1. Consultar a API pública JSON do BCB (dividida em janelas de 10 anos conforme regra do SGS).
        2. Ler o arquivo CSV local oficial caso esteja no diretório.
        3. Carregar a base histórica oficial de contingência (1995-2026) se sem conexão.
        """
        self._ultima_extracao = datetime.now()

        # 1. Tentativa via API oficial do Banco Central (janelas de 10 anos)
        try:
            registros_api: List[Dict[str, str]] = []
            janelas = [
                ("01/01/1995", "31/12/2004"),
                ("01/01/2005", "31/12/2014"),
                ("01/01/2015", "31/12/2024"),
                ("01/01/2025", "31/12/2026"),
            ]
            headers = {"User-Agent": "Mozilla/5.0 (ProjetoCDIA-PUCSP/1.0)", "Accept": "application/json"}
            for data_ini, data_fim in janelas:
                url = f"{self.__url_api_json}&dataInicial={data_ini}&dataFinal={data_fim}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    dados_janela = json.loads(resp.read().decode("utf-8"))
                    if isinstance(dados_janela, list):
                        registros_api.extend(dados_janela)

            if len(registros_api) > 100:
                self._modo_extracao = "API Online BCB (SGS 4390 JSON)"
                return pd.DataFrame(registros_api)
        except Exception:
            pass

        # 2. Tentativa via arquivo CSV local (caso já exista no diretório do projeto)
        if self.__caminho_csv_local and Path(self.__caminho_csv_local).exists():
            try:
                df_csv = pd.read_csv(self.__caminho_csv_local, sep=";", decimal=",")
                if {"data", "valor"}.issubset(set(df_csv.columns)) and len(df_csv) > 50:
                    self._modo_extracao = f"Arquivo CSV Local ({self.__caminho_csv_local})"
                    return df_csv
            except Exception:
                pass

        # 3. Fallback resiliente com os dados históricos oficiais da Série 4390
        self._modo_extracao = "Base Histórica Oficial Integrada (SGS 4390 - BCB)"
        return self._construir_dataframe_oficial_contingencia()

    @staticmethod
    def _construir_dataframe_oficial_contingencia() -> pd.DataFrame:
        """Constrói o DataFrame no formato exato do SGS/BCB ('data', 'valor')."""
        linhas: List[Dict[str, Any]] = []
        for ano, valores_mensais in sorted(HISTORICO_OFICIAL_SGS_4390.items()):
            for indice_mes, taxa in enumerate(valores_mensais, start=1):
                linhas.append(
                    {
                        "data": f"01/{indice_mes:02d}/{ano}",
                        "valor": f"{taxa:.2f}",
                    }
                )
        return pd.DataFrame(linhas)


class Indicador(ABC):
    """
    Classe Base Abstrata que representa um indicador de negócio/econômico calculado.
    Demonstra Encapsulamento, Herança e Polimorfismo (Etapa 3).
    """

    def __init__(self, nome: str, valor: float, unidade: str, descricao: str) -> None:
        self._nome = nome
        self._valor = float(valor)
        self._unidade = unidade
        self._descricao = descricao

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def valor(self) -> float:
        return self._valor

    @property
    def unidade(self) -> str:
        return self._unidade

    @property
    def descricao(self) -> str:
        return self._descricao

    @abstractmethod
    def formatar_valor(self) -> str:
        """Método polimórfico para formatação visual do indicador."""
        pass

    @abstractmethod
    def classificar_cenario(self) -> str:
        """Método polimórfico que interpreta o valor do indicador para apoio à decisão."""
        pass

    def para_dicionario(self) -> Dict[str, Any]:
        """Exporta os metadados e o resultado formatado do indicador."""
        return {
            "nome": self._nome,
            "valor_numerico": round(self._valor, 4),
            "valor_formatado": self.formatar_valor(),
            "unidade": self._unidade,
            "descricao": self._descricao,
            "interpretacao": self.classificar_cenario(),
        }


class IndicadorEstatistico(Indicador):
    """
    Subclasse de Indicador voltada para métricas estatísticas da taxa mensal
    (ex.: Média Mensal, Mediana, Volatilidade/Desvio-Padrão, Máximo e Mínimo).
    """

    def __init__(
        self,
        nome: str,
        valor: float,
        unidade: str = "% a.m.",
        descricao: str = "",
        casas_decimais: int = 2,
    ) -> None:
        super().__init__(nome, valor, unidade, descricao)
        self.__casas_decimais = casas_decimais

    def formatar_valor(self) -> str:
        valor_str = f"{self._valor:.{self.__casas_decimais}f}".replace(".", ",")
        return f"{valor_str}{self._unidade}"

    def classificar_cenario(self) -> str:
        if self._valor >= 1.00:
            return "Patamar mensal elevado (Política Monetária Contracionista)"
        if self._valor >= 0.60:
            return "Patamar mensal moderado (Equilíbrio Neutro)"
        return "Patamar mensal reduzido (Estímulo Monetário / Juros Baixos)"


class IndicadorFinanceiro(Indicador):
    """
    Subclasse de Indicador voltada para métricas de capitalização composta e retorno
    acumulado (ex.: Taxa Acumulada no Período, Taxa Anualizada Composta, Montante R$).
    Sobrescreve polimorficamente `formatar_valor` e `classificar_cenario`.
    """

    def __init__(
        self,
        nome: str,
        valor: float,
        unidade: str = "% a.a.",
        descricao: str = "",
        eh_moeda: bool = False,
    ) -> None:
        super().__init__(nome, valor, unidade, descricao)
        self.__eh_moeda = eh_moeda

    def formatar_valor(self) -> str:
        if self.__eh_moeda:
            texto = f"{self._valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {texto}"
        valor_str = f"{self._valor:.2f}".replace(".", ",")
        return f"{valor_str}{self._unidade}"

    def classificar_cenario(self) -> str:
        if self.__eh_moeda:
            return "Resultado de capitalização composta em títulos pós-fixados (Tesouro Selic)"
        if self._valor >= 12.0:
            return "Custo de crédito severo e alta atratividade na Renda Fixa pós-fixada"
        if self._valor >= 7.0:
            return "Custo de oportunidade moderado para alocação de capital"
        return "Cenário favorável à tomada de crédito e investimentos produtivos"


class AnalisadorSelic:
    """
    Classe responsável pelo processamento, higienização e análise estatística/financeira
    dos dados com a biblioteca Pandas (Etapas 2 e 4).
    Aplica o Princípio da Responsabilidade Única (SRP).
    """

    NOMES_MESES: Dict[int, str] = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }

    def __init__(self, df_bruto: pd.DataFrame) -> None:
        if df_bruto is None or df_bruto.empty:
            raise ValueError("O DataFrame bruto fornecido ao AnalisadorSelic está vazio.")
        self.__df_bruto = df_bruto.copy()
        self.__relatorio_qualidade: Dict[str, Any] = {}
        self.__df_tratado: pd.DataFrame = self._executar_pipeline_tratamento()

    @property
    def df_bruto(self) -> pd.DataFrame:
        """Retorna cópia protegida do DataFrame bruto (Encapsulamento)."""
        return self.__df_bruto.copy()

    @property
    def df_tratado(self) -> pd.DataFrame:
        """Retorna cópia protegida do DataFrame tratado e enriquecido (Encapsulamento)."""
        return self.__df_tratado.copy()

    @property
    def relatorio_qualidade(self) -> Dict[str, Any]:
        """Retorna o diagnóstico de valores ausentes, duplicidades e tipos (Etapa 2)."""
        return dict(self.__relatorio_qualidade)

    def _executar_pipeline_tratamento(self) -> pd.DataFrame:
        """
        Executa todas as operações obrigatórias das Etapas 2 e 4 com Pandas:
        - Identificação de variáveis e tipos
        - Verificação e tratamento de valores ausentes (dropna / coerção segura)
        - Verificação e remoção de duplicidades (drop_duplicates)
        - Ordenação cronológica dos dados (sort_values)
        - Criação de colunas derivadas financeiras e classificação de regime monetário
        """
        df = self.__df_bruto.copy()
        total_inicial = len(df)

        # Padronização dos nomes das colunas
        df.columns = [str(c).strip().lower() for c in df.columns]
        if "data" not in df.columns or "valor" not in df.columns:
            raise KeyError("O dataset deve conter as colunas 'data' e 'valor'.")

        # Conversão de tipos (data para datetime e valor para float)
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
        df["taxa_mensal"] = (
            df["valor"]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
        )

        # Contabilização de valores ausentes/inconsistentes antes do tratamento
        valores_ausentes = int(df["data"].isna().sum() + df["taxa_mensal"].isna().sum())
        inconsistencias_negativas = int((df["taxa_mensal"] < 0).sum())

        # Tratamento de dados ausentes e inconsistências
        df = df.dropna(subset=["data", "taxa_mensal"]).copy()
        df = df[df["taxa_mensal"] >= 0].copy()

        # Verificação e remoção de duplicidades por data de competência
        duplicidades_encontradas = int(df.duplicated(subset=["data"]).sum())
        df = df.drop_duplicates(subset=["data"], keep="last").copy()

        # Ordenação cronológica estrita
        df = df.sort_values(by="data", ascending=True).reset_index(drop=True)

        # Enriquecimento de atributos temporais e financeiros
        df["ano"] = df["data"].dt.year.astype(int)
        df["mes_num"] = df["data"].dt.month.astype(int)
        df["mes_nome"] = df["mes_num"].map(self.NOMES_MESES)
        df["trimestre"] = "T" + df["data"].dt.quarter.astype(str)
        df["competencia"] = df["data"].dt.strftime("%m/%Y")
        df["decada"] = (df["ano"] // 10 * 10).astype(str) + "s"

        # Fator mensal de capitalização e equivalência anualizada composta: ((1 + i)^12 - 1) * 100
        df["fator_mensal"] = 1.0 + (df["taxa_mensal"] / 100.0)
        df["taxa_anualizada_equivalente"] = ((df["fator_mensal"] ** 12) - 1.0) * 100.0

        # Acumulado móvel em 12 meses (rolling compound return) e média móvel de 6 meses
        df["selic_acumulada_12m"] = (
            df["fator_mensal"]
            .rolling(window=12, min_periods=12)
            .apply(np.prod, raw=True)
            .sub(1.0)
            .mul(100.0)
        )
        df["media_movel_6m"] = df["taxa_mensal"].rolling(window=6, min_periods=1).mean()

        # Classificação categórica do Regime de Política Monetária
        condicoes = [
            df["taxa_mensal"] < 0.50,
            (df["taxa_mensal"] >= 0.50) & (df["taxa_mensal"] < 0.85),
            (df["taxa_mensal"] >= 0.85) & (df["taxa_mensal"] < 1.15),
            df["taxa_mensal"] >= 1.15,
        ]
        categorias = [
            "1. Expansionista (< 0,50% a.m.)",
            "2. Moderado (0,50% a 0,84% a.m.)",
            "3. Contracionista (0,85% a 1,14% a.m.)",
            "4. Fortemente Contracionista (>= 1,15% a.m.)",
        ]
        df["regime_monetario"] = np.select(condicoes, categorias, default="Não classificado")

        # Registro do relatório de auditoria e exploração inicial (Etapa 2)
        self.__relatorio_qualidade = {
            "registros_brutos": total_inicial,
            "registros_validos": len(df),
            "valores_ausentes_tratados": valores_ausentes,
            "duplicidades_removidas": duplicidades_encontradas,
            "inconsistencias_removidas": inconsistencias_negativas,
            "data_inicial": df["data"].min().strftime("%d/%m/%Y"),
            "data_final": df["data"].max().strftime("%d/%m/%Y"),
            "variaveis_e_tipos": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

        return df

    def filtrar_dados(
        self,
        ano_inicial: Optional[int] = None,
        ano_final: Optional[int] = None,
        regimes: Optional[List[str]] = None,
        meses: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Realiza seleção e filtragem de registros (Etapa 4).
        """
        df = self.__df_tratado.copy()
        if ano_inicial is not None:
            df = df[df["ano"] >= int(ano_inicial)]
        if ano_final is not None:
            df = df[df["ano"] <= int(ano_final)]
        if regimes:
            df = df[df["regime_monetario"].isin(regimes)]
        if meses:
            df = df[df["mes_num"].isin(meses)]
        return df.sort_values(by="data", ascending=True).reset_index(drop=True)

    def calcular_estatisticas_descritivas(self, df_alvo: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        Calcula estatísticas descritivas completas com Pandas (Etapa 4).
        """
        df = df_alvo if df_alvo is not None else self.__df_tratado
        if df.empty:
            return {
                "contagem_meses": 0.0,
                "media_mensal": 0.0,
                "mediana_mensal": 0.0,
                "desvio_padrao": 0.0,
                "variancia": 0.0,
                "coeficiente_variacao_pct": 0.0,
                "minimo_mensal": 0.0,
                "maximo_mensal": 0.0,
                "quartil_25": 0.0,
                "quartil_75": 0.0,
                "amplitude": 0.0,
            }

        serie = df["taxa_mensal"]
        media = float(serie.mean())
        desvio = float(serie.std(ddof=1)) if len(serie) > 1 else 0.0
        minimo = float(serie.min())
        maximo = float(serie.max())

        return {
            "contagem_meses": float(len(serie)),
            "media_mensal": round(media, 4),
            "mediana_mensal": round(float(serie.median()), 4),
            "desvio_padrao": round(desvio, 4),
            "variancia": round(float(serie.var(ddof=1)) if len(serie) > 1 else 0.0, 4),
            "coeficiente_variacao_pct": round((desvio / media * 100.0) if media > 0 else 0.0, 2),
            "minimo_mensal": round(minimo, 4),
            "maximo_mensal": round(maximo, 4),
            "quartil_25": round(float(serie.quantile(0.25)), 4),
            "quartil_75": round(float(serie.quantile(0.75)), 4),
            "amplitude": round(maximo - minimo, 4),
        }

    def agrupar_por_ano(self, df_alvo: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Realiza agrupamento (groupby) por ano calculando a taxa anual efetiva composta,
        média mensal, volatilidade, mínimo, máximo e quantidade de meses (Etapa 4).
        """
        df = df_alvo if df_alvo is not None else self.__df_tratado
        if df.empty:
            return pd.DataFrame()

        agrupado = (
            df.groupby("ano", as_index=False)
            .agg(
                meses_registrados=("taxa_mensal", "count"),
                media_mensal=("taxa_mensal", "mean"),
                mediana_mensal=("taxa_mensal", "median"),
                desvio_padrao=("taxa_mensal", "std"),
                minimo_mensal=("taxa_mensal", "min"),
                maximo_mensal=("taxa_mensal", "max"),
                fator_anual_composto=("fator_mensal", "prod"),
            )
            .sort_values(by="ano", ascending=True)
            .reset_index(drop=True)
        )
        agrupado["desvio_padrao"] = agrupado["desvio_padrao"].fillna(0.0)
        agrupado["selic_acumulada_ano_pct"] = (agrupado["fator_anual_composto"] - 1.0) * 100.0
        return agrupado

    def agrupar_por_regime(self, df_alvo: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Agrupa os registros por regime de política monetária para análise de distribuição.
        """
        df = df_alvo if df_alvo is not None else self.__df_tratado
        if df.empty:
            return pd.DataFrame()

        resumo = (
            df.groupby("regime_monetario", as_index=False)
            .agg(
                quantidade_meses=("taxa_mensal", "count"),
                taxa_media=("taxa_mensal", "mean"),
                taxa_anualizada_media=("taxa_anualizada_equivalente", "mean"),
            )
            .sort_values(by="regime_monetario", ascending=True)
            .reset_index(drop=True)
        )
        total = resumo["quantidade_meses"].sum()
        resumo["participacao_pct"] = np.where(
            total > 0, (resumo["quantidade_meses"] / total) * 100.0, 0.0
        )
        return resumo

    def agrupar_sazonalidade_mensal(self, df_alvo: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Agrupa os dados pelos 12 meses do calendário para investigar padrões sazonais.
        """
        df = df_alvo if df_alvo is not None else self.__df_tratado
        if df.empty:
            return pd.DataFrame()

        sazonal = (
            df.groupby(["mes_num", "mes_nome"], as_index=False)
            .agg(
                media_mensal=("taxa_mensal", "mean"),
                mediana_mensal=("taxa_mensal", "median"),
                maximo_historico=("taxa_mensal", "max"),
                minimo_historico=("taxa_mensal", "min"),
                ocorrencias=("taxa_mensal", "count"),
            )
            .sort_values(by="mes_num", ascending=True)
            .reset_index(drop=True)
        )
        return sazonal

    def gerar_indicadores(
        self,
        df_alvo: Optional[pd.DataFrame] = None,
        capital_inicial: float = 10000.0,
    ) -> List[Indicador]:
        """
        Elabora 6 indicadores relevantes para o problema utilizando as classes polimórficas
        IndicadorEstatistico e IndicadorFinanceiro (cumpre e supera o mínimo de 5 indicadores
        da Etapa 4).
        """
        df = df_alvo if df_alvo is not None else self.__df_tratado
        if df.empty:
            return []

        df_ord = df.sort_values(by="data", ascending=True).reset_index(drop=True)
        stats = self.calcular_estatisticas_descritivas(df_ord)

        # 1. Última Taxa Selic Mensal Vigente
        ultima_linha = df_ord.iloc[-1]
        ind_atual = IndicadorEstatistico(
            nome=f"Selic Mensal Vigente ({ultima_linha['competencia']})",
            valor=float(ultima_linha["taxa_mensal"]),
            unidade="% a.m.",
            descricao="Taxa Selic efetiva acumulada no último mês fechado da seleção.",
        )

        # 2. Selic Acumulada nos Últimos 12 Meses (Composta)
        ultimos_12 = df_ord.tail(12)
        fator_12m = float(ultimos_12["fator_mensal"].prod())
        taxa_12m = (fator_12m - 1.0) * 100.0
        ind_acum_12m = IndicadorFinanceiro(
            nome="Selic Acumulada (Últimos 12M)",
            valor=taxa_12m,
            unidade="% a.a.",
            descricao="Rentabilidade composta acumulada nos últimos 12 meses do filtro.",
        )

        # 3. Taxa Média Mensal do Período
        ind_media = IndicadorEstatistico(
            nome="Taxa Média Mensal (Período)",
            valor=stats["media_mensal"],
            unidade="% a.m.",
            descricao="Média aritmética das taxas mensais da Selic no intervalo analisado.",
        )

        # 4. Pico Histórico Mensal no Período
        linha_max = df_ord.loc[df_ord["taxa_mensal"].idxmax()]
        ind_maximo = IndicadorEstatistico(
            nome=f"Pico Mensal ({linha_max['competencia']})",
            valor=float(linha_max["taxa_mensal"]),
            unidade="% a.m.",
            descricao=f"Maior taxa mensal registrada no período selecionado ({linha_max['competencia']}).",
        )

        # 5. Mínima Histórica Mensal no Período
        linha_min = df_ord.loc[df_ord["taxa_mensal"].idxmin()]
        ind_minimo = IndicadorEstatistico(
            nome=f"Mínima Mensal ({linha_min['competencia']})",
            valor=float(linha_min["taxa_mensal"]),
            unidade="% a.m.",
            descricao=f"Menor taxa mensal registrada no período selecionado ({linha_min['competencia']}).",
        )

        # 6. Volatilidade Mensal (Desvio-Padrão)
        ind_volatilidade = IndicadorEstatistico(
            nome="Volatilidade (Desvio-Padrão)",
            valor=stats["desvio_padrao"],
            unidade=" p.p.",
            descricao="Dispersão das taxas mensais em pontos percentuais no período.",
        )

        # 7. Simulação de Capital Corrigido pela Selic no Período
        fator_total = float(df_ord["fator_mensal"].prod())
        montante_final = capital_inicial * fator_total
        ind_montante = IndicadorFinanceiro(
            nome="Capital Corrigido no Período",
            valor=montante_final,
            unidade="R$",
            descricao=f"Evolução composta de R$ {capital_inicial:,.2f} corrigidos pela Selic no período.",
            eh_moeda=True,
        )

        return [
            ind_atual,
            ind_acum_12m,
            ind_media,
            ind_maximo,
            ind_minimo,
            ind_volatilidade,
            ind_montante,
        ]


# ==============================================================================
# ETAPA 5 - DESENVOLVIMENTO DAS VISUALIZAÇÕES INTERATIVAS (PLOTLY)
# ==============================================================================

class VisualizadorSelic:
    """
    Classe responsável pela geração dos gráficos interativos com Plotly (Etapa 5).
    Implementa 5 visualizações distintas:
    1. Gráfico de Linhas: Evolução histórica da Taxa Selic Mensal e Média Móvel (6M).
    2. Gráfico de Barras: Taxa Selic Efetiva Acumulada por Ano (% a.a.).
    3. Gráfico de Setores (Rosca/Pie): Distribuição de meses por Regime Monetário.
    4. Gráfico Adicional 1 (Boxplot): Dispersão e Outliers das taxas mensais por Década/Ciclo.
    5. Gráfico Adicional 2 (Histograma): Distribuição de frequências das taxas mensais.
    """

    PALETA_CORES = {
        "primaria": "#0B3C5D",
        "secundaria": "#328CC1",
        "destaque": "#D9B310",
        "alerta": "#B82601",
        "sucesso": "#1D6A50",
    }

    def __init__(self, tema_plotly: str = "plotly_white") -> None:
        self.__tema = tema_plotly

    @property
    def tema(self) -> str:
        return self.__tema

    def criar_grafico_linhas_historico(self, df: pd.DataFrame) -> Any:
        """
        1. Gráfico de Linhas: Série temporal da Taxa Selic Mensal (% a.m.) e Média Móvel de 6 meses.
        """
        if not PLOTLY_DISPONIVEL:
            return {"tipo": "line", "titulo": "Evolução Mensal da Taxa Selic (% a.m.)", "linhas": len(df)}

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["data"],
                y=df["taxa_mensal"],
                mode="lines",
                name="Selic Acumulada no Mês (% a.m.)",
                line=dict(color=self.PALETA_CORES["primaria"], width=2.5),
                hovertemplate="<b>Competência:</b> %{x|%m/%Y}<br><b>Selic Mensal:</b> %{y:.2f}% a.m.<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["data"],
                y=df["media_movel_6m"],
                mode="lines",
                name="Média Móvel (6 Meses)",
                line=dict(color=self.PALETA_CORES["alerta"], width=2, dash="dash"),
                hovertemplate="<b>Competência:</b> %{x|%m/%Y}<br><b>Média Móvel 6M:</b> %{y:.2f}% a.m.<extra></extra>",
            )
        )
        fig.update_layout(
            title="Evolução Histórica da Taxa Selic Acumulada no Mês (% a.m.) e Média Móvel (6M)",
            xaxis_title="Data de Competência",
            yaxis_title="Taxa Selic (% ao mês)",
            template=self.__tema,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return fig

    def criar_grafico_barras_anual(self, df_anual: pd.DataFrame) -> Any:
        """
        2. Gráfico de Barras: Taxa Selic Efetiva Acumulada por Ano (% a.a.) por capitalização composta.
        """
        if not PLOTLY_DISPONIVEL:
            return {"tipo": "bar", "titulo": "Taxa Selic Acumulada por Ano (% a.a.)", "anos": len(df_anual)}

        fig = px.bar(
            df_anual,
            x="ano",
            y="selic_acumulada_ano_pct",
            text=df_anual["selic_acumulada_ano_pct"].map(lambda v: f"{v:.1f}%"),
            color="selic_acumulada_ano_pct",
            color_continuous_scale="YlGnBu",
            labels={
                "ano": "Ano",
                "selic_acumulada_ano_pct": "Selic Acumulada no Ano (% a.a.)",
            },
            title="Taxa Selic Efetiva Acumulada por Ano (% ao ano - Capitalização Composta)",
            template=self.__tema,
        )
        fig.update_traces(
            textposition="outside",
            hovertemplate="<b>Ano:</b> %{x}<br><b>Selic Acumulada:</b> %{y:.2f}% a.a.<extra></extra>",
        )
        fig.update_layout(
            xaxis=dict(tickmode="linear", dtick=1),
            yaxis_title="Taxa Acumulada no Ano (% a.a.)",
            coloraxis_showscale=False,
        )
        return fig

    def criar_grafico_setores_regimes(self, df_regimes: pd.DataFrame) -> Any:
        """
        3. Gráfico de Setores (Pie/Donut): Proporção de meses em cada Regime de Política Monetária.
        """
        if not PLOTLY_DISPONIVEL:
            return {"tipo": "pie", "titulo": "Distribuição por Regime Monetário", "categorias": len(df_regimes)}

        fig = px.pie(
            df_regimes,
            names="regime_monetario",
            values="quantidade_meses",
            hole=0.42,
            color_discrete_sequence=["#2A9D8F", "#457B9D", "#E9C46A", "#E76F51"],
            title="Distribuição dos Meses por Regime de Política Monetária",
            template=self.__tema,
        )
        fig.update_traces(
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Meses: %{value}<br>Participação: %{percent}<extra></extra>",
        )
        return fig

    def criar_grafico_boxplot_decadas(self, df: pd.DataFrame) -> Any:
        """
        4. Gráfico Adicional (Boxplot): Distribuição estatística, mediana, quartis e outliers por década.
        """
        if not PLOTLY_DISPONIVEL:
            return {"tipo": "box", "titulo": "Boxplot da Taxa Selic Mensal por Década", "linhas": len(df)}

        fig = px.box(
            df,
            x="decada",
            y="taxa_mensal",
            color="decada",
            points="outliers",
            labels={
                "decada": "Década",
                "taxa_mensal": "Taxa Selic Mensal (% a.m.)",
            },
            title="Dispersão Estatística e Outliers da Taxa Selic Mensal por Década (Boxplot)",
            template=self.__tema,
        )
        fig.update_layout(showlegend=False)
        return fig

    def criar_grafico_histograma_frequencia(self, df: pd.DataFrame) -> Any:
        """
        5. Gráfico Adicional (Histograma): Distribuição de frequência das taxas mensais da Selic.
        """
        if not PLOTLY_DISPONIVEL:
            return {"tipo": "histogram", "titulo": "Histograma da Taxa Selic Mensal", "linhas": len(df)}

        fig = px.histogram(
            df,
            x="taxa_mensal",
            nbins=25,
            marginal="violin",
            color_discrete_sequence=[self.PALETA_CORES["secundaria"]],
            labels={"taxa_mensal": "Taxa Selic Mensal (% a.m.)", "count": "Frequência (Meses)"},
            title="Histograma de Frequência das Taxas Mensais da Selic",
            template=self.__tema,
        )
        fig.update_layout(yaxis_title="Quantidade de Meses")
        return fig


# ==============================================================================
# ETAPA 6 - DESENVOLVIMENTO DO DASHBOARD DINÂMICO (STREAMLIT)
# ==============================================================================

class DashboardSelic:
    """
    Classe orquestradora da aplicação web interativa em Streamlit (Etapa 6).
    Recebe as dependências por composição/injeção no construtor (__init__),
    respeitando o Princípio da Inversão de Dependência (SOLID - DIP).
    """

    def __init__(
        self,
        fonte_dados: FonteDados,
        analisador: AnalisadorSelic,
        visualizador: VisualizadorSelic,
    ) -> None:
        self.__fonte = fonte_dados
        self.__analisador = analisador
        self.__visualizador = visualizador

    def renderizar(self) -> None:
        """Renderiza todos os componentes exigidos na Etapa 6 do projeto."""
        if not STREAMLIT_DISPONIVEL:
            print(
                "Aviso: A biblioteca 'streamlit' não está instalada neste ambiente.\n"
                "Para instalar e abrir o dashboard em seu computador, execute:\n"
                "    pip install streamlit plotly pandas numpy\n"
                "    streamlit run app.py"
            )
            return

        st.set_page_config(
            page_title="Dashboard Taxa Selic (SGS 4390 - BCB)",
            page_icon="📈",
            layout="wide",
        )

        # 1. Cabeçalho Institucional e Contextualização (Etapa 1 e Etapa 6)
        st.title("📈 Sistema de Análise de Dados e Dashboard: Taxa Selic Acumulada no Mês")
        st.markdown(
            f"**Curso:** Ciência de Dados e Inteligência Artificial (CDIA) — Programação Orientada a Objetos  \n"
            f"**Fonte Pública Oficial:** [{self.__fonte.nome_fonte}]({self.__fonte.url_referencia}) | "
            f"**Modo de Carregamento:** `{self.__fonte.modo_extracao}`"
        )
        st.markdown("---")

        # 2. Barra Lateral com Filtros Interativos (Etapa 6)
        st.sidebar.header("⚙️ Filtros Interativos")
        df_completo = self.__analisador.df_tratado
        ano_min = int(df_completo["ano"].min())
        ano_max = int(df_completo["ano"].max())

        intervalo_anos: Tuple[int, int] = st.sidebar.slider(
            "Selecione o Intervalo de Anos:",
            min_value=ano_min,
            max_value=ano_max,
            value=(max(ano_min, 2000), ano_max),
            step=1,
        )

        regimes_disponiveis = sorted(df_completo["regime_monetario"].unique().tolist())
        regimes_selecionados = st.sidebar.multiselect(
            "Regime de Política Monetária:",
            options=regimes_disponiveis,
            default=regimes_disponiveis,
        )

        capital_simulacao = st.sidebar.number_input(
            "Capital Inicial para Simulação (R$):",
            min_value=100.0,
            max_value=10000000.0,
            value=10000.0,
            step=500.0,
        )

        # Aplicação dos filtros no AnalisadorSelic
        df_filtrado = self.__analisador.filtrar_dados(
            ano_inicial=intervalo_anos[0],
            ano_final=intervalo_anos[1],
            regimes=regimes_selecionados,
        )

        if df_filtrado.empty:
            st.warning("Nenhum registro encontrado para os filtros selecionados. Ajuste os parâmetros na barra lateral.")
            return

        # 3. Indicadores Principais - KPIs (Etapa 4 e Etapa 6)
        st.subheader("📌 Indicadores Principais (KPIs do Período Selecionado)")
        indicadores = self.__analisador.gerar_indicadores(
            df_alvo=df_filtrado, capital_inicial=capital_simulacao
        )

        colunas_kpi = st.columns(4)
        for idx, ind in enumerate(indicadores[:4]):
            with colunas_kpi[idx]:
                st.metric(
                    label=ind.nome,
                    value=ind.formatar_valor(),
                    help=f"{ind.descricao} | Diagnóstico: {ind.classificar_cenario()}",
                )

        colunas_kpi_2 = st.columns(3)
        for idx, ind in enumerate(indicadores[4:7]):
            with colunas_kpi_2[idx]:
                st.metric(
                    label=ind.nome,
                    value=ind.formatar_valor(),
                    help=f"{ind.descricao} | Diagnóstico: {ind.classificar_cenario()}",
                )

        st.markdown("---")

        # 4. Visualizações Dinâmicas Interativas com Plotly (Etapa 5 e Etapa 6)
        st.subheader("📊 Visualizações Dinâmicas e Análise Gráfica")

        aba_linhas, aba_barras, aba_setores, aba_distribuicao = st.tabs(
            [
                "1. Evolução Mensal (Linhas)",
                "2. Acumulado por Ano (Barras)",
                "3. Regimes Monetários (Setores)",
                "4. Dispersão e Frequência (Boxplot & Histograma)",
            ]
        )

        with aba_linhas:
            fig_linhas = self.__visualizador.criar_grafico_linhas_historico(df_filtrado)
            st.plotly_chart(fig_linhas, use_container_width=True)
            st.caption(
                "Interpretação: A curva azul exibe a taxa Selic efetiva acumulada em cada mês (% a.m.), "
                "enquanto a linha tracejada vermelha suaviza oscilações de curto prazo através da média móvel de 6 meses."
            )

        with aba_barras:
            df_anual = self.__analisador.agrupar_por_ano(df_filtrado)
            fig_barras = self.__visualizador.criar_grafico_barras_anual(df_anual)
            st.plotly_chart(fig_barras, use_container_width=True)
            st.caption(
                "Interpretação: O gráfico de barras demonstra o efeito da capitalização composta mês a mês "
                "sobre o retorno anual efetivo da Selic (% a.a.), destacando os ciclos de aperto e afrouxamento monetário."
            )

        with aba_setores:
            df_regimes = self.__analisador.agrupar_por_regime(df_filtrado)
            fig_setores = self.__visualizador.criar_grafico_setores_regimes(df_regimes)
            st.plotly_chart(fig_setores, use_container_width=True)
            st.caption(
                "Interpretação: O gráfico de rosca quantifica a proporção do tempo em que a economia brasileira "
                "operou sob regimes expansionistas, moderados ou contracionistas no recorte selecionado."
            )

        with aba_distribuicao:
            col_box, col_hist = st.columns(2)
            with col_box:
                fig_box = self.__visualizador.criar_grafico_boxplot_decadas(df_filtrado)
                st.plotly_chart(fig_box, use_container_width=True)
            with col_hist:
                fig_hist = self.__visualizador.criar_grafico_histograma_frequencia(df_filtrado)
                st.plotly_chart(fig_hist, use_container_width=True)
            st.caption(
                "Interpretação: O Boxplot evidencia a queda estrutural da dispersão e da mediana das taxas mensais "
                "após a estabilização do Plano Real (anos 1990 vs. décadas de 2000, 2010 e 2020), enquanto o Histograma "
                "revela a faixa modal de ocorrência das taxas mensais."
            )

        st.markdown("---")

        # 5. Tabela de Dados Interativa e Qualidade dos Dados (Etapa 2, Etapa 4 e Etapa 6)
        st.subheader("🗂️ Tabela de Dados Tratados e Estatísticas Descritivas")
        col_tab1, col_tab2 = st.columns([2, 1])

        with col_tab1:
            st.markdown("**Registros Mensais Filtrados (Mais recentes primeiro):**")
            colunas_exibicao = [
                "competencia",
                "ano",
                "mes_nome",
                "taxa_mensal",
                "taxa_anualizada_equivalente",
                "selic_acumulada_12m",
                "regime_monetario",
            ]
            st.dataframe(
                df_filtrado.sort_values(by="data", ascending=False)[colunas_exibicao],
                use_container_width=True,
                hide_index=True,
            )

        with col_tab2:
            st.markdown("**Resumo Estatístico Descritivo (Pandas):**")
            stats = self.__analisador.calcular_estatisticas_descritivas(df_filtrado)
            df_stats = pd.DataFrame(
                [
                    {"Métrica Estatística": "Meses Analisados (N)", "Valor": f"{int(stats['contagem_meses'])}"},
                    {"Métrica Estatística": "Média Mensal", "Valor": f"{stats['media_mensal']:.2f}% a.m."},
                    {"Métrica Estatística": "Mediana Mensal", "Valor": f"{stats['mediana_mensal']:.2f}% a.m."},
                    {"Métrica Estatística": "Desvio-Padrão", "Valor": f"{stats['desvio_padrao']:.2f} p.p."},
                    {"Métrica Estatística": "Coeficiente de Variação", "Valor": f"{stats['coeficiente_variacao_pct']:.2f}%"},
                    {"Métrica Estatística": "Mínimo Mensal", "Valor": f"{stats['minimo_mensal']:.2f}% a.m."},
                    {"Métrica Estatística": "Quartil 25% (Q1)", "Valor": f"{stats['quartil_25']:.2f}% a.m."},
                    {"Métrica Estatística": "Quartil 75% (Q3)", "Valor": f"{stats['quartil_75']:.2f}% a.m."},
                    {"Métrica Estatística": "Máximo Mensal", "Valor": f"{stats['maximo_mensal']:.2f}% a.m."},
                ]
            )
            st.table(df_stats)

        st.markdown("---")

        # 6. Análise Interpretativa e Respostas às Perguntas de Pesquisa (Etapa 1 e Etapa 6)
        st.subheader("🧠 Análise Interpretativa e Apoio à Tomada de Decisão")
        st.markdown(
            """
            1. **Como os ciclos da Taxa Selic impactam a tomada de decisão entre crédito e investimentos em Renda Fixa?**  
               Em períodos de **regime contracionista** (taxa mensal $\\ge 0,85\\%$ a.m., equivalente a mais de $10,7\\%$ a.a.), o custo do crédito corporativo e ao consumidor encarece fortemente, desestimulando alavancagem e financiamentos de longo prazo, ao passo que aplicações pós-fixadas atreladas à Selic (como o Tesouro Selic) oferecem elevada rentabilidade com baixíssimo risco de mercado.
            2. **Quais foram os períodos de maior e menor aperto monetário na série pós-Plano Real?**  
               A mínima histórica ocorreu entre **agosto de 2020 e fevereiro de 2021** (durante a pandemia de COVID-19), quando a Selic mensal atingiu **0,13% a.m.** em fevereiro de 2021 (acumulado anual de apenas **2,75% em 2020** e **4,44% em 2021**). Em contraste, após os choques inflacionários globais e domésticos, a taxa voltou a superar **1,00% a.m.** entre 2022 e 2026, acumulando **14,33% em 2025**.
            3. **Por que a capitalização composta anual difere da simples multiplicação da taxa mensal por 12?**  
               Porque o rendimento da Selic incide de forma composta (juros sobre juros): $\\text{Taxa Anual} = (1 + i_{\\text{mensal}})^{12} - 1$. Em patamares elevados (por exemplo, $1,15\\%$ a.m.), a soma linear indicaria $13,80\\%$ a.a., mas a capitalização composta resulta em **$14,71\\%$ a.a.**, diferença expressiva em contratos de longo prazo e gestão de tesouraria.
            """
        )


# ==============================================================================
# ETAPA 7 - INTEGRAÇÃO, GERAÇÃO DO CSV OFICIAL E TESTES AUTOMATIZADOS DO SISTEMA
# ==============================================================================

def exportar_csv_local(caminho_destino: str = "selic_sgs_4390.csv") -> Path:
    """
    Gera o arquivo CSV local no padrão exato da Série 4390 do SGS/BCB
    (separador ponto-e-vírgula e vírgula decimal) para garantir reprodutibilidade.
    """
    df_padrao = FonteDadosBCB._construir_dataframe_oficial_contingencia()
    df_padrao["valor"] = df_padrao["valor"].str.replace(".", ",", regex=False)
    destino = Path(caminho_destino)
    df_padrao.to_csv(destino, sep=";", index=False, encoding="utf-8")
    return destino


def executar_suite_validacao() -> None:
    """
    Executa testes integrados em todas as classes, métodos, agrupamentos,
    indicadores polimórficos e visualizações para comprovar ausência de erros.
    """
    print("=" * 78)
    print("INICIANDO SUÍTE DE TESTES E VALIDAÇÃO DO SISTEMA (SÉRIE SGS 4390 - BCB)")
    print("=" * 78)

    # 1. Teste de instanciamento e herança da FonteDadosBCB
    fonte: FonteDados = FonteDadosBCB(codigo_serie=4390)
    assert isinstance(fonte, FonteDados), "Erro: FonteDadosBCB deve herdar de FonteDados."
    df_bruto = fonte.obter_dados()
    assert not df_bruto.empty, "Erro: O DataFrame bruto retornado não pode estar vazio."
    print(f"[OK] 1. FonteDadosBCB carregada com sucesso ({len(df_bruto)} registros | Modo: {fonte.modo_extracao}).")

    # 2. Teste do AnalisadorSelic e pipeline de tratamento com Pandas
    analisador = AnalisadorSelic(df_bruto)
    df_tratado = analisador.df_tratado
    qualidade = analisador.relatorio_qualidade
    assert qualidade["registros_validos"] >= 350, "Erro: Quantidade insuficiente de meses tratados."
    assert df_tratado["taxa_mensal"].isna().sum() == 0, "Erro: Não deve haver valores ausentes após tratamento."
    assert df_tratado["data"].is_monotonic_increasing, "Erro: Os dados devem estar estritamente ordenados por data."
    print(
        f"[OK] 2. AnalisadorSelic validado ({qualidade['registros_validos']} meses de "
        f"{qualidade['data_inicial']} a {qualidade['data_final']})."
    )

    # 3. Teste de Seleção, Filtragem, Agrupamento e Estatísticas Descritivas (Etapa 4)
    df_2020_2026 = analisador.filtrar_dados(ano_inicial=2020, ano_final=2026)
    assert df_2020_2026["ano"].min() == 2020 and df_2020_2026["ano"].max() == 2026
    stats = analisador.calcular_estatisticas_descritivas(df_2020_2026)
    df_anual = analisador.agrupar_por_ano(df_2020_2026)
    df_regimes = analisador.agrupar_por_regime(df_2020_2026)
    df_sazonal = analisador.agrupar_sazonalidade_mensal(df_2020_2026)
    assert len(df_anual) == 7, "Erro: O agrupamento anual 2020-2026 deve conter 7 anos."
    assert not df_regimes.empty and not df_sazonal.empty
    print(
        f"[OK] 3. Operações Pandas (Filtro 2020-2026): Média = {stats['media_mensal']:.2f}% a.m., "
        f"Mín = {stats['minimo_mensal']:.2f}% a.m., Máx = {stats['maximo_mensal']:.2f}% a.m."
    )

    # 4. Teste de Polimorfismo e Encapsulamento dos Indicadores (Etapa 3 e Etapa 4)
    indicadores = analisador.gerar_indicadores(df_2020_2026, capital_inicial=10000.0)
    assert len(indicadores) >= 5, "Erro: O projeto exige pelo menos 5 indicadores."
    print(f"[OK] 4. Indicadores Polimórficos gerados ({len(indicadores)} indicadores):")
    for ind in indicadores:
        assert isinstance(ind, Indicador)
        info = ind.para_dicionario()
        print(f"     - {info['nome']}: {info['valor_formatado']} -> {info['interpretacao']}")

    # 5. Teste do VisualizadorSelic (Etapa 5)
    visualizador = VisualizadorSelic()
    g_linhas = visualizador.criar_grafico_linhas_historico(df_2020_2026)
    g_barras = visualizador.criar_grafico_barras_anual(df_anual)
    g_setores = visualizador.criar_grafico_setores_regimes(df_regimes)
    g_box = visualizador.criar_grafico_boxplot_decadas(df_tratado)
    g_hist = visualizador.criar_grafico_histograma_frequencia(df_tratado)
    assert all(g is not None for g in [g_linhas, g_barras, g_setores, g_box, g_hist])
    print("[OK] 5. VisualizadorSelic testado com 5 gráficos interativos (Linhas, Barras, Setores, Boxplot, Histograma).")

    print("=" * 78)
    print("TODOS OS TESTES PASSARAM COM SUCESSO! NENHUM ERRO ENCONTRADO.")
    print("=" * 78)


# ==============================================================================
# PONTO DE ENTRADA DA APLICAÇÃO
# ==============================================================================

def main() -> None:
    if "--test" in sys.argv:
        executar_suite_validacao()
        return

    fonte = FonteDadosBCB(codigo_serie=4390)
    df_bruto = fonte.obter_dados()
    analisador = AnalisadorSelic(df_bruto)
    visualizador = VisualizadorSelic()
    dashboard = DashboardSelic(fonte, analisador, visualizador)

    if STREAMLIT_DISPONIVEL and hasattr(st, "runtime") and st.runtime.exists():
        dashboard.renderizar()
    else:
        # Caso executado via `python app.py` diretamente no terminal, roda a validação
        # e exibe instruções claras de como abrir o painel Streamlit.
        executar_suite_validacao()
        print("\nPara iniciar o Dashboard Web Interativo no navegador, execute:")
        print("    streamlit run app.py")


if __name__ == "__main__":
    main()