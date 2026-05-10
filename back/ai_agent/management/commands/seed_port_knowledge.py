"""
Seed inicial do conhecimento portuário.

Uso:
    python manage.py seed_port_knowledge
    python manage.py seed_port_knowledge --clear   # limpa e recria
"""
from django.core.management.base import BaseCommand


GLOSSARY = [
    ("PLR", "Prancha Líquida Real — produtividade efetiva da operação, medida em toneladas por hora (ou por dia), descontados todos os tempos não operacionais.", "PLR de 1.200 t/h significa que foram movimentadas 1.200 toneladas por hora efetivamente trabalhada."),
    ("PBM", "Prancha Bruta Média — produtividade total calculada sobre o tempo total de berço (incluindo esperas e paralisações).", ""),
    ("DWT", "Deadweight Tonnage — capacidade máxima de carga de um navio em toneladas métricas, incluindo carga, combustível, água e tripulação.", "Um navio de 80.000 DWT pode carregar até 80.000 toneladas."),
    ("LOA", "Length Overall — comprimento total do navio, da proa à popa.", "Para calcular a ocupação de berço: LOA + 15m na proa + 15m na popa."),
    ("Boca", "Largura máxima do navio no ponto mais largo do casco.", "Um navio com boca de 32m não pode atracar em berço com restrição de 30m."),
    ("Calado", "Distância vertical entre a linha d'água e a parte mais baixa do casco. Determina a profundidade mínima necessária no berço.", "Calado de 12m exige profundidade mínima de 12,5m com folga de segurança."),
    ("NOR", "Notice of Readiness — aviso formal emitido pelo comandante do navio declarando que o navio está pronto para iniciar as operações de carga/descarga.", ""),
    ("ETA", "Estimated Time of Arrival — hora estimada de chegada do navio ao porto.", ""),
    ("ETB", "Estimated Time of Berthing — hora estimada de atracação do navio no berço.", ""),
    ("ETS", "Estimated Time of Sailing — hora estimada de partida do navio do berço.", ""),
    ("Atracação", "Procedimento de amarração do navio ao berço para início das operações portuárias.", ""),
    ("Desatracação", "Procedimento de desamarração do navio do berço para saída do porto.", ""),
    ("Shifting", "Movimentação de um navio de um berço para outro dentro do mesmo porto.", "O shifting ocorre quando um berço mais adequado fica disponível ou por necessidade operacional."),
    ("By-pass", "Situação em que um navio passa à frente de outro na fila de espera por critério de prioridade operacional ou contratual.", ""),
    ("STS", "Ship-to-Ship — operação de transferência de carga diretamente entre dois navios, geralmente realizada em fundeadouro.", ""),
    ("Berço", "Posição numerada no cais onde o navio é amarrado para realizar operações portuárias. Cada berço tem restrições de LOA, calado e tipo de carga.", ""),
    ("Prancha", "Taxa de produtividade da operação portuária. Pode ser expressa em t/h (toneladas por hora) ou t/dia.", ""),
    ("Janela Operacional", "Período de tempo reservado para um navio operar num berço específico, definido em contrato ou por programação portuária.", ""),
    ("Fila de Navios", "Lista ordenada de navios aguardando berço disponível, geralmente ordenada por ETA ou prioridade contratual.", ""),
    ("Fundeadouro", "Área aquática fora do cais onde os navios ancoram para aguardar o berço disponível.", ""),
    ("TUP", "Terminal de Uso Privado — terminal portuário operado por empresa privada para cargas próprias ou de terceiros.", ""),
    ("Modal", "Tipo de transporte terrestre ligado ao porto (ferroviário, rodoviário, dutoviário).", ""),
    ("Granel Sólido", "Carga a granel não líquida transportada sem embalagem, como minério, grão, fertilizante e carvão.", ""),
    ("Granel Líquido", "Carga líquida transportada em tanques, como petróleo, combustível, óleos vegetais e produtos químicos.", ""),
    ("Carga Geral", "Carga acondicionada em volumes, caixas, fardos ou paletes, transportada sem contêiner.", ""),
    ("Demurrage", "Multa cobrada ao armador ou ao terminal quando o navio permanece no berço além do tempo contratualmente previsto.", ""),
    ("Despacho", "Bônus pago quando a operação é concluída antes do tempo previsto em contrato.", ""),
    ("Tempo de Berço", "Período total em que o navio permanece atracado, desde a atracação até a desatracação.", ""),
    ("Tempo Operacional", "Parte do tempo de berço efetivamente utilizada em operações de carga/descarga.", ""),
    ("Paralização", "Interrupção da operação por motivos como chuva, maré, manutenção de equipamento ou aguardo de recurso.", ""),
]

