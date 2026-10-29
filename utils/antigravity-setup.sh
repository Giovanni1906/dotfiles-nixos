#!/usr/bin/env bash
# Crea el entorno virtual de google-antigravity en ~/.local/share/antigravity/venv.
# Idempotente: se puede ejecutar varias veces sin problema.

set -euo pipefail

VENV="$HOME/.local/share/antigravity/venv"

ok()    { printf '  \033[32m✓\033[0m %s\n' "$*"; }
aviso() { printf '  \033[33m!\033[0m %s\n' "$*"; }
error() { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

command -v uv > /dev/null || error "uv no está instalado: primero ./init.sh sistema"

if [ -d "$VENV" ]; then
    ok "Entorno ya existe en $VENV"
else
    mkdir -p "$(dirname "$VENV")"
    uv venv "$VENV"
    ok "Entorno creado en $VENV"
fi

uv pip install --python "$VENV/bin/python" google-antigravity
ok "google-antigravity instalado"

ENV_FILE="$HOME/dotfiles/.env"
if [ ! -f "$ENV_FILE" ] || ! grep -q 'GEMINI_API_KEY' "$ENV_FILE"; then
    aviso "Añade GEMINI_API_KEY a ~/dotfiles/.env para usar el SDK"
fi

printf '\n  Para activar el entorno:\n    source %s/bin/activate\n    (o el alias: ag-activate)\n\n' "$VENV"
