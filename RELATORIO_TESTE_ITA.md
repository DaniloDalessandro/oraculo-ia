# Relatorio de teste do ITA

Data do teste: 2026-05-10

Ambiente testado:
- Frontend: http://localhost:3002
- Backend: http://localhost:8001
- Endpoint usado: POST /ai-agent/ask/
- Usuario de teste criado: testador@oraculo.local
- Base: 6.200 atracacoes e 12.400 cargas, anos 2021 a 2025

## Resumo executivo

Foram executadas 15 perguntas dificeis contra o agente ITA, cobrindo joins, agregacoes, rankings, janelas analiticas, datas, consistencia referencial, PLR e produtividade.

Resultado geral:
- Aprovadas: 10
- Aprovadas com ressalva: 3
- Reprovadas: 2

Principais problemas encontrados:
- Dois SQLs invalidos foram gerados em perguntas com janela analitica/subquery.
- Uma resposta confundiu o limite de retorno de 50 linhas com o total real da consulta. O total real era 593.
- Em pergunta ambigua sobre "total mensal de PLR", o agente assumiu PLR medio sem pedir confirmacao.
- Algumas respostas textuais trouxeram interpretacoes de data que podem ficar erradas, por exemplo tratar 2025 como ano em andamento.

## Resultado por pergunta

| # | Pergunta | Status API | Avaliacao | Observacao |
|---|---|---:|---|---|
| 1 | Total de toneladas por ano e sentido entre 2021 e 2025 | success | Aprovada com ressalva | SQL correto para agregacao por ano/sentido. Ressalva: resposta marcou 2025 como parcial, embora o teste esteja em 2026 e a base va ate dez/2025. |
| 2 | Top 10 navios por permanencia no porto em 2024 | success | Aprovada | Calculou horas entre atracacao e desatracacao, ordenou e limitou corretamente. |
| 3 | Media de espera ETA -> atracacao por berco em 2025 | success | Aprovada | Boa agregacao por berco, com filtro de campos nulos. |
| 4 | Comparativo mensal DIESEL 2024 vs 2025 com variacao percentual | success | Aprovada | SQL correto com CASE por ano e variacao percentual. |
| 5 | Clientes com CARGA e DESCARGA em 2025, tonelagem por operacao | success | Aprovada | Usou CTE e HAVING para identificar clientes com ambas operacoes. |
| 6 | Bercos com maior proporcao de excludente=1 em 2025 | success | Aprovada | Usou FILTER e percentual corretamente. |
| 7 | Top 5 de cargas por tonelagem em 2023 separado por operacao e sentido | partial | Reprovada | SQL invalido: SELECT/ORDER BY externo usou alias `c` fora da subquery. Deveria usar colunas da subquery. |
| 8 | Atracacoes com duracao operacional negativa em 2025 | success | Aprovada | Retornou vazio de forma coerente e SQL estava correto. |
| 9 | Maior prancha media por carga e berco em 2025, minimo 5 registros | success | Aprovada | Bom uso de CTE, HAVING e ROW_NUMBER por berco. |
| 10 | Ranking de operadores por tonelagem em 2024 por sentido e participacao | success | Aprovada | Bom uso de janela `SUM(...) OVER (PARTITION BY sentido)`. |
| 11 | IMOs com mais de uma atracacao em 2025 e intervalo medio entre atracacoes | partial | Reprovada | SQL invalido: `i.imo` no ORDER BY nao estava agregado nem no GROUP BY. |
| 12 | Cargas sem atracacao correspondente | success | Aprovada | LEFT JOIN anti-match correto. Retorno vazio coerente. |
| 13 | Total mensal de PLR em 2025 | success | Aprovada com ressalva | Dominio define PLR como taxa, entao o agente calculou PLR mensal. Porem a pergunta pedia "total"; deveria esclarecer ou explicar a interpretacao. |
| 14 | Atracacoes de 2025 com mais de uma natureza_tipo e tonelagem total | success | Aprovada com ressalva grave | SQL retornou `LIMIT 50` e a resposta disse "50 atracacoes". Verificacao direta mostrou 593 atracacoes. Nao pode apresentar linhas limitadas como total. |
| 15 | Tempo medio de operacao por natureza_tipo e toneladas por hora | success | Aprovada | Resultado coerente; ressalva menor: produtividade por grupo pode ser mais robusta como total toneladas / total horas, nao media simples das linhas. |

## Evidencias criticas

Teste 7 falhou com:

```sql
SELECT c.operacao, c.sentido, c.nome_carga, total_toneladas
FROM (...)
WHERE rank <= 5
ORDER BY c.operacao, c.sentido, rank
```

Problema: o alias `c` nao existe fora da subquery.

Teste 11 falhou com erro de agrupamento:

```text
column "i.imo" must appear in the GROUP BY clause or be used in an aggregate function
```

Teste 14:
- Resposta do agente: "50 atracacoes"
- Verificacao direta: 593 atracacoes em 2025 com mais de uma `natureza_tipo`
- Causa: a consulta tinha `LIMIT 50` e a resposta tratou o numero de linhas retornadas como total real.

## Recomendacoes

1. Ajustar o prompt/validador para proibir alias de tabela fora do escopo em subqueries.
2. Criar validacao extra para queries com `ROW_NUMBER`, CTE e subquery, pois os dois erros reais apareceram nesse padrao.
3. Quando o SQL tiver `LIMIT`, a resposta deve dizer "primeiros N registros" e nunca inferir total a partir do `row_count`.
4. Para perguntas de total/listagem, se houver `LIMIT`, gerar tambem um `COUNT(*) OVER()` ou uma consulta de total.
5. Para PLR, quando o usuario pedir "total de PLR", responder que PLR e taxa e confirmar se deseja media mensal, produtividade total ponderada ou tonelagem.
6. Remover frases temporais fixas como "ano em andamento"; usar a data real do sistema ou a cobertura da base.
7. Adicionar testes automatizados com as 15 perguntas acima e expectativa minima: status, SQL executavel e ausencia de inferencia errada por truncamento.
