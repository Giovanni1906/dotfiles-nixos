#!/usr/bin/env bash
# =============================================================================
# CONECTOR DE PROYECTOS AL MCP CONTEXT-HUB (Mac Mini vía Tailscale)
# =============================================================================
# Uso: context-init [nombre-proyecto] [--forzar]
#
# Ejecútalo en la raíz de cualquier repositorio para:
#   1. Crear AGENTS.md, el enlace CLAUDE.md -> AGENTS.md y .cursor/rules/context-hub.mdc
#   2. Si existía un CLAUDE.md previo con reglas, migrar su contenido al MCP
#   3. Registrar el proyecto en el servidor MCP context-hub (CONTEXT_HUB_URL en ~/dotfiles/.env)

set -euo pipefail

[ -f "$HOME/dotfiles/.env" ] && source "$HOME/dotfiles/.env"
MCP_URL="${CONTEXT_HUB_URL:-}"
PROYECTO=""
FORZAR=0

for arg in "$@"; do
    case "$arg" in
        --forzar|-f) FORZAR=1 ;;
        -h|--help)
            sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) PROYECTO="$arg" ;;
    esac
done

[ -n "$PROYECTO" ] || PROYECTO="$(basename "$PWD")"

ok()    { printf '  \033[32m✓\033[0m %s\n' "$*"; }
aviso() { printf '  \033[33m!\033[0m %s\n' "$*"; }
error() { printf '  \033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

printf '\033[1;36m==> Conectando proyecto "%s" a context-hub (%s)\033[0m\n' "$PROYECTO" "$MCP_URL"

# 1. Si hay un CLAUDE.md real (no symlink) que aún no apunta a context-hub, rescatar sus reglas
REGLAS_PREVIAS=""
if [ -f "CLAUDE.md" ] && [ ! -L "CLAUDE.md" ] && ! grep -q "context-hub" "CLAUDE.md" 2>/dev/null; then
    REGLAS_PREVIAS="$(cat "CLAUDE.md")"
    cp "CLAUDE.md" "CLAUDE.md.respaldo"
    ok "Reglas previas detectadas en CLAUDE.md (respaldo en CLAUDE.md.respaldo)"
fi

# 2. Crear AGENTS.md (leído por Antigravity, Cursor, Hermes, Codex)
if [ ! -f "AGENTS.md" ] || [ "$FORZAR" = 1 ] || [ -n "$REGLAS_PREVIAS" ]; then
    cat > "AGENTS.md" <<EOF
# Contexto Unificado — \`${PROYECTO}\`

> **Instrucción obligatoria para todos los agentes (Cursor, Claude Code, Antigravity, Hermes, Codex):**
> 1. Al comenzar cualquier tarea o conversación en este repositorio, llama **primero** a la herramienta MCP \`get_project_context(project_name="${PROYECTO}")\` del servidor \`context-hub\`.
> 2. Si el proyecto tiene carpeta \`docs/contexto/\`, revísala antes de cambios estructurales y mantenla actualizada (Memory-Driven Development).
> 3. Cuando resuelvas un bug no obvio o tomes una decisión importante, regístrala en la memoria compartida usando \`append_project_memory(project_name="${PROYECTO}", category="...", note="...")\`.
EOF
    ok "Creado AGENTS.md"
else
    ok "AGENTS.md ya existe (usa --forzar para sobrescribir)"
fi

# 3. Enlazar CLAUDE.md -> AGENTS.md (para Claude Code)
ln -sf "AGENTS.md" "CLAUDE.md"
ok "Enlazado CLAUDE.md -> AGENTS.md"

# 4. Crear regla para Cursor (.cursor/rules/context-hub.mdc)
mkdir -p ".cursor/rules"
cat > ".cursor/rules/context-hub.mdc" <<EOF
---
description: Conexión automática al servidor MCP context-hub
globs: *
alwaysApply: true
---

Al iniciar cualquier tarea en este proyecto (\`${PROYECTO}\`), llama primero a la herramienta \`get_project_context(project_name="${PROYECTO}")\` del servidor MCP \`context-hub\` para cargar las reglas globales, las reglas del proyecto y la memoria compartida entre agentes.
EOF
ok "Creado .cursor/rules/context-hub.mdc"

# 5. Verificar/registrar el proyecto en el servidor MCP de la Mac Mini
llamar_mcp() {
    local payload="$1"
    curl -sS --max-time 5 -X POST "$MCP_URL" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "$payload" 2>/dev/null || true
}

escapar_json() {
    python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

 consulta_payload=$(printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_project_context","arguments":{"project_name":"%s","include_global":false}}}' "$PROYECTO")
respuesta=$(llamar_mcp "$consulta_payload")

if [ -z "$respuesta" ]; then
    aviso "No se pudo contactar a $MCP_URL (verifica Tailscale). Los archivos locales ya quedaron listos."
    exit 0
fi

if grep -q "NO ENCONTRADO" <<< "$respuesta" || [ "$FORZAR" = 1 ] || [ -n "$REGLAS_PREVIAS" ]; then
    if [ -n "$REGLAS_PREVIAS" ]; then
        reglas_md="$REGLAS_PREVIAS"
    else
        reglas_md="# Reglas del Proyecto: \`${PROYECTO}\`

## 1. Descripción y Stack
- Proyecto: \`${PROYECTO}\`
- Revisa \`README.md\` y \`docs/contexto/\` (si existe) para detalles de arquitectura.

## 2. Convenciones
- Commits en español siguiendo Conventional Commits (\`feat:\`, \`fix:\`, \`docs:\`, \`refactor:\`).
- Registrar decisiones importantes y bugs resueltos con \`append_project_memory\`.
"
    fi

    reglas_json=$(printf '%s' "$reglas_md" | escapar_json)
    registro_payload=$(printf '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"register_or_update_project","arguments":{"project_name":"%s","rules_markdown":%s}}}' "$PROYECTO" "$reglas_json")
    reg_resp=$(llamar_mcp "$registro_payload")

    if grep -q "exitosamente" <<< "$reg_resp"; then
        ok "Proyecto '${PROYECTO}' registrado en la Mac Mini (~/context-hub/data/projects/${PROYECTO}/)"
        [ -f "CLAUDE.md.respaldo" ] && rm -f "CLAUDE.md.respaldo"
    else
        aviso "Respuesta inesperada al registrar en MCP: $reg_resp"
    fi
else
    ok "El proyecto '${PROYECTO}' ya está registrado en la Mac Mini (usa --forzar para sobrescribir sus reglas)"
fi
