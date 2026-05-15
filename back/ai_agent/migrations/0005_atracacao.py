from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_agent', '0004_alter_portbusinessrule_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Atracacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operacaomodalid', models.BigIntegerField(unique=True, verbose_name='ID Operação Modal')),
                ('numero_atracacao', models.IntegerField(blank=True, null=True, verbose_name='Número Atracação')),
                ('status', models.CharField(blank=True, max_length=50, null=True, verbose_name='Status')),
                ('berco', models.CharField(blank=True, max_length=100, null=True, verbose_name='Berço')),
                ('navio', models.CharField(blank=True, max_length=255, null=True, verbose_name='Navio')),
                ('imo', models.CharField(blank=True, max_length=20, null=True, verbose_name='IMO')),
                ('comprimento', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Comprimento (m)')),
                ('largura', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Largura (m)')),
                ('dwt', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name='DWT')),
                ('duv', models.CharField(blank=True, max_length=100, null=True, verbose_name='DUV')),
                ('escala', models.CharField(blank=True, max_length=100, null=True, verbose_name='Escala')),
                ('bordo', models.CharField(blank=True, max_length=50, null=True, verbose_name='Bordo')),
                ('calado_entrada', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Calado Entrada (m)')),
                ('calado_saida', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Calado Saída (m)')),
                ('navegacao', models.CharField(blank=True, max_length=100, null=True, verbose_name='Navegação')),
                ('agencia', models.CharField(blank=True, max_length=255, null=True, verbose_name='Agência')),
                ('procedencia', models.CharField(blank=True, max_length=255, null=True, verbose_name='Procedência')),
                ('destino', models.CharField(blank=True, max_length=255, null=True, verbose_name='Destino')),
                ('bandeira', models.CharField(blank=True, max_length=100, null=True, verbose_name='Bandeira')),
                ('eta', models.DateTimeField(blank=True, null=True, verbose_name='ETA')),
                ('etb', models.DateTimeField(blank=True, null=True, verbose_name='ETB')),
                ('nor', models.DateTimeField(blank=True, null=True, verbose_name='NOR')),
                ('prontidao', models.DateTimeField(blank=True, null=True, verbose_name='Prontidão')),
                ('atracacao', models.DateTimeField(blank=True, null=True, verbose_name='Atracação')),
                ('inicio_operacao', models.DateTimeField(blank=True, null=True, verbose_name='Início Operação')),
                ('termino_operacao', models.DateTimeField(blank=True, null=True, verbose_name='Término Operação')),
                ('desatracacao', models.DateTimeField(blank=True, null=True, verbose_name='Desatracação')),
                ('ets', models.DateTimeField(blank=True, null=True, verbose_name='ETS')),
                ('entremanobra', models.DateTimeField(blank=True, null=True, verbose_name='Entre Manobra')),
                ('is_improdutividade', models.BooleanField(blank=True, null=True, verbose_name='É Improdutividade')),
                ('horas_planejadas', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Horas Planejadas')),
                ('prancha', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Prancha')),
                ('excludente_emap', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Excludente EMAP')),
                ('excludente_intemperie', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Excludente Intempérie')),
                ('excl_emap_lm', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Excl. EMAP LM')),
                ('excl_intemperie_lm', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Excl. Intempérie LM')),
                ('prox_atracacao', models.DateTimeField(blank=True, null=True, verbose_name='Próxima Atracação')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Atracação',
                'verbose_name_plural': 'Atracações',
                'db_table': 'atracacoes',
                'ordering': ['operacaomodalid'],
            },
        ),
    ]
