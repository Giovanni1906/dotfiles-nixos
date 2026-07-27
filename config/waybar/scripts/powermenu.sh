# Configuración de colores y estilo
MORADO="#3399cc" 
FONDO="rgba(19, 62, 124, 0.4)"
BORDE="rgba(19, 62, 124, 0.2)"
TEXTO="#3399cc"
FONDO_SELECT="rgba(10, 30, 60, 0.95)" 
TEXTO_SELECT="#cdd6f4" 

# Quitamos el -p "Sistema:" y apagamos el inputbar
chosen=$(printf " Apagar\n Reiniciar\n Suspender\n Cerrar Sesión" | rofi -dmenu -i \
-theme-str "window { location: center; anchor: center; width: 20%; border: 2px; border-color: $BORDE; border-radius: 10px; background-color: $FONDO; padding: 15px; }" \
-theme-str "inputbar { enabled: false; }" \
-theme-str "listview { lines: 4; scrollbar: false; background-color: transparent; margin: 0; }" \
-theme-str "element { padding: 15px 10px; border-radius: 5px; background-color: transparent; }" \
-theme-str "element normal.normal, element alternate.normal { background-color: transparent; }" \
-theme-str "element selected.normal { background-color: $FONDO_SELECT; border: 1px; border-color: $MORADO; }" \
-theme-str "element-text { text-color: $TEXTO; background-color: transparent; }" \
-theme-str "element-text selected { text-color: $TEXTO; background-color: transparent; }"
)

case "$chosen" in
    " Apagar") poweroff ;;
    " Reiniciar") reboot ;;
    " Suspender") systemctl suspend ;;
    " Cerrar Sesión") hyprctl dispatch exit ;;
esac
