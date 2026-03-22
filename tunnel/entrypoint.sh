#!/bin/bash
set -e

echo "=== Tunnel Service Starting ==="

# 1. Start backend tunnel (webhook)
cloudflared tunnel --url http://backend:8000 --no-autoupdate > /tmp/cf_backend.log 2>&1 &
CF_BACKEND_PID=$!
echo "[tunnel] cloudflared backend started (PID: $CF_BACKEND_PID)"

# 2. Start frontend tunnel (login page)
cloudflared tunnel --url http://frontend:3000 --no-autoupdate > /tmp/cf_frontend.log 2>&1 &
CF_FRONTEND_PID=$!
echo "[tunnel] cloudflared frontend started (PID: $CF_FRONTEND_PID)"

# 3. Wait for both URLs
BACKEND_URL=""
FRONTEND_URL=""

for i in $(seq 1 40); do
    sleep 3
    if [ -z "$BACKEND_URL" ]; then
        BACKEND_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cf_backend.log 2>/dev/null | head -1)
    fi
    if [ -z "$FRONTEND_URL" ]; then
        FRONTEND_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cf_frontend.log 2>/dev/null | head -1)
    fi

    if [ -n "$BACKEND_URL" ] && [ -n "$FRONTEND_URL" ]; then
        echo "[tunnel] Backend URL: $BACKEND_URL"
        echo "[tunnel] Frontend URL: $FRONTEND_URL"
        break
    else
        echo "[tunnel] Aguardando URLs... backend=${BACKEND_URL:-?} frontend=${FRONTEND_URL:-?} (${i}/40)"
    fi
done

if [ -z "$BACKEND_URL" ] || [ -z "$FRONTEND_URL" ]; then
    echo "[tunnel] ERRO: URLs não encontradas após 120s"
    cat /tmp/cf_backend.log
    cat /tmp/cf_frontend.log
    exit 1
fi

# 4. Wait for connections to be established
echo "[tunnel] Aguardando conexões estáveis..."
sleep 5

# 5. Test tunnels
echo "[tunnel] Testando tunnels..."
BACKEND_TEST=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/health" 2>/dev/null || echo "FAIL")
FRONTEND_TEST=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}" 2>/dev/null || echo "FAIL")
echo "[tunnel] Backend health check: $BACKEND_TEST"
echo "[tunnel] Frontend health check: $FRONTEND_TEST"

# 6. Register webhook with Meta
APP_ID="${WHATSAPP_APP_ID}"
APP_SECRET="${WHATSAPP_APP_SECRET}"

if [ -n "$APP_ID" ] && [ -n "$APP_SECRET" ]; then
    APP_ACCESS_TOKEN="${APP_ID}|${APP_SECRET}"
    echo "[tunnel] Registrando webhook no Meta..."
    REG=$(curl -s -X POST \
        "https://graph.facebook.com/${WHATSAPP_API_VERSION}/${APP_ID}/subscriptions" \
        -d "object=whatsapp_business_account" \
        -d "callback_url=${BACKEND_URL}/webhook/whatsapp" \
        -d "verify_token=${WHATSAPP_VERIFY_TOKEN}" \
        -d "fields=messages" \
        -d "access_token=${APP_ACCESS_TOKEN}")
    echo "[tunnel] Resultado registro: $REG"

    if echo "$REG" | jq -e '.success == true' > /dev/null 2>&1; then
        echo "[tunnel] ✓ Webhook registrado com sucesso!"
    else
        echo "[tunnel] ⚠ Falha no registro — tentando novamente em 10s..."
        sleep 10
        REG2=$(curl -s -X POST \
            "https://graph.facebook.com/${WHATSAPP_API_VERSION}/${APP_ID}/subscriptions" \
            -d "object=whatsapp_business_account" \
            -d "callback_url=${BACKEND_URL}/webhook/whatsapp" \
            -d "verify_token=${WHATSAPP_VERIFY_TOKEN}" \
            -d "fields=messages" \
            -d "access_token=${APP_ACCESS_TOKEN}")
        echo "[tunnel] Segunda tentativa: $REG2"
        if echo "$REG2" | jq -e '.success == true' > /dev/null 2>&1; then
            echo "[tunnel] ✓ Webhook registrado na segunda tentativa!"
        fi
    fi
else
    echo "[tunnel] ⚠ WHATSAPP_APP_ID ou WHATSAPP_APP_SECRET não configurados."
fi

# 7. Subscribe phone number
if [ -n "$WHATSAPP_TOKEN" ]; then
    echo "[tunnel] Inscrevendo número no WhatsApp..."
    SUB=$(curl -s -X POST \
        "https://graph.facebook.com/${WHATSAPP_API_VERSION}/${WHATSAPP_PHONE_NUMBER_ID}/subscribed_apps" \
        -H "Authorization: Bearer ${WHATSAPP_TOKEN}")
    echo "[tunnel] Inscrição: $SUB"
fi

# 8. Update APP_URL on backend dynamically
echo "[tunnel] Atualizando APP_URL no backend para: $FRONTEND_URL"
UPDATE=$(curl -s -X POST "${BACKEND_URL}/internal/set-app-url" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${FRONTEND_URL}\"}" 2>/dev/null || echo "skipped")
echo "[tunnel] Update APP_URL: $UPDATE"

echo ""
echo "[tunnel] ============================================"
echo "[tunnel] BACKEND TUNNEL: $BACKEND_URL"
echo "[tunnel] FRONTEND TUNNEL: $FRONTEND_URL"
echo "[tunnel] WEBHOOK URL:    ${BACKEND_URL}/webhook/whatsapp"
echo "[tunnel] LOGIN URL:      ${FRONTEND_URL}/login"
echo "[tunnel] ============================================"

# Keep alive
tail -f /tmp/cf_backend.log /tmp/cf_frontend.log &
wait $CF_BACKEND_PID
