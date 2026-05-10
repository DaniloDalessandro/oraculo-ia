DO $$
DECLARE
    total_atracacoes CONSTANT INTEGER := 6200;

    navios TEXT[] := ARRAY[
        'TORM ATLANTIC',
        'FAIR WINDS',
        'NAVE ATRIA',
        'LUCIO COSTA',
        'MISHELL',
        'STAR OSPREY',
        'ZUMBA',
        'DALLAS',
        'OCEAN ELECTRA',
        'RUKAI BENEFIT',
        'CYMONA ENERGY',
        'SUPER G',
        'SEASTAR VIKING',
        'ATLANTIC PIONEER',
        'PACIFIC HORIZON',
        'MARINE EXPRESS',
        'BLUE ORION',
        'SANTOS TRADER',
        'RIO NAVIGATOR',
        'GLOBAL MERCURY'
    ];

    bercos TEXT[] := ARRAY['99', '100', '101', '102', '103', '104', '105', '106', '108'];
    agencias TEXT[] := ARRAY[
        'WILSON SONS',
        'INCHCAPE SHIPPING',
        'LBH BRASIL',
        'TRAMARCO',
        'BEMARITIMA',
        'UNIMAR',
        'OCEANUS AGENCIAMENTO'
    ];
    clientes TEXT[] := ARRAY[
        'PETROBRAS',
        'RAIZEN',
        'YARA BRASIL',
        'BRASKEM',
        'SUZANO',
        'BUNGE',
        'CARGILL',
        'VIBRA ENERGIA',
        'COPERSUCAR',
        'ULTRACARGO'
    ];
    cargas TEXT[] := ARRAY[
        'FERTILIZANTE',
        'GASOLINA',
        'DIESEL',
        'ETANOL',
        'CELULOSE',
        'CARGA GERAL',
        'GRANEL LÍQUIDO',
        'GRANEL SÓLIDO'
    ];
    operadores TEXT[] := ARRAY[
        'OPERADOR TERMINAL 1',
        'OPERADOR TERMINAL 2',
        'OPERADOR GRANÉIS',
        'OPERADOR LÍQUIDOS',
        'OPERADOR MULTICARGAS',
        'OPERADOR PORTUÁRIO SUL'
    ];

    i INTEGER;
    j INTEGER;
    ano INTEGER;
    qtd_cargas INTEGER;
    atracacao_id BIGINT;

    v_navio TEXT;
    v_berco TEXT;
    v_carga TEXT;
    v_natureza_tipo TEXT;
    v_natureza_subtipo TEXT;
    v_operacao TEXT;
    v_sentido TEXT;

    v_dwt NUMERIC(14, 2);
    v_comprimento NUMERIC(10, 2);
    v_largura NUMERIC(10, 2);
    v_calado_entrada NUMERIC(6, 2);
    v_calado_saida NUMERIC(6, 2);
    v_quantidade NUMERIC(14, 3);
    v_pbm NUMERIC(14, 3);
    v_prancha INTEGER;

    v_nor TIMESTAMP;
    v_eta TIMESTAMP;
    v_etb TIMESTAMP;
    v_atracacao TIMESTAMP;
    v_inicio TIMESTAMP;
    v_termino TIMESTAMP;
    v_desatracacao TIMESTAMP;
