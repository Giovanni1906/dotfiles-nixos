#!/usr/bin/env bash
# Cambia el tamaño de fuente de la ventana de Kitty enfocada.
# Uso: kitty-zoom.sh +1 | -1   (lo llama Hyprland con CTRL + rueda del ratón)

PASO="${1:-+1}"

PID=$(hyprctl activewindow | awk '$1 == "pid:" {print $2}')
SOCKET="$XDG_RUNTIME_DIR/kitty-$PID"

# Si la ventana enfocada no es Kitty no hay socket: no hacer nada
[[ -S "$SOCKET" ]] || exit 0

kitty @ --to "unix:$SOCKET" set-font-size -- "$PASO"
