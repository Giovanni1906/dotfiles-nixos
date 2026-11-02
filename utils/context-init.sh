#!/usr/bin/env bash
# =============================================================================
# CONECTOR DE PROYECTOS AL MCP CONTEXT-HUB (Mac Mini vía Tailscale)
# =============================================================================
# Uso: context-init [nombre-proyecto] [--forzar|-f] [--plantilla|-p]
#
# Ejecútalo en la raíz de cualquier repositorio para:
#   1. Crear AGENTS.md, el enlace CLAUDE.md -> AGENTS.md y .cursor/rules/context-hub.mdc
#   2. Si existía un CLAUDE.md o .cursor/rules previo, migrar su contenido al MCP
#   3. Con --plantilla (-p), crear los 6 archivos base en docs/contexto/ (y README.md si falta)
#   4. Registrar el proyecto en el servidor MCP context-hub (CONTEXT_HUB_URL en ~/dotfiles/.env)

set -euo pipefail

# 0. Si el CLI universal context-hub está disponible, delegar en él directamente
for candidate in \
    "$HOME/.local/bin/context-init" \
    "$HOME/Proyectos/personal/context-hub/context-menu.sh" \
    "$HOME/.local/share/context-hub/context-menu.sh"; do
    if [ -f "$candidate" ] && [ -x "$candidate" ] && [ "$(realpath "$candidate" 2>/dev/null || true)" != "$(realpath "${BASH_SOURCE[0]}" 2>/dev/null || true)" ]; then
        exec "$candidate" "$@"
    fi
done

if [ "$PWD" = "$HOME" ] || [ "$PWD" = "/" ]; then
    printf '\n\033[1;31m✗ No puedes ejecutar context-init en tu carpeta personal (%s) ni en la raíz (/).\033[0m\n' "$PWD" >&2
    printf '  Navega a la carpeta de tu proyecto (ej. cd ~/Proyectos/mi-proyecto) antes de conectarlo.\n\n' >&2
    exit 1
fi

[ -f "$HOME/dotfiles/.env" ] && source "$HOME/dotfiles/.env"
MCP_URL="${CONTEXT_HUB_URL:-}"
PROYECTO=""
FORZAR=0
PLANTILLA=0

for arg in "$@"; do
    case "$arg" in
        --forzar|-f) FORZAR=1 ;;
        --plantilla|-p) PLANTILLA=1 ;;
        -h|--help)
            sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

# 0. Asegurar que los agentes locales tengan configurado context-hub (por si se editó .env sin rebuild)
if [ -n "$MCP_URL" ] && [[ "$MCP_URL" != *"ip_tailscale"* ]]; then
    mkdir -p "$HOME/.gemini/config" "$HOME/.cursor" "$HOME/.codex"
    for mcp_file in "$HOME/.gemini/config/mcp_config.json" "$HOME/.cursor/mcp.json"; do
        if [ ! -s "$mcp_file" ]; then
            cat > "$mcp_file" <<EOF
{
  "mcpServers": {
    "context-hub": {
      "url": "$MCP_URL"
    }
  }
}
EOF
        fi
    done
    if [ -d "$HOME/.hermes" ] && ! grep -q 'context-hub:' "$HOME/.hermes/config.yaml" 2>/dev/null; then
        cat >> "$HOME/.hermes/config.yaml" <<EOF

mcp_servers:
  context-hub:
    url: $MCP_URL
    enabled: true
EOF
    fi
    if ! grep -q 'context-hub' "$HOME/.codex/config.toml" 2>/dev/null; then
        cat >> "$HOME/.codex/config.toml" <<EOF
[mcp_servers.context-hub]
url = "$MCP_URL"
EOF
    fi
    if command -v claude >/dev/null 2>&1 && ! grep -q '"context-hub"' "$HOME/.claude.json" 2>/dev/null; then
        claude mcp add --transport http --scope user context-hub "$MCP_URL" >/dev/null 2>&1 || true
    fi
fi

# 1. Si hay un CLAUDE.md real (no symlink) o reglas previas en .cursor/, rescatar sus reglas
REGLAS_PREVIAS=""
if [ -f "CLAUDE.md" ] && [ ! -L "CLAUDE.md" ] && ! grep -q "context-hub" "CLAUDE.md" 2>/dev/null; then
    REGLAS_PREVIAS="$(cat "CLAUDE.md")"
    cp "CLAUDE.md" "CLAUDE.md.respaldo"
    ok "Reglas previas detectadas en CLAUDE.md (respaldo en CLAUDE.md.respaldo)"
