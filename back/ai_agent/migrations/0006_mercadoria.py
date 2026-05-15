from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_agent', '0005_atracacao'),
    ]

    operations = [
        migrations.CreateModel(
            name='Mercadoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mercadoria_id', models.BigIntegerField(unique=True, verbose_name='ID Mercadoria')),
                ('atracacao_id', models.BigIntegerField(blank=True, null=True, verbose_name='ID Atracação (operacaomodalid)')),
                ('nome', models.CharField(blank=True, max_length=255, null=True, verbose_name='Nome')),
                ('gm', models.CharField(blank=True, max_length=255, null=True, verbose_name='Grupo de Mercadoria')),
                ('natureza_tipo', models.CharField(blank=True, max_length=150, null=True, verbose_name='Natureza Tipo')),
                ('natureza_subtipo', models.CharField(blank=True, max_length=150, null=True, verbose_name='Natureza Subtipo')),
                ('operacao', models.CharField(blank=True, max_length=100, null=True, verbose_name='Operação')),
                ('sentido', models.CharField(blank=True, max_length=100, null=True, verbose_name='Sentido')),
                ('operador', models.CharField(blank=True, max_length=255, null=True, verbose_name='Operador')),
                ('cliente', models.CharField(blank=True, max_length=255, null=True, verbose_name='Cliente')),
                ('pbm', models.DecimalField(blank=True, decimal_places=3, max_digits=16, null=True, verbose_name='PBM')),
                ('plr', models.DecimalField(blank=True, decimal_places=3, max_digits=16, null=True, verbose_name='PLR')),
                ('qtdm', models.DecimalField(blank=True, decimal_places=3, max_digits=16, null=True, verbose_name='QTDM')),
                ('qtdr', models.DecimalField(blank=True, decimal_places=3, max_digits=16, null=True, verbose_name='QTDR')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Mercadoria',
                'verbose_name_plural': 'Mercadorias',
                'db_table': 'mercadorias',
                'ordering': ['mercadoria_id'],
            },
        ),
    ]
