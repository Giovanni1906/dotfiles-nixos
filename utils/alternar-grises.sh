#!/usr/bin/env bash
# Toggle de escala de grises vía shader GLSL del compositor (Hyprland misc:screen_shader).
# Uso: alternar-grises.sh [on|off]  — sin argumento alterna el estado actual.
set -euo pipefail

SHADER="$HOME/dotfiles/config/hypr/shaders/escala-grises.glsl"
ESTADO="$HOME/.local/state/dotfiles/grises.state"
mkdir -p "$(dirname "$ESTADO")"

estado_actual() {
    [ -f "$ESTADO" ] && cat "$ESTADO" || echo "off"
}

activar() {
    hyprctl keyword misc:screen_shader "$SHADER" > /dev/null
    echo "on" > "$ESTADO"
    notify-send -a sistema -i preferences-color "Escala de grises activada" "Pantalla en modo enfoque sin color"
}

desactivar() {
    hyprctl keyword misc:screen_shader "[[EMPTY]]" > /dev/null
    echo "off" > "$ESTADO"
    notify-send -a sistema -i preferences-color "Escala de grises desactivada" "Pantalla con colores normales"
}

case "${1:-toggle}" in
    on)  activar ;;
    off) desactivar ;;
    toggle)
        if [ "$(estado_actual)" = "on" ]; then
            desactivar
        else
            activar
        fi
        ;;
    *)
        echo "Uso: $(basename "$0") [on|off|toggle]" >&2
        exit 1
        ;;
esac
