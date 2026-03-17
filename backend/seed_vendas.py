"""
Popula a tabela vendas com 1000 registros sintéticos.

Uso:
  docker compose exec backend python seed_vendas.py
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.database import Base
from app.models.venda import Venda

# ── Dados de referência ───────────────────────────────────────────────────────

PRODUTOS = {
    "Eletrônicos": [
        ("Smartphone Samsung Galaxy A54", 1899.90),
        ("Notebook Dell Inspiron 15", 3499.00),
        ("Tablet iPad 10ª geração", 2799.00),
        ("Smart TV LG 50\"", 2199.00),
        ("Fone Bluetooth Sony WH-1000XM5", 1299.00),
        ("Monitor LG 27\" Full HD", 899.00),
        ("Câmera Sony Alpha 6400", 5499.00),
        ("Teclado Mecânico Keychron K2", 499.00),
    ],
    "Eletrodomésticos": [
        ("Geladeira Brastemp Frost Free 400L", 2899.00),
        ("Máquina de Lavar Consul 11kg", 1599.00),
        ("Micro-ondas Electrolux 31L", 599.00),
        ("Cafeteira Nespresso Vertuo", 799.00),
        ("Aspirador Robô Roomba i3", 1899.00),
        ("Ar Condicionado Split Midea 12000 BTU", 1799.00),
        ("Liquidificador Philips Walita", 299.00),
        ("Fritadeira Air Fryer Philco 4L", 399.00),
    ],
    "Móveis": [
        ("Sofá 3 Lugares Retrátil", 2199.00),
        ("Mesa de Jantar 6 Cadeiras", 1899.00),
        ("Cama Box Casal Queen", 1499.00),
        ("Guarda-Roupa 6 Portas", 1299.00),
        ("Escrivaninha Home Office", 699.00),
        ("Cadeira Gamer ThunderX3", 899.00),
        ("Estante para Livros 5 Prateleiras", 349.00),
        ("Rack para TV 180cm", 599.00),
    ],
    "Vestuário": [
        ("Tênis Nike Air Max 270", 599.00),
        ("Jaqueta Jeans Levi's", 349.00),
        ("Vestido Midi Floral", 199.00),
        ("Calça Cargo Masculina", 179.00),
        ("Camisa Social Masculina", 149.00),
        ("Bolsa de Couro Feminina", 299.00),
        ("Óculos de Sol Ray-Ban Wayfarer", 499.00),
        ("Tênis Adidas Ultraboost 22", 699.00),
    ],
    "Alimentos": [
        ("Kit Whey Protein 1kg", 149.00),
        ("Cesta Básica Completa", 299.00),
        ("Vinho Tinto Reservado Concha y Toro", 89.90),
        ("Azeite Extravirgem 500ml", 49.90),
        ("Chocolate Belga 70% 200g", 29.90),
        ("Café Especial 500g", 59.90),
        ("Mel Orgânico 700g", 44.90),
        ("Kit Chás Premium 50 sachês", 79.90),
    ],
    "Livros": [
        ("Clean Code - Robert Martin", 89.90),
        ("O Poder do Hábito - Charles Duhigg", 49.90),
        ("Pai Rico Pai Pobre - Robert Kiyosaki", 44.90),
        ("Sapiens - Yuval Noah Harari", 54.90),
        ("O Senhor dos Anéis - Tolkien", 129.90),
        ("Atomic Habits - James Clear", 59.90),
        ("Design Patterns - Gang of Four", 119.90),
        ("Fundamentos de Algoritmos", 99.90),
    ],
}

CLIENTES = [
    "Ana Paula Ferreira", "Bruno Costa Lima", "Carlos Eduardo Souza",
    "Daniela Mendes", "Eduardo Ramos", "Fernanda Oliveira",
    "Gabriel Silva", "Helena Barbosa", "Igor Martins", "Julia Carvalho",
    "Lucas Pereira", "Mariana Santos", "Nicolas Rodrigues", "Olivia Alves",
    "Pedro Henrique Lima", "Rafaela Gomes", "Samuel Nunes", "Tatiane Moreira",
    "Ulisses Figueiredo", "Vanessa Cunha", "Wagner Teixeira", "Xuxa Mendes",
    "Yuri Andrade", "Zuleica Borges", "Alexandre Pinto", "Beatriz Lopes",
    "Caio Fernandes", "Diana Rocha", "Elias Vieira", "Fabiana Castro",
]

VENDEDORES = [
    "João Vendedor", "Maria Vendas", "Roberto Comercial",
    "Patrícia Negócios", "Marcos Estrela", "Cristiane Top",
    "Anderson Prime", "Luciana Vendas",
]

REGIOES = ["Sudeste", "Sul", "Nordeste", "Norte", "Centro-Oeste"]

STATUS_PAGAMENTO = ["pago", "pago", "pago", "pendente", "cancelado"]

FORMAS_PAGAMENTO = [
    "Cartão de Crédito", "Cartão de Crédito", "Cartão de Débito",
    "PIX", "PIX", "Boleto", "Dinheiro",
]


def random_date(start_days_ago: int = 365) -> datetime:
    delta = random.randint(0, start_days_ago)
    return datetime.now(timezone.utc) - timedelta(days=delta, hours=random.randint(0, 23), minutes=random.randint(0, 59))


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSess = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    vendas = []
    for _ in range(1000):
        categoria = random.choice(list(PRODUTOS.keys()))
        produto, valor_unit = random.choice(PRODUTOS[categoria])
        # Variação de ±15% no preço
        valor_unit = round(valor_unit * random.uniform(0.85, 1.15), 2)
        quantidade = random.randint(1, 5)
        valor_total = round(valor_unit * quantidade, 2)

        vendas.append(Venda(
            id=uuid.uuid4(),
            data_venda=random_date(),
            produto=produto,
            categoria=categoria,
            quantidade=quantidade,
            valor_unitario=valor_unit,
            valor_total=valor_total,
            cliente=random.choice(CLIENTES),
            vendedor=random.choice(VENDEDORES),
            regiao=random.choice(REGIOES),
            status_pagamento=random.choice(STATUS_PAGAMENTO),
            forma_pagamento=random.choice(FORMAS_PAGAMENTO),
            created_at=datetime.now(timezone.utc),
        ))

    async with AsyncSess() as db:
        db.add_all(vendas)
        await db.commit()

    await engine.dispose()
    print(f"✓ {len(vendas)} vendas inseridas com sucesso.")


if __name__ == "__main__":
    asyncio.run(main())