KNOWLEDGE = [
    {
        "title": "Data de referência padrão para análises históricas",
        "category": "indicador",
        "content": (
            "Para análises históricas mensais e anuais, utilizar a data de desatracação como data de referência padrão, "
            "pois representa quando a operação foi concluída. Usar data de atracação somente quando o usuário solicitar explicitamente."
        ),
        "priority": 1,
    },
    {
        "title": "Cálculo de ocupação de berço (Regra LOA)",
        "category": "regra_de_atracacao",
        "content": (
            "Para calcular a ocupação efetiva de um berço, usar: comprimento do navio (LOA) + 15 metros de folga na proa + 15 metros de folga na popa. "
            "Total: LOA + 30 metros. Nenhum outro navio pode ser alocado nesse espaço simultaneamente."
        ),
        "priority": 1,
    },
    {
        "title": "Conceito de PLR — como calcular",
        "category": "indicador",
        "content": (
            "PLR (Prancha Líquida Real) = Quantidade movimentada (t) ÷ Tempo operacional efetivo (h). "
            "O tempo operacional exclui: paralisações climáticas, aguardo de rebocador, manutenção corretiva, "
            "aguardo de autorização e outros tempos não imputáveis ao terminal."
        ),
        "priority": 2,
    },
    {
        "title": "Conceito de PBM — como calcular",
        "category": "indicador",
        "content": (
            "PBM (Prancha Bruta Média) = Quantidade movimentada (t) ÷ Tempo total de berço (h). "
            "Inclui todos os tempos, operacionais ou não. PBM < PLR sempre."
        ),
        "priority": 2,
    },
    {
        "title": "Critério de prioridade na fila de navios",
        "category": "prioridade",
        "content": (
            "A ordem padrão de prioridade para atracação é: "
            "1. Contratos com janela operacional definida e garantida; "
            "2. Navios com cargas perecíveis ou operações de emergência; "
            "3. Navios com menor ETA (chegada mais antiga); "
            "4. Critério de by-pass somente com autorização da gerência portuária."
        ),
        "priority": 2,
    },
    {
        "title": "Shifting — quando realizar",
        "category": "procedimento",
        "content": (
            "O shifting (mudança de berço) deve ser realizado quando: "
            "1. O berço original não atende às restrições de calado ou LOA do navio; "
            "2. Um berço mais adequado fica disponível e o contrato prevê essa possibilidade; "
            "3. Há conflito de prioridade com outro navio de maior precedência. "
            "O tempo de shifting não é contabilizado como tempo operacional."
        ),
        "priority": 3,
    },
    {
        "title": "NOR — Notice of Readiness",
        "category": "procedimento",
        "content": (
            "O NOR deve ser emitido pelo comandante quando o navio estiver ancorado ou atracado e "
            "todas as porões/tanques estiverem prontos para operação. "
            "O tempo de stallia começa a contar após a aceitação do NOR pelo terminal. "
            "NOR inválido não inicia contagem de tempo."
        ),
        "priority": 3,
    },
    {
        "title": "Restrições de calado por berço",
        "category": "regra_de_berco",
        "content": (
            "Cada berço possui profundidade máxima autorizada. "
            "Ao consultar disponibilidade de berço, verificar sempre se o calado do navio é compatível "
            "com a profundidade do berço na preamar e na baixamar. "
            "A folga de segurança padrão é de 0,5m entre o calado do navio e o fundo."
        ),
        "priority": 2,
    },
    {
        "title": "By-pass — critérios de aplicação",
        "category": "excecao",
        "content": (
            "O by-pass é a ultrapassagem de um navio na fila operacional. "
            "Pode ser aplicado quando: o navio seguinte tem carga perecível, há contrato de janela garantida, "
            "ou por decisão gerencial documentada. "
            "O by-pass deve ser registrado com justificativa formal para fins de auditoria."
        ),
        "priority": 3,
    },
    {
        "title": "Operação STS (Ship-to-Ship)",
        "category": "conceito_operacional",
        "content": (
            "Operações STS ocorrem fora do cais, geralmente no fundeadouro. "
            "Exigem autorização da ANTAQ e da Capitania dos Portos. "
            "O tempo de STS não compõe o tempo de berço. "
            "A produtividade é medida separadamente da operação em cais."
        ),
        "priority": 4,
    },
]

