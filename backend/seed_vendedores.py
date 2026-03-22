"""
Popula vendedores (10 registros) e vendas (10.000.000 registros) usando
generate_series do PostgreSQL — sem loop Python, sem memória extra.

Pré-requisito:
  docker compose exec backend alembic upgrade head

Uso:
  docker compose exec backend python seed_vendedores.py

Tempo estimado: 2–8 minutos dependendo do hardware da VPS.
"""

import os
import time

import psycopg2

DSN = (
    os.environ.get("DATABASE_URL_SYNC", "postgresql+psycopg2://postgres:postgres@db:5432/oraculo")
    .replace("postgresql+psycopg2://", "postgresql://")
)

VENDEDORES = [
    ("João Silva",      "joao.silva@empresa.com",      "Sudeste",      95000),
    ("Maria Santos",    "maria.santos@empresa.com",    "Sul",          82000),
    ("Roberto Faria",   "roberto.faria@empresa.com",   "Nordeste",     78000),
    ("Patricia Lopes",  "patricia.lopes@empresa.com",  "Norte",        70000),
    ("Marcos Oliveira", "marcos.oliveira@empresa.com", "Centro-Oeste", 88000),
    ("Cristiane Lima",  "cristiane.lima@empresa.com",  "Sudeste",      91000),
    ("Anderson Costa",  "anderson.costa@empresa.com",  "Sul",          76000),
    ("Luciana Pereira", "luciana.pereira@empresa.com", "Nordeste",     83000),
    ("Felipe Rocha",    "felipe.rocha@empresa.com",    "Sudeste",      99000),
    ("Camila Torres",   "camila.torres@empresa.com",   "Sul",          87000),
]

SQL_VENDAS = """
INSERT INTO vendas (
    id, data_venda, produto, categoria, quantidade, valor_unitario, valor_total,
    cliente, vendedor, vendedor_id, regiao, status_pagamento, forma_pagamento, created_at
)
SELECT
    gen_random_uuid(),
    NOW() - (random() * INTERVAL '3 years'),
    (ARRAY[
        'Smartphone Samsung Galaxy A54',
        'Notebook Dell Inspiron 15',
        'Tablet iPad 10ª geração',
        'Smart TV LG 50"',
        'Monitor LG 27" Full HD',
        'Câmera Sony Alpha 6400',
        'Geladeira Brastemp Frost Free 400L',
        'Máquina de Lavar Consul 11kg',
        'Ar Condicionado Midea 12000 BTU',
        'Tênis Nike Air Max 270',
        'Cadeira Gamer ThunderX3',
        'Sofá 3 Lugares Retrátil',
        'Cafeteira Nespresso Vertuo',
        'Teclado Mecânico Keychron K2',
        'Fone Bluetooth Sony WH-1000XM5',
        'Kit Whey Protein 1kg'
    ])[1 + (random() * 15)::int],
    (ARRAY[
        'Eletrônicos', 'Eletrodomésticos', 'Móveis',
        'Vestuário',   'Alimentos',        'Periféricos'
    ])[1 + (random() * 5)::int],
    qty,
    price,
    qty * price,
    'Cliente ' || (1000 + (random() * 8999)::int)::text,
    v.nome,
    v.id,
    v.regiao,
    (ARRAY['pago', 'pago', 'pago', 'pendente', 'cancelado'])[1 + (random() * 4)::int],
    (ARRAY[
        'Cartão de Crédito', 'Cartão de Crédito', 'Cartão de Débito',
        'PIX', 'PIX', 'Boleto', 'Dinheiro'
    ])[1 + (random() * 6)::int],
    NOW() - (random() * INTERVAL '3 years')
FROM generate_series(1, 10000000) gs
CROSS JOIN LATERAL (SELECT (1 + floor(random() * 10))::int AS vid) x
CROSS JOIN LATERAL (SELECT id, nome, regiao FROM vendedores WHERE id = x.vid) v
CROSS JOIN LATERAL (SELECT (1 + (random() * 9)::int) AS qty) q
CROSS JOIN LATERAL (SELECT ((50 + random() * 4950)::numeric(10, 2)) AS price) p
"""


def main() -> None:
    print("Conectando ao banco...")
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()

    # Sem timeout para esta operação longa
    cur.execute("SET statement_timeout = 0")

    print("Limpando dados anteriores...")
    # CASCADE limpa vendas automaticamente (FK vendedor_id → vendedores.id)
    cur.execute("TRUNCATE vendedores RESTART IDENTITY CASCADE")
    conn.commit()

    print("Inserindo 10 vendedores...")
    cur.executemany(
        "INSERT INTO vendedores (nome, email, regiao, meta_mensal) VALUES (%s, %s, %s, %s)",
        VENDEDORES,
    )
    conn.commit()
    print("  ✓ 10 vendedores inseridos (IDs 1–10)")

    print("\nGerando 10.000.000 vendas via generate_series...")
    print("  (isso pode levar alguns minutos — o PostgreSQL gera tudo internamente)\n")
    t0 = time.time()

    cur.execute(SQL_VENDAS)
    conn.commit()

    elapsed = time.time() - t0
    mins, secs = divmod(int(elapsed), 60)
    print(f"  ✓ 10.000.000 vendas inseridas em {mins}m {secs}s")

    cur.execute("SELECT COUNT(*) FROM vendas")
    total = cur.fetchone()[0]
    print(f"  ✓ Total atual na tabela: {total:,}")

    cur.execute("""
        SELECT v.nome, COUNT(*) AS total_vendas, SUM(vd.valor_total)::numeric(14,2) AS receita
        FROM vendas vd
        JOIN vendedores v ON v.id = vd.vendedor_id
        GROUP BY v.nome
        ORDER BY receita DESC
    """)
    print("\n  Resumo por vendedor:")
    print(f"  {'Nome':<22} {'Vendas':>12} {'Receita':>18}")
    print("  " + "-" * 54)
    for nome, total_v, receita in cur.fetchall():
        print(f"  {nome:<22} {total_v:>12,} R$ {receita:>14,.2f}")

    cur.close()
    conn.close()
    print("\nConcluído.")


if __name__ == "__main__":
    main()
