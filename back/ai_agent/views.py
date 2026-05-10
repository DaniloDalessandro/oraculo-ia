"""
Views do Agente IA

Endpoint principal: POST /ai-agent/ask/
"""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_agent.services.agent_service import run_agent
from ai_agent.logs.logger import log_error
from ai_agent.models import AIAgentFeedback

logger = logging.getLogger("ai_agent")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ask(request):
    """
    POST /ai-agent/ask/

    Body:
        { "question": "Qual foi o total de PLR por mês em 2025?" }

    Response:
        {
            "answer": "...",
            "intent": "...",
            "sql": "...",
            "validation_sql": "...",
            "filters": {...},
            "status": "success"
        }
    """
    question = request.data.get("question", "").strip()
    conversation_history = request.data.get("conversation_history", [])

    if not question:
        return Response(
            {"error": "O campo 'question' é obrigatório."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(question) > 2000:
        return Response(
            {"error": "A pergunta não pode ter mais de 2000 caracteres."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validar e limitar histórico
    if not isinstance(conversation_history, list):
        conversation_history = []
    conversation_history = conversation_history[-20:]  # máximo 20 mensagens

    try:
        result = run_agent(
            question=question,
            user=request.user,
            conversation_history=conversation_history,
        )
        return Response(result, status=status.HTTP_200_OK)

    except Exception as exc:
        log_error("Erro inesperado na view /ask", exc, {"question": question})
        return Response(
            {
                "error": "Erro interno ao processar a pergunta. Tente novamente.",
                "status": "error",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refresh_schema(request):
    """
    POST /ai-agent/refresh-schema/

    Força a re-leitura do schema do banco (invalida o cache).
    Útil após mudanças na estrutura do banco.
    """
    try:
        from ai_agent.services.schema_service import schema_service
        from ai_agent.tools.cache_lookup_tool import invalidate_profile
        schema_service.invalidate_cache()
        invalidate_profile()
        schema = schema_service.introspect(force_refresh=True)
        return Response(
            {
                "message": "Schema e perfil do banco atualizados com sucesso.",
                "tables": list(schema.keys()),
                "table_count": len(schema),
            }
        )
    except Exception as exc:
        log_error("Erro ao atualizar schema", exc)
        return Response(
            {"error": "Erro ao atualizar o schema."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def feedback(request):
    """
    POST /ai-agent/feedback/

    Body:
        {
            "question": "...",
            "generated_sql": "...",
            "accepted": true | false,
            "feedback": "texto opcional"
        }
    """
    question = request.data.get("question", "").strip()
    if not question:
        return Response(
            {"error": "O campo 'question' é obrigatório."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    accepted = bool(request.data.get("accepted", True))
    generated_sql = request.data.get("generated_sql", "").strip()
    feedback_text = request.data.get("feedback", "").strip()

    AIAgentFeedback.objects.create(
        user=request.user,
        question=question,
        generated_sql=generated_sql,
        accepted=accepted,
        feedback=feedback_text,
    )

    if not accepted:
        try:
            from ai_agent.services.learning_service import learning_service
            learning_service.mark_failure(question)
        except Exception as exc:
            logger.warning("Feedback: falha ao penalizar learning: %s", exc)
    else:
        try:
            from ai_agent.models import AIAgentLearning
            from ai_agent.services.semantic_search_service import find_best_match
            entries = list(AIAgentLearning.objects.order_by("-last_used_at")[:100])
            patterns = [e.question_pattern for e in entries]
            match = find_best_match(question, patterns, threshold=0.80)
            if match:
                idx, _ = match
                entry = entries[idx]
                entry.user_feedback = 1
                entry.success_rate = min(1.0, entry.success_rate + 0.1)
                entry.save(update_fields=["user_feedback", "success_rate"])
        except Exception as exc:
            logger.warning("Feedback: falha ao reforçar learning: %s", exc)

    logger.info("Feedback %s registrado para: %s", "positivo" if accepted else "negativo", question[:60])
    return Response({"ok": True}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def schema_info(request):
    """
    GET /ai-agent/schema/

    Retorna o schema atual do banco (para debug e documentação).
    """
    try:
        from ai_agent.services.schema_service import schema_service
        schema = schema_service.introspect()
        return Response(
            {
                "tables": list(schema.keys()),
                "table_count": len(schema),
                "schema_summary": schema_service.get_text_summary(schema),
            }
        )
    except Exception as exc:
        log_error("Erro ao ler schema", exc)
        return Response(
            {"error": "Erro ao ler o schema."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def table_data(request):
    """
    GET /ai-agent/table-data/?table=<name>&page=<n>&page_size=<n>&search=<q>

    Retorna as linhas de uma tabela com paginação e busca textual.
    """
    from ai_agent.services.schema_service import schema_service
    from django.db import connection

    table_name = request.query_params.get("table", "").strip()
    if not table_name:
        return Response({"error": "Parâmetro 'table' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

    # Valida se a tabela existe no schema (evita SQL injection)
    schema = schema_service.introspect()
    if table_name not in schema:
        return Response({"error": "Tabela não encontrada."}, status=status.HTTP_404_NOT_FOUND)

    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1
    try:
        page_size = min(100, max(1, int(request.query_params.get("page_size", 50))))
    except ValueError:
        page_size = 50

    search = request.query_params.get("search", "").strip()
    offset = (page - 1) * page_size

    try:
        with connection.cursor() as cursor:
            # Total de linhas
            if search:
                text_cols = schema[table_name].get("text_columns", [])
                if text_cols:
                    where_parts = " OR ".join(
                        f'CAST("{col}" AS TEXT) ILIKE %s' for col in text_cols[:5]
                    )
                    params_count = [f"%{search}%"] * min(5, len(text_cols))
                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE {where_parts}', params_count)
                else:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                    search = ""  # sem colunas de texto, ignora busca
            else:
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')

            total = cursor.fetchone()[0]

            # Dados paginados
            if search:
                text_cols = schema[table_name].get("text_columns", [])[:5]
                where_parts = " OR ".join(f'CAST("{col}" AS TEXT) ILIKE %s' for col in text_cols)
                params_data = [f"%{search}%"] * len(text_cols)
                cursor.execute(
                    f'SELECT * FROM "{table_name}" WHERE {where_parts} LIMIT %s OFFSET %s',
                    params_data + [page_size, offset],
                )
            else:
                cursor.execute(f'SELECT * FROM "{table_name}" LIMIT %s OFFSET %s', [page_size, offset])

            columns = [desc[0] for desc in cursor.description]
            rows = []
            for row in cursor.fetchall():
                rows.append({col: (str(val) if val is not None else None) for col, val in zip(columns, row)})

        return Response({
            "columns": columns,
            "rows": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),
        })
    except Exception as exc:
        log_error("Erro ao ler dados da tabela", exc)
        return Response({"error": f"Erro ao ler tabela: {str(exc)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def schema_detail(request):
    """
    GET /ai-agent/schema/detail/

    Retorna o schema completo com colunas, tipos e metadados por tabela.
    """
    try:
        from ai_agent.services.schema_service import schema_service
        schema = schema_service.introspect()

        tables = []
        for table_name, info in schema.items():
            tables.append({
                "name": table_name,
                "columns": info.get("columns", []),
                "primary_keys": info.get("primary_keys", []),
                "foreign_keys": info.get("foreign_keys", {}),
                "indexes": info.get("indexes", []),
                "date_columns": info.get("date_columns", []),
                "numeric_columns": info.get("numeric_columns", []),
                "text_columns": info.get("text_columns", []),
            })

        return Response({"tables": tables, "table_count": len(tables)})
    except Exception as exc:
        log_error("Erro ao ler schema detalhado", exc)
        return Response(
            {"error": "Erro ao ler o schema."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ─── Knowledge Base CRUD ──────────────────────────────────────────────────────

from ai_agent.models import PortKnowledgeBase, PortGlossary, PortBusinessRule
from ai_agent.serializers import (
    PortKnowledgeBaseSerializer,
    PortGlossarySerializer,
    PortBusinessRuleSerializer,
)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def knowledge_list(request):
    if request.method == "GET":
        qs = PortKnowledgeBase.objects.all()
        category = request.query_params.get("category")
        active = request.query_params.get("active")
        if category:
            qs = qs.filter(category=category)
        if active is not None:
            qs = qs.filter(is_active=active.lower() == "true")
        return Response(PortKnowledgeBaseSerializer(qs, many=True).data)

    serializer = PortKnowledgeBaseSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def knowledge_detail(request, pk):
    try:
        obj = PortKnowledgeBase.objects.get(pk=pk)
    except PortKnowledgeBase.DoesNotExist:
        return Response({"error": "Não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(PortKnowledgeBaseSerializer(obj).data)
    if request.method == "DELETE":
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = PortKnowledgeBaseSerializer(obj, data=request.data, partial=request.method == "PATCH")
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def glossary_list(request):
    if request.method == "GET":
        qs = PortGlossary.objects.all()
        active = request.query_params.get("active")
        if active is not None:
            qs = qs.filter(is_active=active.lower() == "true")
        return Response(PortGlossarySerializer(qs, many=True).data)

    serializer = PortGlossarySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def glossary_detail(request, pk):
    try:
        obj = PortGlossary.objects.get(pk=pk)
    except PortGlossary.DoesNotExist:
        return Response({"error": "Não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(PortGlossarySerializer(obj).data)
    if request.method == "DELETE":
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = PortGlossarySerializer(obj, data=request.data, partial=request.method == "PATCH")
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def rules_list(request):
    if request.method == "GET":
        qs = PortBusinessRule.objects.all()
        rule_type = request.query_params.get("rule_type")
        active = request.query_params.get("active")
        if rule_type:
            qs = qs.filter(rule_type=rule_type)
        if active is not None:
            qs = qs.filter(is_active=active.lower() == "true")
        return Response(PortBusinessRuleSerializer(qs, many=True).data)

    serializer = PortBusinessRuleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def rules_detail(request, pk):
    try:
        obj = PortBusinessRule.objects.get(pk=pk)
    except PortBusinessRule.DoesNotExist:
        return Response({"error": "Não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(PortBusinessRuleSerializer(obj).data)
    if request.method == "DELETE":
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = PortBusinessRuleSerializer(obj, data=request.data, partial=request.method == "PATCH")
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def knowledge_meta(request):
    """Retorna as opções de choices para os formulários do frontend."""
    return Response({
        "knowledge_categories": [
            {"value": k, "label": v}
            for k, v in PortKnowledgeBase.CATEGORY_CHOICES
        ],
        "knowledge_sources": [
            {"value": k, "label": v}
            for k, v in PortKnowledgeBase.SOURCE_CHOICES
        ],
        "rule_types": [
            {"value": k, "label": v}
            for k, v in PortBusinessRule.RULE_TYPE_CHOICES
        ],
    })
