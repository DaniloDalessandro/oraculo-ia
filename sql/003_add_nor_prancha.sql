BEGIN;

ALTER TABLE atracacoes_navio
    ADD COLUMN IF NOT EXISTS nor TIMESTAMP;

ALTER TABLE cargas_atracacao
    ADD COLUMN IF NOT EXISTS prancha INTEGER;

UPDATE atracacoes_navio
SET
    nor = COALESCE(
        nor,
        atracacao - (((id % 48) + 1)::TEXT || ' hours')::INTERVAL,
        eta,
        created_at,
        CURRENT_TIMESTAMP
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE nor IS NULL;

UPDATE cargas_atracacao
SET
    prancha = COALESCE(prancha, 300 + (id % 743)::INTEGER),
    updated_at = CURRENT_TIMESTAMP
WHERE prancha IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_atracacoes_navio_nor_antes_atracacao'
    ) THEN
        ALTER TABLE atracacoes_navio
            ADD CONSTRAINT chk_atracacoes_navio_nor_antes_atracacao
            CHECK (nor IS NULL OR atracacao IS NULL OR nor <= atracacao);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_cargas_atracacao_prancha_intervalo'
    ) THEN
        ALTER TABLE cargas_atracacao
            ADD CONSTRAINT chk_cargas_atracacao_prancha_intervalo
            CHECK (prancha IS NULL OR prancha BETWEEN 300 AND 1042);
    END IF;
END $$;

COMMENT ON COLUMN atracacoes_navio.nor IS
    'Notice of Readiness: data e hora de prontidao do navio, sempre menor ou igual a atracacao.';

COMMENT ON COLUMN cargas_atracacao.prancha IS
    'Produtividade operacional da mercadoria em toneladas por hora, com valor inteiro entre 300 e 1042.';

COMMIT;
