from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class AIAgentLog(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_PARTIAL = "partial"
    STATUS_AMBIGUOUS = "ambiguous"

    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Sucesso"),
        (STATUS_ERROR, "Erro"),
        (STATUS_PARTIAL, "Parcial"),
        (STATUS_AMBIGUOUS, "Ambíguo"),
    ]

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_agent_logs",
    )
    question = models.TextField(verbose_name="Pergunta")
    detected_intent = models.CharField(
        max_length=100, blank=True, verbose_name="Intenção detectada"
    )
    generated_sql = models.TextField(blank=True, verbose_name="SQL gerada")
    validation_sql = models.TextField(
        blank=True, verbose_name="SQL de validação cruzada"
    )
    sql_result_preview = models.TextField(
        blank=True, verbose_name="Preview do resultado"
    )
    final_answer = models.TextField(blank=True, verbose_name="Resposta final")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SUCCESS,
        verbose_name="Status",
    )
    error_message = models.TextField(blank=True, verbose_name="Mensagem de erro")
    execution_time_ms = models.IntegerField(
        default=0, verbose_name="Tempo de execução (ms)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Log do Agente IA"
        verbose_name_plural = "Logs do Agente IA"

    def __str__(self):
        return f"[{self.status.upper()}] {self.question[:60]}"


class AIAgentLearning(models.Model):
    """Padrões aprendidos de consultas bem-sucedidas."""

    question_pattern = models.TextField(verbose_name="Padrão da pergunta")
    detected_intent = models.CharField(max_length=100, blank=True)
    generated_sql = models.TextField(verbose_name="SQL gerada")
    optimized_sql = models.TextField(blank=True, verbose_name="SQL otimizada")
    success_rate = models.FloatField(default=1.0)
    execution_time_ms = models.IntegerField(default=0)
    user_feedback = models.SmallIntegerField(null=True, blank=True)  # 1=bom, -1=ruim
    chart_type_used = models.CharField(max_length=50, blank=True)
    correction_count = models.IntegerField(default=0)
    times_used = models.IntegerField(default=1)
    last_used_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-times_used", "-last_used_at"]
        verbose_name = "Aprendizado do Agente"
        verbose_name_plural = "Aprendizados do Agente"

    def __str__(self):
        return f"{self.question_pattern[:60]} (usado {self.times_used}x)"


class AIAgentFeedback(models.Model):
    """Feedbacks e correções dos usuários."""

    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ai_feedbacks",
    )
    question = models.TextField()
    generated_sql = models.TextField(blank=True)
    corrected_sql = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    accepted = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Feedback do Agente"
        verbose_name_plural = "Feedbacks do Agente"

    def __str__(self):
        flag = "✓" if self.accepted else "✗"
        return f"{flag} {self.question[:60]}"


class PortKnowledgeBase(models.Model):
    """Base de conhecimento portuário: regras, procedimentos e contexto operacional."""

    CATEGORY_CHOICES = [
        ("regra_de_atracacao", "Regra de Atracação"),
        ("conceito_operacional", "Conceito Operacional"),
        ("regra_de_berco", "Regra de Berço"),
        ("regra_de_carga", "Regra de Carga"),
        ("prioridade", "Prioridade"),
        ("excecao", "Exceção"),
        ("glossario", "Glossário"),
        ("procedimento", "Procedimento"),
        ("indicador", "Indicador"),
        ("aprendido", "Aprendido em Conversa"),
    ]
    SOURCE_CHOICES = [
        ("manual", "Cadastro Manual"),
        ("conversa", "Aprendido em Conversa"),
        ("documento", "Documento"),
        ("seed", "Seed Inicial"),
    ]

    title = models.CharField(max_length=200, verbose_name="Título")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name="Categoria")
    content = models.TextField(verbose_name="Conteúdo")
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    source_name = models.CharField(max_length=200, blank=True, verbose_name="Fonte")
    priority = models.IntegerField(default=5, help_text="1 = maior prioridade, 10 = menor")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "-updated_at"]
        verbose_name = "Conhecimento Portuário"
        verbose_name_plural = "Base de Conhecimento Portuário"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class PortGlossary(models.Model):
    """Glossário de termos técnicos portuários."""

    term = models.CharField(max_length=100, unique=True, verbose_name="Termo")
    definition = models.TextField(verbose_name="Definição")
    example = models.TextField(blank=True, verbose_name="Exemplo")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["term"]
        verbose_name = "Glossário Portuário"
        verbose_name_plural = "Glossário Portuário"

    def __str__(self):
        return self.term


class PortBusinessRule(models.Model):
    """Regras de negócio operacionais do porto."""

    RULE_TYPE_CHOICES = [
        ("prioridade", "Prioridade"),
        ("restricao", "Restrição"),
        ("preferencia", "Preferência de Berço"),
        ("calculo", "Cálculo / Fórmula"),
        ("procedimento", "Procedimento"),
        ("excecao", "Exceção"),
    ]

    rule_name = models.CharField(max_length=200, verbose_name="Nome da Regra")
    rule_type = models.CharField(max_length=30, choices=RULE_TYPE_CHOICES, verbose_name="Tipo")
    condition = models.TextField(verbose_name="Condição (quando aplicar)")
    action = models.TextField(verbose_name="Ação (o que fazer)")
    priority = models.IntegerField(default=5, help_text="1 = maior prioridade")
    explanation = models.TextField(blank=True, verbose_name="Explicação adicional")
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["priority", "rule_name"]
        verbose_name = "Regra de Negócio Portuária"
        verbose_name_plural = "Regras de Negócio Portuárias"

    def __str__(self):
        return f"[{self.get_rule_type_display()}] {self.rule_name}"


class UserAIPreferences(models.Model):
    """Preferências de cada usuário para o agente."""

    STYLE_CHOICES = [
        ("normal", "Normal"),
        ("resumida", "Resumida"),
        ("tecnica", "Técnica"),
        ("detalhada", "Detalhada"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="ai_preferences",
    )
    preferred_date_field = models.CharField(
        max_length=100, blank=True,
        default="desatracacao",
        help_text="Campo de data preferido para filtros temporais",
    )
    preferred_chart_type = models.CharField(max_length=50, blank=True, default="bar")
    preferred_response_style = models.CharField(
        max_length=20, choices=STYLE_CHOICES, default="normal",
    )
    preferred_limit = models.IntegerField(default=50)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferências IA do Usuário"
        verbose_name_plural = "Preferências IA dos Usuários"

    def __str__(self):
        return f"Preferências de {self.user}"
