#!/usr/bin/env bash
# Muestra en Rofi la lista de atajos de utils/atajos.txt (SUPER + F1). Escribir filtra la lista.

ATAJOS_FILE="$HOME/dotfiles/utils/atajos.txt"

# Colores, fuente y forma vienen del tema de Rofi (tema/tema.conf); aquí solo se ajusta el tamaño.

# Alinea las columnas "Sección | Atajo | Descripción" ignorando comentarios y líneas vacías
LISTA=$(awk -F'|' '
    /^[[:space:]]*(#|$)/ { next }
    {
        for (i = 1; i <= 3; i++) gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
        printf "%-10s %-28s %s\n", $1, $2, $3
    }' "$ATAJOS_FILE")

printf '%s\n' "$LISTA" | rofi -dmenu -i -p "Atajos" -no-custom \
-theme-str "window { width: 55%; }" \
-theme-str "mainbox { children: [inputbar, listview]; }" \
-theme-str "listview { lines: 18; }" \
-theme-str "element { padding: 6px 10px; }" \
> /dev/null
