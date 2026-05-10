SQL_GENERATION_PROMPT = """
Voce e um especialista em SQL PostgreSQL para sistemas portuarios.

SCHEMA DO BANCO:
{schema}

PERFIL DO BANCO (valores reais, cardinalidade, % de NULL):
{samples}
ATENCAO: Colunas marcadas com alto % NULL devem ser evitadas em filtros WHERE.
Colunas CAT mostram os valores exatos que existem; use-os literalmente nas queries.

{port_context}
INTENCAO CLASSIFICADA: {intent}

{context_hint}
{learning_hint}
PREFERENCIAS DO USUARIO:
- Limite de linhas padrao: {preferred_limit}

PERGUNTA DO USUARIO: {question}

INSTRUCOES PARA GERACAO DO SQL:
1. Use somente tabelas e colunas que existem no schema acima.
2. Use aliases claros e descritivos, por exemplo: a.id AS atracacao_id.
3. Evite SELECT *; selecione apenas colunas necessarias.
4. Aplique LIMIT em listagens, usando o padrao LIMIT {preferred_limit}.
5. Para contagens com JOIN, use COUNT(DISTINCT tabela.id).
6. Regra obrigatoria de data: para filtros temporais em atracacoes_navio, use sempre a coluna desatracacao como referencia de periodo.
7. Para filtros de mes/ano, use EXTRACT(YEAR FROM desatracacao) ou DATE_TRUNC('month', desatracacao).
8. Trate NULL com COALESCE ou IS NOT NULL quando relevante.
9. Use GROUP BY explicito em agregacoes.
10. Use ORDER BY explicito em rankings e listagens ordenadas.
11. Gere apenas SELECT; nunca INSERT, UPDATE, DELETE ou DDL.
12. Use aspas duplas para nomes de colunas/tabelas com caracteres especiais.
13. Nunca divida numeric por interval. Para duracao em horas entre timestamps, use:
    EXTRACT(EPOCH FROM (col_fim - col_inicio)) / 3600.0
14. Em subqueries e CTEs, aliases internos de tabela, como c ou a, existem somente dentro daquele bloco.
    No SELECT externo, WHERE externo e ORDER BY externo, use o alias da subquery/CTE ou nomes de colunas expostas.
    ERRADO: SELECT c.operacao FROM (SELECT c.operacao FROM cargas_atracacao c) sub ORDER BY c.operacao
    CORRETO: SELECT sub.operacao FROM (SELECT c.operacao FROM cargas_atracacao c) sub ORDER BY sub.operacao
15. Se usar ROW_NUMBER(), exponha todas as colunas necessarias na subquery/CTE e ordene externamente por essas colunas expostas.
16. Se a pergunta pede um total real e tambem uma listagem limitada, inclua COUNT(*) OVER() AS total_registros quando possivel.
17. Para produtividade/PLR de grupo, prefira produtividade ponderada: SUM(toneladas) / SUM(horas), salvo se o usuario pedir media simples.

EXEMPLOS DE SQL PARA DADOS PORTUARIOS:
-- Total por mes:
SELECT DATE_TRUNC('month', desatracacao) AS mes, SUM(dwt) AS total
FROM atracacoes_navio
GROUP BY 1
ORDER BY 1;

-- Ranking com COUNT DISTINCT:
SELECT berco, COUNT(DISTINCT id) AS qtd_atracacoes
FROM atracacoes_navio
GROUP BY berco
ORDER BY qtd_atracacoes DESC
LIMIT 10;

-- Comparativo entre anos:
SELECT EXTRACT(YEAR FROM desatracacao) AS ano, SUM(dwt) AS total
FROM atracacoes_navio
WHERE EXTRACT(YEAR FROM desatracacao) IN (2024, 2025)
GROUP BY 1
ORDER BY 1;

-- PLR (Prancha Liquida Real) = toneladas / horas operacionais:
SELECT
  SUM(c.quantidade_toneladas) / NULLIF(SUM(EXTRACT(EPOCH FROM (a.termino_operacao - a.inicio_operacao)) / 3600.0), 0) AS plr_ponderado
FROM atracacoes_navio a
JOIN cargas_atracacao c ON c.atracacao_id = a.id
WHERE a.termino_operacao IS NOT NULL
  AND a.inicio_operacao IS NOT NULL;

-- Ranking por subquery com ROW_NUMBER correto:
SELECT ranked.operacao, ranked.sentido, ranked.nome_carga, ranked.total_toneladas
FROM (
  SELECT
    c.operacao,
    c.sentido,
    c.nome_carga,
    SUM(c.quantidade_toneladas) AS total_toneladas,
    ROW_NUMBER() OVER (
      PARTITION BY c.operacao, c.sentido
      ORDER BY SUM(c.quantidade_toneladas) DESC
    ) AS rn
  FROM cargas_atracacao c
  JOIN atracacoes_navio a ON a.id = c.atracacao_id
  GROUP BY c.operacao, c.sentido, c.nome_carga
) ranked
WHERE ranked.rn <= 5
ORDER BY ranked.operacao, ranked.sentido, ranked.rn;

Responda SOMENTE com o SQL puro, sem explicacoes, sem markdown, sem comentarios.
O SQL deve ser uma unica instrucao SELECT valida.
"""

SQL_CROSS_CHECK_PROMPT = """
Voce e um especialista em SQL PostgreSQL.

SCHEMA DO BANCO:
{schema}

A seguinte consulta foi executada para responder: "{question}"

SQL PRINCIPAL:
{main_sql}

RESULTADO PRINCIPAL:
{main_result}

Crie uma segunda consulta de verificacao que produza o mesmo resultado usando estrutura SQL diferente.

OBRIGATORIO:
- Use as mesmas colunas de data e a mesma logica de agregacao do SQL principal.
- Apenas mude a estrutura, como subquery ou CTE; nao mude campos nem filtros.
- Se o principal usa DATE_TRUNC, a verificacao tambem deve usar DATE_TRUNC na mesma coluna.
- Se o principal filtra por ano=2025, a verificacao tambem deve filtrar por ano=2025.
- Nao use colunas ou tabelas diferentes das do SQL principal.
- Em SELECT/ORDER BY externos, nao use aliases internos de subqueries.

O objetivo e confirmar o resultado por outro caminho equivalente, nao produzir um resultado diferente.

Responda SOMENTE com o SQL puro de verificacao, sem explicacoes.
"""
