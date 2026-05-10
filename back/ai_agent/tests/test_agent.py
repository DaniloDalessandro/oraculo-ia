"""
Testes de Integração do Agente IA

Testa o fluxo completo usando mocks do LLM e do banco.
"""
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient


class AgentFlowTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass"
        )
        self.client = APIClient()

    # ─── Teste de classificador com fallback ──────────────────────────────

    def test_classifier_fallback_totalizacao(self):
        from ai_agent.tools.classifier_tool import _fallback_classify
        self.assertEqual(_fallback_classify("quantas atracações ocorreram?"), "totalizacao")

    def test_classifier_fallback_ranking(self):
        from ai_agent.tools.classifier_tool import _fallback_classify
        self.assertEqual(_fallback_classify("qual o maior berço?"), "ranking")

    def test_classifier_fallback_media(self):
        from ai_agent.tools.classifier_tool import _fallback_classify
        self.assertEqual(_fallback_classify("qual a média de permanência?"), "media")

    def test_classifier_fallback_evolucao(self):
        from ai_agent.tools.classifier_tool import _fallback_classify
        self.assertEqual(_fallback_classify("evolução mensal de PLR"), "evolucao_temporal")

    # ─── Teste do executor SQL com mock do banco ──────────────────────────

    @patch("ai_agent.services.sql_service.connection")
    def test_sql_executor_success(self, mock_connection):
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.description = [("id",), ("nome",)]
        mock_cursor.fetchall.return_value = [(1, "Navio A"), (2, "Navio B")]
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.settings_dict = {"ENGINE": "django.db.backends.sqlite3"}

        from ai_agent.tools.sql_executor_tool import sql_executor_tool
        result = sql_executor_tool("SELECT id, nome FROM navios LIMIT 10")

        self.assertTrue(result["success"])
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["columns"], ["id", "nome"])

    # ─── Teste da view /ask/ com mock do agente ───────────────────────────

    @patch("ai_agent.views.run_agent")
    def test_ask_endpoint_success(self, mock_run_agent):
        mock_run_agent.return_value = {
            "answer": "Total de 150 atracações em 2025.",
            "intent": "totalizacao",
            "sql": "SELECT COUNT(*) FROM atracacoes",
            "validation_sql": "",
            "filters": {"row_count": 1},
            "status": "success",
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/ai-agent/ask/",
            {"question": "Quantas atracações em 2025?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("answer", data)

    def test_ask_endpoint_empty_question(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/ai-agent/ask/",
            {"question": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_ask_endpoint_unauthenticated(self):
        response = self.client.post(
            "/ai-agent/ask/",
            {"question": "Teste"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    # ─── Teste do schema service ──────────────────────────────────────────

    def test_schema_service_cache(self):
        from ai_agent.services.schema_service import SchemaService
        svc = SchemaService()

        # Primeira leitura
        schema1 = svc.introspect()
        # Segunda leitura deve usar cache
        schema2 = svc.introspect()

        self.assertIs(schema1, schema2)  # Mesmo objeto (cache)

    def test_schema_service_invalidate(self):
        from ai_agent.services.schema_service import SchemaService
        svc = SchemaService()

        schema1 = svc.introspect()
        svc.invalidate_cache()
        schema2 = svc.introspect()

        # Após invalidação, deve ser um novo dict (não o mesmo objeto)
        self.assertIsNot(schema1, schema2)

    # ─── Teste do AIAgentLog ──────────────────────────────────────────────

    def test_log_creation(self):
        from ai_agent.logs.logger import log_interaction

        log = log_interaction(
            question="Teste de log",
            detected_intent="totalizacao",
            generated_sql="SELECT COUNT(*) FROM atracacoes",
            final_answer="Resposta de teste",
            status="success",
            execution_time_ms=150,
            user=self.user,
        )

        self.assertIsNotNone(log)
        self.assertEqual(log.status, "success")
        self.assertEqual(log.detected_intent, "totalizacao")