elif [ -f ".cursorrules" ] && ! grep -q "context-hub" ".cursorrules" 2>/dev/null; then
    REGLAS_PREVIAS="$(cat ".cursorrules")"
    ok "Reglas previas detectadas en .cursorrules"
elif [ -d ".cursor/rules" ]; then
    for rfile in .cursor/rules/*.mdc .cursor/rules/*.md; do
        [ -f "$rfile" ] || continue
        [ "$(basename "$rfile")" = "context-hub.mdc" ] && continue
        contenido="$(awk 'NR==1 && /^---$/ { in_fm=1; next } in_fm && /^---$/ { in_fm=0; next } !in_fm { print }' "$rfile")"
        if [ -n "$contenido" ]; then
            REGLAS_PREVIAS="${REGLAS_PREVIAS:+$REGLAS_PREVIAS

}## Regla Cursor ($(basename "$rfile"))
$contenido"
        fi
    done
    [ -n "$REGLAS_PREVIAS" ] && ok "Reglas previas detectadas en .cursor/rules/"
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

# 4.5. Si se pidió --plantilla (-p), crear los 6 archivos MDD en docs/contexto/ (si no existen)
crear_archivo_plantilla() {
    local ruta="$1"
    if [ ! -f "$ruta" ] || [ "$FORZAR" = 1 ]; then
        cat > "$ruta"
        ok "Creado $ruta"
    else
        ok "$ruta ya existe (omitido)"
    fi
}

if [ "$PLANTILLA" = 1 ]; then
    mkdir -p "docs/contexto"
    crear_archivo_plantilla "docs/contexto/01-arquitectura.md" <<'EOF'
# Arquitectura del Sistema

## Descripción General
[Breve descripción del propósito del sistema y su alcance]

## Stack Tecnológico
- **Frontend**: [Ej. Next.js, React, Tailwind]
- **Backend**: [Ej. FastAPI, Go, Node.js]
- **Base de Datos**: [Ej. PostgreSQL, MongoDB, Qdrant]
- **Infraestructura**: [Ej. Docker, Kubernetes, Vercel]

## Diagrama de Componentes (Mental o Mermaid)
- **Capa de Presentación**: Maneja la UI y el estado del cliente.
- **Capa de API**: Controladores, validación de inputs y ruteo.
- **Capa de Dominio/Lógica**: Reglas de negocio y orquestación.
- **Capa de Datos**: Repositorios y conexión a BD.

## Patrones Arquitectónicos
- [Ej. Arquitectura Hexagonal / Microservicios / Monolito Modular]
- [Estrategia de Caché]
EOF

    crear_archivo_plantilla "docs/contexto/02-convenciones.md" <<'EOF'
# Convenciones del Proyecto

## Estilo de Código
- **Nomenclatura**: `camelCase` para variables/funciones, `PascalCase` para Clases/Componentes, `snake_case` para bases de datos o Python.
- **Tipado**: Tipado estricto obligatorio (TypeScript/Type Hints). Sin usar `any`.
- **Formateo**: Prettier / Black / Gofmt (según lenguaje).

## Git y Commits
- Usar Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`).
- Ramas: `main` (producción), `dev` (desarrollo), `feature/nombre-tarea`.

## Manejo de Errores
- Usar bloques `try/catch` o manejo nativo de errores del lenguaje.
- Nunca silenciar errores sin registrar (`log`). Retornar mensajes de error claros al cliente.
EOF

    crear_archivo_plantilla "docs/contexto/03-decisiones.md" <<'EOF'
# Registro de Decisiones Arquitectónicas (ADRs)

*Este archivo registra las decisiones importantes del proyecto para mantener el contexto histórico.*

## ADR-001: [Título de la decisión, ej. Uso de Qdrant para Vector DB]
- **Fecha**: [YYYY-MM-DD]
- **Contexto**: Necesitamos almacenar embeddings para la búsqueda semántica.
- **Decisión**: Se eligió [Tecnología/Patrón] porque [Justificación].
- **Consecuencias**: 
  - Positivas: [Ventaja 1], [Ventaja 2].
  - Negativas: [Curva de aprendizaje, costo, etc.].
EOF

    crear_archivo_plantilla "docs/contexto/04-glosario.md" <<'EOF'
# Glosario y Lenguaje Ubicuo

*Define los términos del negocio para que tanto desarrolladores, agentes de IA y stakeholders hablen el mismo idioma.*

- **[Término 1, ej. Usuario]**: Persona registrada en el sistema con credenciales válidas.
- **[Término 2, ej. Documento]**: Archivo subido al sistema que ha sido procesado y vectorizado.
- **[Término 3, ej. Workspace]**: Espacio aislado de trabajo que agrupa múltiples documentos y usuarios.
EOF

    crear_archivo_plantilla "docs/contexto/05-flujo-de-trabajo.md" <<'EOF'
# Flujo de Trabajo y Comandos Comunes

## Requisitos Previos
- [Ej. Node.js v18+, Docker, Python 3.10+]

## Entorno Local
1. Clonar repositorio.
2. Copiar `.env.example` a `.env`.
3. Instalar dependencias: `[comando de instalación]`
4. Levantar servicios (BD): `docker compose up -d`
5. Ejecutar en desarrollo: `[comando de dev]`

## Testing y Despliegue
- Ejecutar tests: `[comando de test]`
- Pipeline CI/CD: [Breve descripción de qué hace GitHub Actions / GitLab CI]
EOF

    crear_archivo_plantilla "docs/contexto/06-errores-conocidos.md" <<'EOF'
# Errores Conocidos y Soluciones (Troubleshooting)

*Registro de problemas comunes y cómo resolverlos rápidamente.*

- **Error**: `[Mensaje de error común]`
  - **Causa**: [Por qué ocurre]
  - **Solución Temporal / Definitiva**: [Qué comando ejecutar o qué archivo modificar para arreglarlo]

- **Error**: Fallo de conexión a la BD en Docker.
  - **Causa**: El contenedor tarda en levantar.
  - **Solución**: Reiniciar la API o añadir un script de `wait-for-it`.
EOF

    if [ ! -f "README.md" ]; then
        cat > "README.md" <<EOF
# ${PROYECTO}

> **Nota para IAs y Desarrolladores:** Este proyecto utiliza MDD (Memory-Driven Development). Por favor, lee la carpeta \`docs/contexto/\` antes de realizar cambios estructurales.

## Descripción
[Breve descripción de lo que hace el proyecto y qué problema resuelve, aplicando la regla #1: Por qué existe].

## Estructura de Documentación
El contexto detallado vive en \`/docs/contexto/\`:
1. [Arquitectura](./docs/contexto/01-arquitectura.md)
2. [Convenciones](./docs/contexto/02-convenciones.md)
3. [Decisiones (ADRs)](./docs/contexto/03-decisiones.md)
4. [Glosario](./docs/contexto/04-glosario.md)
5. [Flujo de Trabajo](./docs/contexto/05-flujo-de-trabajo.md)
6. [Errores Conocidos](./docs/contexto/06-errores-conocidos.md)

## Inicio Rápido
Consulta el [Flujo de Trabajo](./docs/contexto/05-flujo-de-trabajo.md) para levantar el proyecto en tu máquina local.
EOF
        ok "Creado README.md base"
    fi
elif [ ! -d "docs/contexto" ]; then
    aviso "Este proyecto aún no tiene docs/contexto/. Puedes:"
    printf '    - Ejecutar "context-init --plantilla" para crear los 6 archivos base, o\n'
    printf '    - Pedirle al agente: "Audita el proyecto y genera la carpeta docs/contexto/ con los 6 archivos .md"\n'
fi

# 5. Verificar/registrar el proyecto en el servidor MCP de la Mac Mini
llamar_mcp() {
    local payload="$1"
    curl -sS --max-time 5 -X POST "$MCP_URL" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "$payload" 2>/dev/null || true
}

escapar_json() {
    awk 'BEGIN { ORS=""; print "\"" }
    {
        gsub(/\\/, "\\\\")
        gsub(/"/, "\\\"")
        gsub(/\t/, "\\t")
        gsub(/\r/, "\\r")
        if (NR > 1) printf "\\n"
        printf "%s", $0
    }
    END { print "\"" }'
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
