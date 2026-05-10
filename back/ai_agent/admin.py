from django.contrib import admin
from .models import (
    AIAgentLog, AIAgentLearning, AIAgentFeedback, UserAIPreferences,
    PortKnowledgeBase, PortGlossary, PortBusinessRule,
)


@admin.register(AIAgentLog)
class AIAgentLogAdmin(admin.ModelAdmin):
    list_display = ("question_short", "status", "detected_intent", "execution_time_ms", "created_at")
    list_filter = ("status", "detected_intent")
    search_fields = ("question", "final_answer")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def question_short(self, obj):
        return obj.question[:80]
    question_short.short_description = "Pergunta"


@admin.register(AIAgentLearning)
class AIAgentLearningAdmin(admin.ModelAdmin):
    list_display = ("question_short", "detected_intent", "times_used", "success_rate", "user_feedback", "last_used_at")
    list_filter = ("detected_intent",)
    search_fields = ("question_pattern", "generated_sql")
    readonly_fields = ("created_at", "last_used_at")

    def question_short(self, obj):
        return obj.question_pattern[:80]
    question_short.short_description = "Padrão"


@admin.register(AIAgentFeedback)
class AIAgentFeedbackAdmin(admin.ModelAdmin):
    list_display = ("question_short", "accepted", "user", "created_at")
    list_filter = ("accepted",)
    search_fields = ("question", "feedback")
    readonly_fields = ("created_at",)

    def question_short(self, obj):
        return obj.question[:80]
    question_short.short_description = "Pergunta"


@admin.register(UserAIPreferences)
class UserAIPreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "preferred_date_field", "preferred_chart_type", "preferred_response_style", "preferred_limit")
    search_fields = ("user__username",)


# ─── Conhecimento Portuário ─────────────────────────────────────────────── #

@admin.register(PortKnowledgeBase)
class PortKnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "source_type", "priority", "is_active", "updated_at")
    list_filter = ("category", "source_type", "is_active")
    search_fields = ("title", "content")
    list_editable = ("priority", "is_active")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("priority", "-updated_at")
    fieldsets = (
        ("Identificação", {"fields": ("title", "category", "priority", "is_active")}),
        ("Conteúdo", {"fields": ("content",)}),
        ("Origem", {"fields": ("source_type", "source_name")}),
        ("Datas", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(PortGlossary)
class PortGlossaryAdmin(admin.ModelAdmin):
    list_display = ("term", "definition_short", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("term", "definition")
    list_editable = ("is_active",)
    readonly_fields = ("created_at",)

    def definition_short(self, obj):
        return obj.definition[:100]
    definition_short.short_description = "Definição"


@admin.register(PortBusinessRule)
class PortBusinessRuleAdmin(admin.ModelAdmin):
    list_display = ("rule_name", "rule_type", "priority", "is_active", "created_at")
    list_filter = ("rule_type", "is_active")
    search_fields = ("rule_name", "condition", "action", "explanation")
    list_editable = ("priority", "is_active")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Identificação", {"fields": ("rule_name", "rule_type", "priority", "is_active")}),
        ("Regra", {"fields": ("condition", "action")}),
        ("Contexto", {"fields": ("explanation",)}),
        ("Datas", {"fields": ("created_at",), "classes": ("collapse",)}),
    )
