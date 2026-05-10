"""
Learning Service

Salva padrões de consultas bem-sucedidas e recupera SQLs similares
para reutilização como hint na geração de novas consultas.
"""
import logging
from typing import Dict, List, Optional

from ai_agent.services.semantic_search_service import find_best_match

logger = logging.getLogger("ai_agent")

# Similaridade mínima para considerar um match
SIMILARITY_THRESHOLD = 0.72
# Quantos registros carregar para busca
MAX_CANDIDATES = 100


class LearningService:

    def save(
        self,
        question: str,
        intent: str,
        sql: str,
        execution_time_ms: int = 0,
        chart_type: str = "",
        row_count: int = 0,
    ) -> None:
        """Salva uma consulta bem-sucedida no banco de aprendizado."""
        try:
            from ai_agent.models import AIAgentLearning
            from ai_agent.services.semantic_search_service import text_similarity

            # Verificar se já existe entrada muito similar
            recent = AIAgentLearning.objects.order_by("-last_used_at")[:MAX_CANDIDATES]
            patterns = [r.question_pattern for r in recent]
            match = find_best_match(question, patterns, threshold=0.88)

            if match is not None:
                # Atualiza entrada existente
                idx, score = match
                entry = recent[idx]
                entry.times_used += 1
                entry.execution_time_ms = (entry.execution_time_ms + execution_time_ms) // 2
                entry.save(update_fields=["times_used", "execution_time_ms", "last_used_at"])
                logger.debug("Learning: entrada existente atualizada (score=%.2f)", score)
            else:
                # Cria nova entrada
                AIAgentLearning.objects.create(
                    question_pattern=question,
                    detected_intent=intent,
                    generated_sql=sql,
                    execution_time_ms=execution_time_ms,
                    chart_type_used=chart_type,
                    success_rate=1.0,
                )
                logger.debug("Learning: nova entrada salva para '%s'", question[:60])
        except Exception as exc:
            logger.warning("Learning: falha ao salvar: %s", exc)

    def find_similar(
        self,
        question: str,
        intent: str = "",
    ) -> Optional[Dict]:
        """
        Busca a entrada mais similar no banco de aprendizado.

        Returns:
            dict com question_pattern, generated_sql, intent, times_used ou None
        """
        try:
            from ai_agent.models import AIAgentLearning

            qs = AIAgentLearning.objects.filter(success_rate__gte=0.5)
            if intent:
                # Prioriza mesmo intent
                qs = qs.order_by(
                    "-times_used", "-last_used_at"
                ).filter(detected_intent=intent)[:MAX_CANDIDATES] or \
                    qs.order_by("-times_used", "-last_used_at")[:MAX_CANDIDATES]
            else:
                qs = qs.order_by("-times_used", "-last_used_at")[:MAX_CANDIDATES]

            entries = list(qs)
            if not entries:
                return None

            patterns = [e.question_pattern for e in entries]
            match = find_best_match(question, patterns, threshold=SIMILARITY_THRESHOLD)

            if match is None:
                return None

            idx, score = match
            entry = entries[idx]
            logger.info(
                "Learning: match encontrado (score=%.2f) para '%s'",
                score, question[:60],
            )
            return {
                "question_pattern": entry.question_pattern,
                "generated_sql": entry.generated_sql,
                "intent": entry.detected_intent,
                "times_used": entry.times_used,
                "similarity": score,
            }
        except Exception as exc:
            logger.warning("Learning: falha na busca: %s", exc)
            return None

    def mark_failure(self, question: str) -> None:
        """Reduz success_rate de entradas similares após falha."""
        try:
            from ai_agent.models import AIAgentLearning

            entries = list(
                AIAgentLearning.objects.order_by("-last_used_at")[:MAX_CANDIDATES]
            )
            patterns = [e.question_pattern for e in entries]
            match = find_best_match(question, patterns, threshold=0.85)

            if match:
                idx, _ = match
                entry = entries[idx]
                entry.success_rate = max(0.0, entry.success_rate - 0.2)
                entry.correction_count += 1
                entry.save(update_fields=["success_rate", "correction_count"])
        except Exception as exc:
            logger.warning("Learning: falha ao marcar erro: %s", exc)

    def get_user_preferences(self, user) -> Dict:
        """Retorna preferências do usuário ou defaults."""
        defaults = {
            "preferred_date_field": "desatracacao",
            "preferred_chart_type": "bar",
            "preferred_response_style": "normal",
            "preferred_limit": 50,
        }
        if user is None:
            return defaults
        try:
            from ai_agent.models import UserAIPreferences
            prefs = UserAIPreferences.objects.get(user=user)
            return {
                "preferred_date_field": prefs.preferred_date_field or defaults["preferred_date_field"],
                "preferred_chart_type": prefs.preferred_chart_type or defaults["preferred_chart_type"],
                "preferred_response_style": prefs.preferred_response_style,
                "preferred_limit": prefs.preferred_limit,
            }
        except Exception:
            return defaults


learning_service = LearningService()
