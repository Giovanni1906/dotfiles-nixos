# Manual: Cómo Conectar Cualquier Proyecto o Agente Nuevo a `context-hub`

Este manual explica cómo agregar un proyecto nuevo o un agente nuevo para que **Antigravity**, **Cursor**, **Claude Code**, **Hermes** y **Codex** compartan exactamente el mismo contexto y memoria desde tu Mac Mini (`CONTEXT_HUB_URL` en `~/dotfiles/.env`).

---

## 1. Conectar un Proyecto Nuevo (1 solo comando)

Párate en la raíz de cualquier repositorio nuevo o existente y ejecuta:

```bash
~/dotfiles/utils/context-init.sh
# (o usando el alias tras reconstruir NixOS: context-init)
```

### ¿Qué hace `context-init` automáticamente por ti?
1. **Si tenías un `CLAUDE.md` previo**, rescata sus reglas para no perder nada.
2. **Crea `AGENTS.md`** en la raíz (leído nativamente por **Antigravity, Cursor, Hermes y Codex**).
3. **Crea el symlink `CLAUDE.md -> AGENTS.md`** (para que **Claude Code** lea el mismo archivo sin duplicar).
4. **Crea `.cursor/rules/context-hub.mdc`** (para **Cursor**).
5. **Conecta con la Mac Mini (`$CONTEXT_HUB_URL`)** y registra el proyecto en `~/context-hub/data/projects/<nombre-proyecto>/` creando su `rules.md` y `memory.md`.

---

## 2. ¿Qué pasa si instalas un Agente Nuevo (Hermes, Codex, Windsurf, etc.)?

Cuando instalas un agente nuevo en tu PC, hay dos partes:
1. **El archivo del proyecto (`AGENTS.md`):** **No tienes que hacer nada en tus proyectos.** Casi todos los agentes modernos (Antigravity, Cursor, Hermes, OpenAI Codex, Windsurf, Zed, etc.) adoptaron el estándar `AGENTS.md` en la raíz del repositorio (y Claude Code usa `CLAUDE.md`, que ya está enlazado a `AGENTS.md`).
2. **La conexión al servidor MCP:** Sí debes decirle al nuevo agente una sola vez (a nivel global de tu usuario) dónde está la URL definida en `CONTEXT_HUB_URL` (dentro de `~/dotfiles/.env`).

### Agentes que `nixos/modulos/ia.nix` ya configura automáticamente:

| Agente | Archivo global que `ia.nix` configura | Cómo añadirlo manualmente si hace falta |
|---|---|---|
| **Antigravity (`agy`)** | `~/.gemini/config/mcp_config.json` | Ya automático en `ia.nix` (usando `.env`) |
| **Cursor** | `~/.cursor/mcp.json` | Ya automático en `ia.nix` (usando `.env`) |
| **Claude Code (`claude`)** | `~/.claude.json` | `claude mcp add --transport http --scope user context-hub "$CONTEXT_HUB_URL"` (ya automático en `ia.nix`) |
| **Hermes (`hermes`)** | `~/.hermes/config.yaml` | `hermes mcp add --url "$CONTEXT_HUB_URL" context-hub` (ya automático en `ia.nix`) |
| **Codex CLI (`codex`)** | `~/.codex/config.toml` | Bloque `[mcp_servers.context-hub]` con `url = "$CONTEXT_HUB_URL"` (ya automático en `ia.nix`) |

Si en el futuro pruebas otro agente distinto, solo buscas su opción global de MCP y le pones la URL Streamable HTTP de tu `.env` (`CONTEXT_HUB_URL`).
