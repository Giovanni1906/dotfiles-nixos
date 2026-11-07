#!/usr/bin/env bash
# Hook de notificación para agentes de IA.
# Detecta el proyecto activo y anuncia "Tarea terminada en <proyecto>" (voz + visual).
#
# Usado por:
#   - hook Stop de Claude Code (~/.claude/settings.json)
#   - alias de agy / hermes (nixos/modulos/ia.nix)
#
# El sonido siempre suena; la voz respeta un cooldown para no saturar
# en conversaciones largas. Ambos se saltan si no hay sesión de audio.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COOLDOWN_VOZ=20
TS_FILE="${XDG_CACHE_HOME:-$HOME/.cache}/ia-notificacion-ts"

# Cooldown para la voz (el sonido siempre suena)
ahora=$(date +%s)
hablar=1
if [ -f "$TS_FILE" ]; then
    ultimo=$(cat "$TS_FILE" 2>/dev/null || echo 0)
    (( ahora - ultimo < COOLDOWN_VOZ )) && hablar=0
fi

# Detectar nombre del proyecto desde git o carpeta actual
DIRECTORIO="${PWD:-$(pwd)}"
if git -C "$DIRECTORIO" rev-parse --show-toplevel >/dev/null 2>&1; then
    PROYECTO=$(basename "$(git -C "$DIRECTORIO" rev-parse --show-toplevel)")
else
    PROYECTO=$(basename "$DIRECTORIO")
fi
# Limpiar separadores para pronunciación natural
PROYECTO_VOZ=$(echo "$PROYECTO" | tr '-_' '  ')

# Notificación visual (app-name=ia para filtros de Mako)
notify-send -a ia -t 7000 -i utilities-terminal \
    "IA — $PROYECTO" "Tarea terminada" 2>/dev/null &

# Sonido siempre
"$SCRIPT_DIR/voz.sh" --sonido

# Voz si fuera del cooldown
if [ "$hablar" = "1" ]; then
    echo "$ahora" > "$TS_FILE"
    sleep 0.4
    "$SCRIPT_DIR/voz.sh" --silencio "Tarea terminada en $PROYECTO_VOZ"
fi

wait
