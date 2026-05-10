RESULT_VALIDATION_PROMPT = """
Você é um validador de resultados de análise de dados.

PERGUNTA ORIGINAL: {question}
INTENÇÃO: {intent}
SQL EXECUTADO: {sql}
RESULTADO (primeiras linhas): {result_preview}
TOTAL DE LINHAS: {row_count}
RESULTADO TRUNCADO: {truncated}

Analise se o resultado responde corretamente à pergunta. Responda em JSON com o formato exato:

{{
  "is_valid": true ou false,
  "issues": ["lista de problemas encontrados, vazia se nenhum"],
  "warnings": ["avisos importantes, como dados ausentes ou truncamento"],
  "confidence": "high|medium|low",
  "suggestion": "sugestão de melhoria na consulta, se necessário"
}}

Verifique especialmente:
- O resultado está vazio quando não deveria estar?
- Há duplicidade óbvia causada por JOIN?
- As agregações fazem sentido para a pergunta?
- Filtros de data/mês/ano foram aplicados corretamente?
- A contagem usa DISTINCT quando necessário?
- O resultado está truncado e isso afeta a resposta?
"""

CROSS_CHECK_VALIDATION_PROMPT = """
Compare os dois resultados de SQL abaixo e determine se são consistentes.

PERGUNTA: {question}

RESULTADO PRINCIPAL:
{main_result}

RESULTADO DE VERIFICAÇÃO:
{check_result}

CRITÉRIOS PARA DIVERGÊNCIA REAL (seja conservador — falsos positivos são prejudiciais):
- Diferença nos totais/somas ACIMA de 15%: divergência real
- Diferença entre 5% e 15%: consistente, mas registrar como aviso
- Diferença ABAIXO de 5%: normal (arredondamento, precisão decimal) — consistent=true
- Mesmo número de linhas com mesma tendência e ordem de grandeza: consistent=true
- Estruturas diferentes mas mesma conclusão geral: consistent=true
- Se a comparação é impossível (estruturas incompatíveis): consistent=true, divergence_detected=false

NÃO considere divergência:
- Diferenças metodológicas esperadas
- Pequenas variações de arredondamento
- Mesmos dados em formatos ligeiramente diferentes

Responda em JSON:
{{
  "consistent": true ou false,
  "divergence_detected": true ou false,
  "divergence_pct": número estimado da diferença percentual (0 se não aplicável),
  "divergence_description": "descrição objetiva apenas se divergence_detected=true, senão string vazia",
  "recommended_result": "main|check|ambiguous",
  "explanation": "explicação técnica em uma frase"
}}
"""
