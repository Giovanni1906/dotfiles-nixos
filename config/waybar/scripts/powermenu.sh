# Rofi-Powermenu/powermenu.sh at main - GitHub https://github.com/w8ste/Rofi-Powermenu/blob/main/powermenu.sh

# Configuración de colores y estilo
MORADO="#3399cc"
FONDO="rgba(19, 62, 124, 0.95)"
BORDE="rgba(19, 62, 124, 0.2)"
TEXTO="#3399cc"
TEXTO_REFERENCIA="rgba(205,214,244,0.6)"
TEXTO_SELECT="#133e7c"
FONDO_SELECT="rgba(19,62,124)"

chosen=$(printf " Apagar\n Reiniciar\n Suspender\n Cerrar Sesión" | rofi -dmenu -i -p "Sistema:" \
-theme-str "prompt { color: $TEXTO; }" \
-theme-str "window { width: 12%; border: 2px; border-color: $BORDE; border-radius: 10px; background-color: $FONDO; }" \
-theme-str "entry { text-color: $TEXTO; placeholder: 'text'; placeholder-color: $TEXTO_REFERENCIA; margin: 0 0 0 10px; }" \
-theme-str "listview { lines: 4; scrollbar: false; }" \
-theme-str "element { padding: 8px; border-radius: 5px; }" \
-theme-str "element selected { background-color: $FONDO; text-color: $FONDO; }" \
-theme-str "element normal.normal, element alternate.normal { background-color: transparent; border-color: $MORADO; }" \
-theme-str "element selected.normal { background-color: transparent; border: 1px; border-color: $MORADO; }" \
-theme-str "element-text { text-color: $TEXTO; }" \
-theme-str "element-text selected {text-color: $TEXTO; }"
)

case "$chosen" in
    " Apagar") poweroff ;;
    " Reiniciar") reboot ;;
    " Suspender") systemctl suspend ;;
    " Cerrar Sesión") hyprctl dispatch exit ;;
esac