BUSINESS_RULES = [
    {
        "rule_name": "Validação de janela de berço",
        "rule_type": "restricao",
        "condition": "Navio com janela operacional contratual definida",
        "action": "Garantir disponibilidade do berço no período da janela, independente de outros navios na fila",
        "priority": 1,
        "explanation": "Janelas contratuais têm precedência sobre a fila FIFO padrão.",
    },
    {
        "rule_name": "Calado máximo por berço",
        "rule_type": "restricao",
        "condition": "Calado do navio ≥ profundidade do berço − 0,5m (folga de segurança)",
        "action": "Proibir atracação. Sugerir berço alternativo com profundidade adequada.",
        "priority": 1,
        "explanation": "Regra de segurança náutica. Não pode ser dispensada.",
    },
    {
        "rule_name": "LOA máximo por berço",
        "rule_type": "restricao",
        "condition": "LOA do navio + 30m > comprimento útil do berço",
        "action": "Proibir atracação no berço. Verificar berços adjacentes ou de maior comprimento.",
        "priority": 1,
        "explanation": "Os 30m correspondem a 15m de folga na proa + 15m na popa.",
    },
    {
        "rule_name": "Ordem FIFO na fila de navios",
        "rule_type": "procedimento",
        "condition": "Ausência de contrato de janela ou prioridade especial",
        "action": "Respeitar ordem de chegada (menor ETA primeiro) para alocação de berços",
        "priority": 2,
        "explanation": "Regra padrão quando não há contratos de prioridade.",
    },
    {
        "rule_name": "Despacho e demurrage",
        "rule_type": "calculo",
        "condition": "Operação conclui antes (despacho) ou depois (demurrage) do laytime contratual",
        "action": "Calcular despacho ou demurrage em horas × taxa contratual por hora",
        "priority": 3,
        "explanation": "Laytime = tempo contratual para operação. Demurrage penaliza atrasos, despacho recompensa agilidade.",
    },
]


class Command(BaseCommand):
    help = "Popula a base de conhecimento portuário com dados iniciais (seed)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove todos os registros seed antes de recriar.",
        )

    def handle(self, *args, **options):
        from ai_agent.models import PortGlossary, PortKnowledgeBase, PortBusinessRule

        if options["clear"]:
            PortGlossary.objects.filter(is_active=True).delete()
            PortKnowledgeBase.objects.filter(source_type="seed").delete()
            PortBusinessRule.objects.all().delete()
            self.stdout.write(self.style.WARNING("Registros seed removidos."))

        # ── Glossário ─────────────────────────────────────────────────────
        g_created = 0
        for term, definition, example in GLOSSARY:
            _, created = PortGlossary.objects.get_or_create(
                term=term,
                defaults={"definition": definition, "example": example},
            )
            if created:
                g_created += 1
        self.stdout.write(self.style.SUCCESS(f"Glossário: {g_created} termos criados."))

        # ── Base de conhecimento ──────────────────────────────────────────
        k_created = 0
        for entry in KNOWLEDGE:
            _, created = PortKnowledgeBase.objects.get_or_create(
                title=entry["title"],
                defaults={
                    "category": entry["category"],
                    "content": entry["content"],
                    "priority": entry["priority"],
                    "source_type": "seed",
                },
            )
            if created:
                k_created += 1
        self.stdout.write(self.style.SUCCESS(f"Conhecimento: {k_created} entradas criadas."))

        # ── Regras de negócio ─────────────────────────────────────────────
        r_created = 0
        for rule in BUSINESS_RULES:
            _, created = PortBusinessRule.objects.get_or_create(
                rule_name=rule["rule_name"],
                defaults={
                    "rule_type": rule["rule_type"],
                    "condition": rule["condition"],
                    "action": rule["action"],
                    "priority": rule["priority"],
                    "explanation": rule.get("explanation", ""),
                },
            )
            if created:
                r_created += 1
        self.stdout.write(self.style.SUCCESS(f"Regras de negócio: {r_created} criadas."))
        self.stdout.write(self.style.SUCCESS("Seed concluído."))
