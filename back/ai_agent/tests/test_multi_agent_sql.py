"""
Testes do subsistema multiagente (supervisor) de geração de SQL.

Cobre: ranking/fallback de resolução de entidade, ferramentas do sql_writer
(gravação em `session`, remoção de LIMIT em count_matching_rows), o roteador
de feature flag como função pura, e o fallback determinístico de
multi_agent_sql_node quando o pipeline multiagente falha.

Sem chamadas reais de LLM/DB — mesma convenção de test_agent.py.
"""
import os
from unittest.mock import patch, MagicMock

from django.test import TestCase


class EntityResolutionToolsTest(TestCase):

    def test_rank_candidates_orders_by_similarity_desc(self):
        from ai_agent.tools.entity_resolution_tools import _rank_candidates

        ranked = _rank_candidates("loreto", ["MSC LORETO", "SANTOS EXPRESS", "LORETO STAR"])

        scores = [score for _, score in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(0.0 <= s <= 1.0 for s in scores))

    @patch("ai_agent.tools.entity_resolution_tools.connection")
    def test_resolve_column_value_prefilter_hit(self, mock_connection):
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [("MSC LORETO",), ("MSC LORETTO",)]
        mock_connection.cursor.return_value = mock_cursor

        from ai_agent.tools.entity_resolution_tools import _resolve_column_value
        text = _resolve_column_value("atracacoes_navio", "navio", "loreto")

        self.assertIn("MSC LORETO", text)
        self.assertEqual(mock_cursor.execute.call_count, 1)

    @patch("ai_agent.tools.entity_resolution_tools.connection")
    def test_resolve_column_value_fullscan_fallback_when_prefilter_empty(self, mock_connection):
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.side_effect = [[], [("MSC LORETO",)]]
        mock_connection.cursor.return_value = mock_cursor

        from ai_agent.tools.entity_resolution_tools import _resolve_column_value
        text = _resolve_column_value("atracacoes_navio", "navio", "loretto")

        self.assertIn("MSC LORETO", text)
        self.assertEqual(mock_cursor.execute.call_count, 2)

    @patch("ai_agent.tools.entity_resolution_tools.connection")
    def test_resolve_column_value_no_candidates(self, mock_connection):
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.side_effect = [[], []]
        mock_connection.cursor.return_value = mock_cursor

        from ai_agent.tools.entity_resolution_tools import _resolve_column_value
        text = _resolve_column_value("atracacoes_navio", "navio", "xyz")

        self.assertIn("Nenhum valor encontrado", text)


class SqlAgentToolsTest(TestCase):

    @patch("ai_agent.tools.sql_agent_tools.sql_executor_tool")
    @patch("ai_agent.tools.sql_agent_tools.sql_validator_tool")
    def test_run_sql_writes_session_only_on_success(self, mock_validator, mock_executor):
        mock_validator.return_value = {"is_valid": True, "errors": [], "warnings": [], "tables_referenced": []}
        mock_executor.return_value = {
            "success": True, "columns": ["navio"], "rows": [["MSC LORETO"]], "row_count": 1,
            "truncated": False, "limited_by_sql": True, "limit_value": 50,
            "dict_rows": [{"navio": "MSC LORETO"}], "error": None,
        }

        from ai_agent.tools.sql_agent_tools import make_sql_agent_tools
        session = {}
        run_sql, _ = make_sql_agent_tools(session)

        run_sql.invoke({"sql": "SELECT navio FROM atracacoes_navio LIMIT 50"})

        self.assertEqual(session["sql"], "SELECT navio FROM atracacoes_navio LIMIT 50")
        self.assertTrue(session["result"]["success"])

    @patch("ai_agent.tools.sql_agent_tools.sql_executor_tool")
    @patch("ai_agent.tools.sql_agent_tools.sql_validator_tool")
    def test_run_sql_does_not_write_session_on_validation_failure(self, mock_validator, mock_executor):
        mock_validator.return_value = {"is_valid": False, "errors": ["SQL inválido"], "warnings": [], "tables_referenced": []}

        from ai_agent.tools.sql_agent_tools import make_sql_agent_tools
        session = {}
        run_sql, _ = make_sql_agent_tools(session)

        run_sql.invoke({"sql": "SELECT * FROM tabela_inexistente"})

        self.assertNotIn("sql", session)
        mock_executor.assert_not_called()

    @patch("ai_agent.tools.sql_agent_tools.sql_executor_tool")
    @patch("ai_agent.tools.sql_agent_tools.sql_validator_tool")
    def test_count_matching_rows_strips_limit_before_wrapping(self, mock_validator, mock_executor):
        mock_validator.return_value = {"is_valid": True, "errors": [], "warnings": [], "tables_referenced": []}
        mock_executor.return_value = {
            "success": True, "columns": ["total"], "rows": [[42]], "row_count": 1,
            "truncated": False, "limited_by_sql": False, "limit_value": None,
            "dict_rows": [{"total": 42}], "error": None,
        }

        from ai_agent.tools.sql_agent_tools import make_sql_agent_tools
        session = {}
        _, count_matching_rows = make_sql_agent_tools(session)

        text = count_matching_rows.invoke({"sql": "SELECT * FROM atracacoes_navio LIMIT 50"})

        self.assertIn("42", text)
        called_sql = mock_executor.call_args[0][0]
        self.assertNotIn("LIMIT 50", called_sql.upper())
        self.assertIn("_CNT_CHECK", called_sql.upper())


