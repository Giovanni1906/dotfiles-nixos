#!/usr/bin/env bash
# Menú de apagado (SUPER + X).
# Colores y forma vienen del tema de Rofi (tema/tema.conf); aquí solo se ajusta el tamaño.

# Sin barra de búsqueda: solo la lista
chosen=$(printf " Apagar\n Reiniciar\n Suspender\n Cerrar Sesión" | rofi -dmenu -i \
-theme-str "window { width: 20%; }" \
-theme-str "mainbox { children: [listview]; }" \
-theme-str "listview { lines: 4; }" \
-theme-str "element { padding: 15px 10px; }"
)

case "$chosen" in
    " Apagar") poweroff ;;
    " Reiniciar") reboot ;;
    " Suspender") systemctl suspend ;;  # hypridle bloquea con hyprlock antes de dormir
    " Cerrar Sesión") hyprctl dispatch exit ;;
esac
