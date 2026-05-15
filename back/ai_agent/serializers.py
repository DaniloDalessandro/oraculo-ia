from rest_framework import serializers
from .models import PortKnowledgeBase, PortGlossary, PortBusinessRule, Atracacao


class PortKnowledgeBaseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)

    class Meta:
        model = PortKnowledgeBase
        fields = [
            "id", "title", "category", "category_display",
            "content", "source_type", "source_type_display",
            "source_name", "priority", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PortGlossarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PortGlossary
        fields = ["id", "term", "definition", "example", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class PortBusinessRuleSerializer(serializers.ModelSerializer):
    rule_type_display = serializers.CharField(source="get_rule_type_display", read_only=True)

    class Meta:
        model = PortBusinessRule
        fields = [
            "id", "rule_name", "rule_type", "rule_type_display",
            "condition", "action", "priority", "explanation",
            "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AtracacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Atracacao
        fields = [
            "id", "operacaomodalid", "numero_atracacao", "status", "berco",
            "navio", "imo", "comprimento", "largura", "dwt", "duv", "escala",
            "bordo", "calado_entrada", "calado_saida", "navegacao", "agencia",
            "procedencia", "destino", "bandeira",
            "eta", "etb", "nor", "prontidao", "atracacao", "inicio_operacao",
            "termino_operacao", "desatracacao", "ets", "entremanobra",
            "is_improdutividade", "horas_planejadas", "prancha",
            "excludente_emap", "excludente_intemperie", "excl_emap_lm", "excl_intemperie_lm",
            "prox_atracacao", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
