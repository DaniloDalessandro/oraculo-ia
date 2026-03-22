#!/bin/bash
# ============================================================
# Script de setup ONE-TIME para CI/CD do Oraculo IA
# Execute UMA VEZ da sua maquina local:
#   bash deploy/setup-ci.sh
# ============================================================

set -e

VPS_IP="82.25.75.110"
VPS_USER="root"
KEY_FILE="$HOME/.ssh/oraculo_deploy_key"

echo "=== Setup CI/CD Oraculo IA ==="
echo ""

# 1. Gerar chave SSH dedicada para deploy
if [ ! -f "$KEY_FILE" ]; then
  echo "Gerando chave SSH para deploy..."
  ssh-keygen -t ed25519 -C "github-actions-oraculo" -f "$KEY_FILE" -N ""
  echo "Chave gerada: $KEY_FILE"
else
  echo "Chave SSH ja existe: $KEY_FILE"
fi

# 2. Copiar chave publica para o VPS
echo ""
echo "Copiando chave publica para o VPS $VPS_IP..."
echo "(sera pedida a senha root do VPS)"
ssh-copy-id -i "${KEY_FILE}.pub" "$VPS_USER@$VPS_IP"
echo "Chave SSH instalada no VPS!"

# 3. Testar conexao
echo ""
echo "Testando conexao SSH sem senha..."
ssh -i "$KEY_FILE" -o BatchMode=yes "$VPS_USER@$VPS_IP" "echo 'SSH OK!'"

# 4. Mostrar o que adicionar no GitHub
echo ""
echo "================================================================"
echo "PROXIMO PASSO: adicionar estes 4 secrets no GitHub"
echo "Acesse: https://github.com/DaniloDalessandro/oraculo-ia/settings/secrets/actions"
echo "================================================================"
echo ""
echo "Secret 1 — VPS_HOST"
echo "  Valor: $VPS_IP"
echo ""
echo "Secret 2 — VPS_USER"
echo "  Valor: $VPS_USER"
echo ""
echo "Secret 3 — VPS_SSH_PRIVATE_KEY"
echo "  Valor (copie tudo abaixo, incluindo BEGIN e END):"
echo "---"
cat "$KEY_FILE"
echo "---"
echo ""
echo "Secret 4 — GHCR_PAT"
echo "  Crie em: https://github.com/settings/tokens/new"
echo "  Nome: oraculo-deploy"
echo "  Escopo necessario: write:packages (inclui read:packages)"
echo "  Depois adicione o token como secret GHCR_PAT"
echo ""
echo "================================================================"
echo "Apos adicionar os 4 secrets, faca git push para main e o"
echo "deploy vai rodar automaticamente!"
echo "================================================================"
