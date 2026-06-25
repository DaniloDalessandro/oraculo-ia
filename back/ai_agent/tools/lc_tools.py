"""
LangChain @tool — Ferramentas do sub-agente de análise.

Usa o padrão de closure para capturar o resultado SQL e a pergunta,
evitando passar grandes payloads JSON como argumentos de ferramenta.

Uso:
    tools = make_analysis_tools(question, result, intent)
    agent = create_react_agent(llm, tools)
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger("ai_agent")


def make_analysis_tools(
    question: str,
    result: dict[str, Any],
    intent: str,
) -> list:
    """
    Cria ferramentas de análise com contexto fechado sobre os dados SQL.

    Cada ferramenta recebe o resultado automaticamente — o LLM não precisa
    passar grandes JSON como argumentos.
    """

    rows: list[dict] = result.get("dict_rows", [])
    columns: list[str] = result.get("columns", [])

    # ── Análise estatística completa ──────────────────────────────────────── #

    @tool
    def run_statistical_analysis() -> str:
        """
        Executa análise estatística completa sobre os dados retornados pela consulta SQL.
        Detecta tendências, sazonalidade, anomalias e calcula estatísticas descritivas.
        Use quando quiser entender padrões nos dados (evolução temporal, comparações, rankings).
        """
        from ai_agent.tools.statistics_skill import run_statistics_skill
        try:
            analysis = run_statistics_skill(
                question=question,
                result=result,
                agent_intent=intent,
            )
            text = analysis.get("stat_context_text", "")
            return text if text else "Dados insuficientes para análise estatística."
        except Exception as exc:
            logger.warning("[lc_tools] run_statistical_analysis falhou: %s", exc)
            return f"Análise estatística indisponível: {exc}"

    # ── Inteligência externa (notícias + eventos) ─────────────────────────── #

    @tool
    def run_external_intelligence(stat_context: str = "") -> str:
        """
        Pesquisa eventos externos, notícias e fatores macroeconômicos que podem
        explicar padrões ou anomalias detectados nos dados portuários.
        Use quando o usuário pergunta 'por que' algo aconteceu, ou quando há
        anomalias significativas nos dados.
        Argumento opcional: stat_context — resumo da análise estatística já realizada.
        """
        from ai_agent.tools.external_intelligence_skill import run_external_intelligence_skill
        stat_analysis = {
            "stat_context_text": stat_context,
            "confidence_score": 0.8,
            "data_quality_score": 0.8,
            "analyses_run": [],
            "warnings": [],
        }
        try:
            analysis = run_external_intelligence_skill(
                question=question,
                result=result,
                stat_analysis=stat_analysis,
                intent=intent,
            )
            text = analysis.get("intel_context_text", "")
            return text if text else "Nenhum evento externo relevante encontrado."
        except Exception as exc:
            logger.warning("[lc_tools] run_external_intelligence falhou: %s", exc)
            return f"Inteligência externa indisponível: {exc}"

    # ── Dados descritivos rápidos ─────────────────────────────────────────── #

    @tool
    def describe_data() -> str:
        """
        Retorna um resumo descritivo dos dados: número de linhas, colunas,
        tipos de dados e amostras de valores. Use para entender a estrutura
        dos dados antes de escolher análises mais específicas.
        """
        try:
            n = len(rows)
            col_info = ", ".join(columns[:10])
            if not rows:
                return "Nenhum dado disponível."
            sample = rows[:3]
            sample_text = json.dumps(sample, ensure_ascii=False, default=str)
            return (
                f"Linhas: {n} | Colunas: {col_info}\n"
                f"Amostra (3 primeiras linhas):\n{sample_text}"
            )
        except Exception as exc:
            return f"Erro ao descrever dados: {exc}"

    # ── KPIs operacionais portuários ──────────────────────────────────────── #

    @tool
    def calculate_port_kpis() -> str:
        """
        Calcula KPIs operacionais portuários específicos: PLR (Prancha Líquida Real),
        throughput, eficiência de berço, tempo médio de operação.
        Use quando os dados contêm métricas de atracação, tonelagem ou operações portuárias.
        """
        from ai_agent.tools.operational_kpi_tool import operational_kpi_tool
        try:
            kpis = operational_kpi_tool(rows, columns, intent)
            return json.dumps(kpis, ensure_ascii=False, default=str, indent=2)
        except Exception as exc:
            logger.warning("[lc_tools] calculate_port_kpis falhou: %s", exc)
            return f"KPIs indisponíveis: {exc}"

    return [
        run_statistical_analysis,
        run_external_intelligence,
        describe_data,
        calculate_port_kpis,
    ]
