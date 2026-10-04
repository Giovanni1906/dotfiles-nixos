#!/usr/bin/env bash
# Muestra en Rofi la lista de atajos de utils/atajos.txt (SUPER + F1). Escribir filtra la lista.

ATAJOS_FILE="$HOME/dotfiles/utils/atajos.txt"

# Colores de powermenu.sh, con fondo casi opaco para que la lista se lea sobre cualquier ventana
MORADO="#3399cc"
FONDO="rgba(10, 30, 60, 0.95)"
BORDE="rgba(19, 62, 124, 0.2)"
TEXTO="#3399cc"
FONDO_SELECT="rgba(19, 62, 124, 0.9)"
FUENTE="JetBrainsMono Nerd Font 11"

# Alinea las columnas "Sección | Atajo | Descripción" ignorando comentarios y líneas vacías
LISTA=$(awk -F'|' '
    /^[[:space:]]*(#|$)/ { next }
    {
        for (i = 1; i <= 3; i++) gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
        printf "%-10s %-28s %s\n", $1, $2, $3
    }' "$ATAJOS_FILE")

printf '%s\n' "$LISTA" | rofi -dmenu -i -p "Atajos" -no-custom \
-theme-str "window { location: center; anchor: center; width: 55%; border: 2px; border-color: $BORDE; border-radius: 10px; background-color: $FONDO; padding: 15px; }" \
-theme-str "inputbar { children: [prompt, entry]; spacing: 10px; padding: 8px; text-color: $TEXTO; background-color: transparent; }" \
-theme-str "prompt, entry { text-color: $TEXTO; background-color: transparent; }" \
-theme-str "listview { lines: 18; scrollbar: false; background-color: transparent; margin: 0; }" \
-theme-str "element { padding: 6px 10px; border-radius: 5px; background-color: transparent; }" \
-theme-str "element normal.normal, element alternate.normal { background-color: transparent; }" \
-theme-str "element selected.normal { background-color: $FONDO_SELECT; border: 1px; border-color: $MORADO; }" \
-theme-str "element-text { font: \"$FUENTE\"; text-color: $TEXTO; background-color: transparent; }" \
> /dev/null
