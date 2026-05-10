from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_agent", "0002_learning_feedback_preferences"),
    ]

    operations = [
        migrations.CreateModel(
            name="PortKnowledgeBase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200, verbose_name="Título")),
                ("category", models.CharField(
                    choices=[
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
                    ],
                    max_length=50,
                    verbose_name="Categoria",
                )),
                ("content", models.TextField(verbose_name="Conteúdo")),
                ("source_type", models.CharField(
                    choices=[
                        ("manual", "Cadastro Manual"),
                        ("conversa", "Aprendido em Conversa"),
                        ("documento", "Documento"),
                        ("seed", "Seed Inicial"),
                    ],
                    default="manual",
                    max_length=20,
                )),
                ("source_name", models.CharField(blank=True, max_length=200, verbose_name="Fonte")),
                ("priority", models.IntegerField(default=5)),
                ("is_active", models.BooleanField(default=True, verbose_name="Ativo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["priority", "-updated_at"], "verbose_name": "Conhecimento Portuário"},
        ),
        migrations.CreateModel(
            name="PortGlossary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("term", models.CharField(max_length=100, unique=True, verbose_name="Termo")),
                ("definition", models.TextField(verbose_name="Definição")),
                ("example", models.TextField(blank=True, verbose_name="Exemplo")),
                ("is_active", models.BooleanField(default=True, verbose_name="Ativo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["term"], "verbose_name": "Glossário Portuário"},
        ),
        migrations.CreateModel(
            name="PortBusinessRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("rule_name", models.CharField(max_length=200, verbose_name="Nome da Regra")),
                ("rule_type", models.CharField(
                    choices=[
                        ("prioridade", "Prioridade"),
                        ("restricao", "Restrição"),
                        ("preferencia", "Preferência de Berço"),
                        ("calculo", "Cálculo / Fórmula"),
                        ("procedimento", "Procedimento"),
                        ("excecao", "Exceção"),
                    ],
                    max_length=30,
                    verbose_name="Tipo",
                )),
                ("condition", models.TextField(verbose_name="Condição (quando aplicar)")),
                ("action", models.TextField(verbose_name="Ação (o que fazer)")),
                ("priority", models.IntegerField(default=5)),
                ("explanation", models.TextField(blank=True, verbose_name="Explicação adicional")),
                ("is_active", models.BooleanField(default=True, verbose_name="Ativa")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["priority", "rule_name"], "verbose_name": "Regra de Negócio Portuária"},
        ),
    ]
