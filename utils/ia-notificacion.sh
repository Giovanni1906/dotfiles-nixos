#!/usr/bin/env bash
# Hook de notificación para agentes de IA.
# Detecta el proyecto activo y anuncia "Tarea terminada en <proyecto>" (voz + visual).
#
# Usado por:
#   - hook Stop de Claude Code (~/.claude/settings.json)
#   - hook Stop de Antigravity (~/.gemini/config/hooks.json)
#   - alias de agy / hermes (nixos/modulos/ia.nix)
#
# El sonido suena con un debounce mínimo de 3s para evitar disparos dobles (hook + alias).
# La voz respeta un cooldown de 20s para no saturar en conversaciones largas.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COOLDOWN_VOZ=20
DEBOUNCE_TOTAL=3
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}"
TS_TOTAL="$CACHE_DIR/ia-notificacion-total-ts"
TS_VOZ="$CACHE_DIR/ia-notificacion-voz-ts"

ahora=$(date +%s)

# Debounce total: evita doble notificación si el hook y el alias terminan a la vez (<3s)
ultimo_total=0
[ -f "$TS_TOTAL" ] && ultimo_total=$(cat "$TS_TOTAL" 2>/dev/null || echo 0)
if (( ahora - ultimo_total < DEBOUNCE_TOTAL )); then
    exit 0
fi
mkdir -p "$CACHE_DIR"
echo "$ahora" > "$TS_TOTAL"

# Cooldown para la voz (no repetir en menos de 20s)
ultimo_voz=0
[ -f "$TS_VOZ" ] && ultimo_voz=$(cat "$TS_VOZ" 2>/dev/null || echo 0)
hablar=1
(( ahora - ultimo_voz < COOLDOWN_VOZ )) && hablar=0

# Detectar nombre del proyecto desde contexto de IA (stdin) o directorio actual
DIRECTORIO=""
if [ ! -t 0 ]; then
    input=$(timeout 0.3 cat 2>/dev/null || true)
    if [ -n "$input" ]; then
        if command -v node >/dev/null 2>&1; then
            DIRECTORIO=$(node -e "
            let d = '';
            process.stdin.on('data', c => d += c);
            process.stdin.on('end', () => {
              try {
                const j = JSON.parse(d);
                const ws = (j.workspacePaths && j.workspacePaths[0])
                        || (j.workspace_roots && j.workspace_roots[0])
                        || j.cwd
                        || '';
                if (ws) console.log(ws);
              } catch(e){}
            });
            " <<< "$input" 2>/dev/null)
        fi
        # Respaldo rápido con grep si node no dio resultado
        if [ -z "$DIRECTORIO" ]; then
            DIRECTORIO=$(echo "$input" | grep -oP '"workspacePaths"\s*:\s*\[\s*"\K[^"]+' 2>/dev/null || true)
            [ -z "$DIRECTORIO" ] && DIRECTORIO=$(echo "$input" | grep -oP '"workspace_roots"\s*:\s*\[\s*"\K[^"]+' 2>/dev/null || true)
            [ -z "$DIRECTORIO" ] && DIRECTORIO=$(echo "$input" | grep -oP '"cwd"\s*:\s*"\K[^"]+' 2>/dev/null || true)
        fi
    fi
fi
[ -z "$DIRECTORIO" ] && DIRECTORIO="${PWD:-$(pwd)}"

if git -C "$DIRECTORIO" rev-parse --show-toplevel >/dev/null 2>&1; then
    PROYECTO=$(basename "$(git -C "$DIRECTORIO" rev-parse --show-toplevel)")
else
    PROYECTO=$(basename "$DIRECTORIO")
fi
# Limpiar separadores para pronunciación natural en bash puro
PROYECTO_VOZ="${PROYECTO//[-_]/ }"

# Notificación visual (app-name=ia para filtros de Mako)
notify-send -a ia -t 7000 -i utilities-terminal \
    "IA — $PROYECTO" "Tarea terminada" 2>/dev/null &

# Sonido
"$SCRIPT_DIR/voz.sh" --sonido

# Voz si fuera del cooldown
if [ "$hablar" = "1" ]; then
    echo "$ahora" > "$TS_VOZ"
    sleep 0.4
    "$SCRIPT_DIR/voz.sh" --silencio "Tarea terminada en $PROYECTO_VOZ"
fi

wait