class RouteSqlStrategyTest(TestCase):

    def test_defaults_to_deterministic_path(self):
        from ai_agent.graph.graph import _route_sql_strategy
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("USE_MULTI_AGENT_SQL", None)
            self.assertEqual(_route_sql_strategy({}), "generate_sql")

    def test_flag_true_routes_to_multi_agent(self):
        from ai_agent.graph.graph import _route_sql_strategy
        with patch.dict(os.environ, {"USE_MULTI_AGENT_SQL": "true"}):
            self.assertEqual(_route_sql_strategy({}), "multi_agent_sql")

    def test_flag_false_routes_to_deterministic(self):
        from ai_agent.graph.graph import _route_sql_strategy
        with patch.dict(os.environ, {"USE_MULTI_AGENT_SQL": "false"}):
            self.assertEqual(_route_sql_strategy({}), "generate_sql")


class MultiAgentSqlNodeFallbackTest(TestCase):

    @patch("ai_agent.graph.nodes.execute_sql_node")
    @patch("ai_agent.graph.nodes.generate_sql_node")
    @patch("ai_agent.graph.multi_agent_sql.build_sql_supervisor")
    def test_falls_back_to_deterministic_path_on_exception(self, mock_build, mock_generate, mock_execute):
        mock_build.side_effect = RuntimeError("falha simulada no supervisor")
        mock_generate.return_value = {"generated_sql": "SELECT 1", "sql_validation": {"is_valid": True}}
        mock_execute.return_value = {"sql_result": {"success": True, "row_count": 1}}

        from ai_agent.graph.nodes import multi_agent_sql_node
        result = multi_agent_sql_node({
            "question": "teste", "resolved_question": "teste", "preferences": {},
        })

        self.assertEqual(result["sql_strategy"], "multi_agent_fallback")
        self.assertEqual(result["generated_sql"], "SELECT 1")
        self.assertTrue(result["sql_result"]["success"])

    @patch("ai_agent.graph.nodes.generate_sql_node")
    @patch("ai_agent.graph.multi_agent_sql.build_sql_supervisor")
    def test_fallback_short_circuits_on_generate_sql_failure(self, mock_build, mock_generate):
        mock_build.side_effect = RuntimeError("falha simulada no supervisor")
        mock_generate.return_value = {
            "status": "partial", "error": "sem sql", "final_answer": "sem sql",
        }

        from ai_agent.graph.nodes import multi_agent_sql_node
        result = multi_agent_sql_node({
            "question": "teste", "resolved_question": "teste", "preferences": {},
        })

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["sql_strategy"], "multi_agent_fallback")
