"""
SQL Agent Tools — ferramentas do agente sql_writer.

Reaproveita sql_validator_tool/sql_executor_tool (mesma validacao de
seguranca do caminho deterministico hoje usado por generate_sql_node/
execute_sql_node) e adiciona count_matching_rows, a ferramenta que ataca
diretamente o problema de completude: verificar o total real de linhas
antes de concluir "nao encontrado" ou finalizar uma listagem cortada
por LIMIT.

Como create_react_agent/create_supervisor so devolvem uma lista de
mensagens, run_sql grava o ultimo SQL validado+executado com sucesso no
dict `session`, fechado no closure — o no do grafo le `session` depois
do agente terminar, em vez de tentar parsear a ultima mensagem como SQL.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict

from langchain_core.tools import tool

from ai_agent.tools.sql_executor_tool import sql_executor_tool, format_result_for_llm
from ai_agent.tools.sql_validator_tool import sql_validator_tool

logger = logging.getLogger("ai_agent")

_LIMIT_RE = re.compile(r"\bLIMIT\s+\d+\b\s*;?\s*$", re.IGNORECASE)


def make_sql_agent_tools(session: Dict[str, Any]) -> list:
    """Cria as ferramentas do agente sql_writer, gravando o ultimo SQL bem-sucedido em `session`."""

    @tool
    def run_sql(sql: str) -> str:
        """
        Valida e executa uma consulta SQL SELECT contra o banco (atracacoes_navio,
        cargas_atracacao). Retorna uma previa tabular do resultado. Use LIMIT nas
        listagens, mas SEMPRE confira a completude com count_matching_rows antes
        de concluir que um resultado esta vazio ou incompleto.
        """
        try:
            validation = sql_validator_tool(sql)
            if not validation["is_valid"]:
                return "SQL invalido: " + "; ".join(validation["errors"])

            result = sql_executor_tool(sql, row_limit=200)
            if not result["success"]:
                return f"Erro ao executar a consulta: {result.get('error', 'desconhecido')}"

            session["sql"] = sql
            session["validation"] = validation
            session["result"] = result
            return format_result_for_llm(result, max_rows=50)
        except Exception as exc:
            logger.warning("[sql_agent_tools] run_sql falhou: %s", exc)
            return f"Erro ao processar a consulta: {exc}"

    @tool
    def count_matching_rows(sql: str) -> str:
        """
        Retorna o total real de linhas que uma consulta produziria sem o LIMIT,
        sem trazer os dados. Use SEMPRE antes de concluir 'nao encontrado' ou de
        finalizar uma listagem que pode ter sido cortada por LIMIT.
        """
        try:
            stripped = _LIMIT_RE.sub("", sql.strip().rstrip(";")).strip()
            count_sql = f"SELECT COUNT(*) AS total FROM ({stripped}) AS _cnt_check"

            validation = sql_validator_tool(count_sql)
            if not validation["is_valid"]:
                return "Nao foi possivel contar: " + "; ".join(validation["errors"])

            result = sql_executor_tool(count_sql, row_limit=1)
            if not result["success"]:
                return f"Erro ao contar linhas: {result.get('error', 'desconhecido')}"

            total = result["dict_rows"][0]["total"] if result["dict_rows"] else 0
            return f"Total real de linhas (sem LIMIT): {total}"
        except Exception as exc:
            logger.warning("[sql_agent_tools] count_matching_rows falhou: %s", exc)
            return f"Erro ao contar linhas: {exc}"

    return [run_sql, count_matching_rows]
