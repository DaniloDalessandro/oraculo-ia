from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ai_agent", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIAgentLearning",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("question_pattern", models.TextField(verbose_name="Padrão da pergunta")),
                ("detected_intent", models.CharField(blank=True, max_length=100)),
                ("generated_sql", models.TextField(verbose_name="SQL gerada")),
                ("optimized_sql", models.TextField(blank=True, verbose_name="SQL otimizada")),
                ("success_rate", models.FloatField(default=1.0)),
                ("execution_time_ms", models.IntegerField(default=0)),
                ("user_feedback", models.SmallIntegerField(blank=True, null=True)),
                ("chart_type_used", models.CharField(blank=True, max_length=50)),
                ("correction_count", models.IntegerField(default=0)),
                ("times_used", models.IntegerField(default=1)),
                ("last_used_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Aprendizado do Agente",
                "verbose_name_plural": "Aprendizados do Agente",
                "ordering": ["-times_used", "-last_used_at"],
            },
        ),
        migrations.CreateModel(
            name="AIAgentFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("question", models.TextField()),
                ("generated_sql", models.TextField(blank=True)),
                ("corrected_sql", models.TextField(blank=True)),
                ("feedback", models.TextField(blank=True)),
                ("accepted", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_feedbacks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Feedback do Agente",
                "verbose_name_plural": "Feedbacks do Agente",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="UserAIPreferences",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("preferred_date_field", models.CharField(blank=True, default="data_desatracacao", max_length=100)),
                ("preferred_chart_type", models.CharField(blank=True, default="bar", max_length=50)),
                ("preferred_response_style", models.CharField(
                    choices=[("normal", "Normal"), ("resumida", "Resumida"), ("tecnica", "Técnica"), ("detalhada", "Detalhada")],
                    default="normal", max_length=20,
                )),
                ("preferred_limit", models.IntegerField(default=50)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Preferências IA do Usuário",
                "verbose_name_plural": "Preferências IA dos Usuários",
            },
        ),
    ]
