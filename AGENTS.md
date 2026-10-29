# Contexto Unificado — `dotfiles`

> **Instrucción obligatoria para todos los agentes (Cursor, Claude Code, Antigravity):**
> 1. Al comenzar cualquier tarea o conversación en este repositorio, llama **primero** a la herramienta MCP `get_project_context(project_name="dotfiles")` del servidor `context-hub` (definido en `CONTEXT_HUB_URL` dentro de `.env`).
> 2. Revisa `docs/contexto/` antes de cambios estructurales y mantenlo actualizado (Memory-Driven Development).
> 3. Cuando resuelvas un bug no obvio o tomes una decisión importante, regístrala en la memoria compartida usando `append_project_memory(project_name="dotfiles", category="...", note="...")`.

---

## Resumen de Respaldo (Offline / Sin Tailscale)

Si el servidor MCP `context-hub` no está accesible temporalmente, aplica estas reglas esenciales:

### 1. Lista de atajos (`utils/atajos.txt`)
- `utils/atajos.txt` es la única lista de atajos del proyecto (`SUPER + F1` / `utils/atajos.sh`).
- Si un cambio añade, quita o modifica un atajo en `config/hypr/hyprland.conf` (`bind*`), `config/kitty/kitty.conf` (`map`) o `config/waybar/config` (`on-click*`/`on-scroll*`), actualizar `utils/atajos.txt` en el mismo cambio.
- Formato: `Sección | Atajo | Descripción [| Comando]` (en español, verbo en infinitivo; mantener orden Hyprland, Kitty, Waybar).

### 2. Tablero kanban del proyecto (Notion)
- Tablero **nixos**: https://app.notion.com/p/nixos-3f0bf08bb2f880849364ea3f4cb40c2d
- Data source (para el MCP de Notion): `collection://3f0bf08b-b2f8-807b-8142-000b0ca5a3e8`
- Estados: `Not started` → `In progress` → `In revision` → `Done` (nunca pasar a `Done`, lo hace el usuario).
- Contenido de tarjeta: **Diagnóstico**, **Pasos** (to-dos) y **Verificación**.
- Commits por función en español (`feat:`, `fix:`, `docs:`, `refactor:`; ver `docs/contexto/02-convenciones.md`).
