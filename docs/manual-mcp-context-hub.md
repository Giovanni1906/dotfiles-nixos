# Manual: Cómo Conectar Cualquier Proyecto o Agente Nuevo a `context-hub`

Este manual explica cómo agregar un proyecto nuevo o un agente nuevo para que **Antigravity**, **Cursor**, **Claude Code**, **Hermes** y **Codex** compartan exactamente el mismo contexto y memoria desde tu Mac Mini (`CONTEXT_HUB_URL` en `~/dotfiles/.env`).

---

## 1. Conectar un Proyecto Nuevo (1 solo comando)

Párate en la raíz de cualquier repositorio nuevo o existente y ejecuta:

```bash
~/dotfiles/utils/context-init.sh
# (o usando el alias: context-init)

# Si además quieres crear de una vez las 6 plantillas vacías en docs/contexto/:
context-init --plantilla
```

### ¿Qué hace `context-init` automáticamente por ti?
1. **Si tenías un `CLAUDE.md` o `.cursor/rules/` previo**, rescata sus reglas para no perder nada.
2. **Crea `AGENTS.md`** en la raíz (leído nativamente por **Antigravity, Cursor, Hermes y Codex**).
3. **Crea el symlink `CLAUDE.md -> AGENTS.md`** (para que **Claude Code** lea el mismo archivo sin duplicar).
4. **Crea `.cursor/rules/context-hub.mdc`** (para **Cursor**).
5. **Si pasas `--plantilla` (`-p`)**, crea los 6 archivos base en `docs/contexto/` (`01-arquitectura.md` a `06-errores-conocidos.md`) y el `README.md` (si no existían).
6. **Conecta con la Mac Mini (`$CONTEXT_HUB_URL`)** y registra el proyecto en `~/context-hub/data/projects/<nombre-proyecto>/` creando su `rules.md` y `memory.md`.

---

## 2. Manual Práctico: Prompts de Arranque y Día a Día

Como las **Reglas Globales (`data/global.md`)** del MCP `context-hub` ya incluyen el **Marco de 5 Pasos** y las **6 Plantillas Maestras de `docs/contexto/`**, ya no necesitas copiar y pegar `docs-y-filosofia.mdc` a mano en cada proyecto. Solo corre `context-init` y háblale a cualquier agente (**Cursor**, **Claude Code**, **Antigravity**, **Hermes**) con estos prompts:

### Prompts de Arranque / Auditoría

**Si el proyecto es NUEVO:**
> "Voy a crear [Descripción de tu idea, ej. un microservicio en Go]. Inicializa el proyecto creando la carpeta `docs/contexto/` con sus 6 archivos `.md` y el `README.md`, aplicando el marco de 5 pasos a la arquitectura inicial."

**Si el proyecto YA EXISTE (y aún no tiene `docs/contexto/`):**
> "Audita el proyecto. Lee todo el código actual y genera la carpeta `docs/contexto/` con los 6 archivos `.md` basados en cómo está construido el sistema hoy."

### Cómo pedir cosas día a día (Marco de 5 Pasos: Preguntar → Eliminar → Simplificar → Acelerar → Automatizar)

**Cuando quieras agregar un feature (Regla de 'Preguntar y Eliminar'):**
> "Quiero implementar [Feature]. Antes de escribir código, aplica los primeros 3 pasos del marco: cuestióname si es necesario, qué podemos eliminar de la idea original y cómo la simplificamos. Dame tus preguntas primero."

**Cuando encuentres un bug (Regla del documento vivo):**
> "Tengo este error: [Pegar error]. Analízalo. Si lo resolvemos, asegúrate de actualizar `06-errores-conocidos.md` con la solución."

**Cuando quieras refactorizar o escalar (Regla de 'Acelerar y Automatizar'):**
> "Refactoriza este flujo. Aplica el paso 4 y 5 del marco. Si esto cambia la arquitectura, actualiza `01-arquitectura.md` y redacta un nuevo ADR en `03-decisiones.md`."

---

## 3. ¿Qué pasa si instalas un Agente Nuevo (Hermes, Codex, Windsurf, etc.)?

Cuando instalas un agente nuevo en tu PC, hay dos partes:
1. **El archivo del proyecto (`AGENTS.md`):** **No tienes que hacer nada en tus proyectos.** Casi todos los agentes modernos (Antigravity, Cursor, Hermes, OpenAI Codex, Windsurf, Zed, etc.) adoptaron el estándar `AGENTS.md` en la raíz del repositorio (y Claude Code usa `CLAUDE.md`, que ya está enlazado a `AGENTS.md`).
2. **La conexión al servidor MCP:** Sí debes decirle al nuevo agente una sola vez (a nivel global de tu usuario) dónde está la URL definida en `CONTEXT_HUB_URL` (dentro de `~/dotfiles/.env`).

### Agentes que `nixos/modulos/ia.nix` ya configura automáticamente:

| Agente | Archivo global que `ia.nix` configura | Cómo añadirlo manualmente si hace falta |
|---|---|---|
| **Antigravity (`agy`)** | `~/.gemini/config/mcp_config.json` | Ya automático en `ia.nix` (usando `.env`) |
| **Cursor** | `~/.cursor/mcp.json` | Ya automático en `ia.nix` (usando `.env`) |
| **Claude Code (`claude`)** | `~/.claude.json` | `claude mcp add --transport http --scope user context-hub "$CONTEXT_HUB_URL"` (ya automático en `ia.nix`) |
| **Claude Desktop** | `~/.config/Claude/claude_desktop_config.json` | Ya automático en `ia.nix` (usando `.env`) |
| **Hermes (`hermes`)** | `~/.hermes/config.yaml` | `hermes mcp add --url "$CONTEXT_HUB_URL" context-hub` (ya automático en `ia.nix`) |
| **Codex CLI (`codex`)** | `~/.codex/config.toml` | Bloque `[mcp_servers.context-hub]` con `url = "$CONTEXT_HUB_URL"` (ya automático en `ia.nix`) |

Si en el futuro pruebas otro agente distinto, solo buscas su opción global de MCP y le pones la URL Streamable HTTP de tu `.env` (`CONTEXT_HUB_URL`).