BEGIN
    PERFORM setseed(0.2025);

    FOR i IN 1..total_atracacoes LOOP
        ano := 2021 + ((i - 1) % 5);

        v_navio := navios[1 + floor(random() * array_length(navios, 1))::INTEGER];
        v_berco := bercos[1 + floor(random() * array_length(bercos, 1))::INTEGER];

        v_dwt := round((5000 + random() * 85000)::NUMERIC, 2);
        v_comprimento := round((100 + random() * 130)::NUMERIC, 2);
        v_largura := round((18 + random() * 18)::NUMERIC, 2);
        v_calado_entrada := round((6 + random() * 8)::NUMERIC, 2);
        v_calado_saida := round(GREATEST(5.5, v_calado_entrada - 1.5 + random() * 2.5)::NUMERIC, 2);

        v_atracacao :=
            make_timestamp(
                ano,
                1,
                1,
                floor(random() * 24)::INTEGER,
                floor(random() * 60)::INTEGER,
                0
            )
            + (floor(random() * 360)::INTEGER || ' days')::INTERVAL;

        v_nor := v_atracacao - ((1 + floor(random() * 48))::INTEGER || ' hours')::INTERVAL;
        v_eta := v_nor - ((1 + floor(random() * 24))::INTEGER || ' hours')::INTERVAL;
        v_etb := v_atracacao - ((floor(random() * 6))::INTEGER || ' hours')::INTERVAL;
        v_inicio := v_atracacao + ((1 + floor(random() * 10))::INTEGER || ' hours')::INTERVAL;
        v_termino := v_inicio + ((4 + floor(random() * 116))::INTEGER || ' hours')::INTERVAL;
        v_desatracacao := v_termino + ((floor(random() * 12))::INTEGER || ' hours')::INTERVAL;

        INSERT INTO atracacoes_navio (
            numero_atracacao,
            berco,
            navio,
            imo,
            agencia,
            cliente,
            eta,
            etb,
            nor,
            atracacao,
            inicio_operacao,
            termino_operacao,
            desatracacao,
            comprimento,
            largura,
            dwt,
            calado_entrada,
            calado_saida,
            status,
            created_at,
            updated_at
        )
        VALUES (
            'ATC-' || ano || '-' || lpad(i::TEXT, 6, '0'),
            v_berco,
            v_navio,
            '9' || lpad(floor(random() * 1000000)::TEXT, 6, '0'),
            agencias[1 + floor(random() * array_length(agencias, 1))::INTEGER],
            clientes[1 + floor(random() * array_length(clientes, 1))::INTEGER],
            v_eta,
            v_etb,
            v_nor,
            v_atracacao,
            v_inicio,
            v_termino,
            v_desatracacao,
            v_comprimento,
            v_largura,
            v_dwt,
            v_calado_entrada,
            v_calado_saida,
            CASE
                WHEN v_desatracacao < CURRENT_TIMESTAMP THEN 'desatracado'
                WHEN v_inicio <= CURRENT_TIMESTAMP AND v_termino >= CURRENT_TIMESTAMP THEN 'em_operacao'
                ELSE 'planejada'
            END,
            v_atracacao - INTERVAL '15 days',
            v_desatracacao
        )
        RETURNING id INTO atracacao_id;

        qtd_cargas := 1 + floor(random() * 3)::INTEGER;

        FOR j IN 1..qtd_cargas LOOP
            v_carga := cargas[1 + floor(random() * array_length(cargas, 1))::INTEGER];
            v_operacao := CASE WHEN random() < 0.52 THEN 'DESCARGA' ELSE 'CARGA' END;
            v_sentido := CASE WHEN v_operacao = 'CARGA' THEN 'EMBARQUE' ELSE 'DESEMBARQUE' END;
            v_quantidade := round((800 + random() * 65000)::NUMERIC, 3);
            v_pbm := round((v_quantidade * (0.96 + random() * 0.08))::NUMERIC, 3);
            v_prancha := 300 + floor(random() * 743)::INTEGER;

            v_natureza_tipo := CASE
                WHEN v_carga IN ('GASOLINA', 'DIESEL', 'ETANOL', 'GRANEL LÍQUIDO') THEN 'GRANEL LÍQUIDO'
                WHEN v_carga IN ('FERTILIZANTE', 'GRANEL SÓLIDO') THEN 'GRANEL SÓLIDO'
                ELSE 'CARGA GERAL'
            END;

            v_natureza_subtipo := CASE
                WHEN v_carga IN ('GASOLINA', 'DIESEL', 'ETANOL') THEN 'COMBUSTÍVEL'
                WHEN v_carga = 'FERTILIZANTE' THEN 'INSUMO AGRÍCOLA'
                WHEN v_carga = 'CELULOSE' THEN 'PRODUTO FLORESTAL'
                WHEN v_carga = 'CARGA GERAL' THEN 'MULTIPROPÓSITO'
                ELSE v_carga
            END;

            INSERT INTO cargas_atracacao (
                atracacao_id,
                nome_carga,
                natureza_tipo,
                natureza_subtipo,
                operacao,
                sentido,
                operador,
                quantidade_toneladas,
                plr,
                prancha,
                observacao,
                created_at,
                updated_at
            )
            VALUES (
                atracacao_id,
                v_carga,
                v_natureza_tipo,
                v_natureza_subtipo,
                v_operacao,
                v_sentido,
                operadores[1 + floor(random() * array_length(operadores, 1))::INTEGER],
                v_quantidade,
                'PLR-' || ano || '-' || lpad(i::TEXT, 6, '0') || '-' || j,
                v_prancha,
                'Dados sintéticos portuários. PBM=' || v_pbm
                    || ' t; LOA=' || v_comprimento
                    || ' m; BOCA=' || v_largura
                    || ' m.',
                v_atracacao - INTERVAL '15 days',
                v_desatracacao
            );
        END LOOP;
    END LOOP;
END $$;
