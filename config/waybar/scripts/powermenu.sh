#!/usr/bin/env bash
# Menú de apagado (SUPER + X).
# Colores y forma vienen del tema de Rofi (tema/tema.conf); aquí solo se ajusta el tamaño.

# Sin barra de búsqueda: solo la lista
chosen=$(printf " Apagar\n Reiniciar\n Bloquear\n Suspender\n Cerrar Sesión" | rofi -dmenu -i \
-theme-str "window { width: 20%; }" \
-theme-str "mainbox { children: [listview]; }" \
-theme-str "listview { lines: 5; }" \
-theme-str "element { padding: 15px 10px; }"
)

case "$chosen" in
    " Apagar") poweroff ;;
    " Reiniciar") reboot ;;
    " Bloquear")
        # Sin suspender: la red, WayVNC y lo que corre en segundo plano siguen activos
        if pidof hypridle > /dev/null; then
            loginctl lock-session
        else
            pidof hyprlock > /dev/null || hyprlock &
        fi ;;
    " Suspender")
        # hypridle bloquea antes de dormir; si no está corriendo, se bloquea aquí
        if ! pidof hypridle > /dev/null; then
            pidof hyprlock > /dev/null || { hyprlock & sleep 1; }
        fi
        systemctl suspend ;;
    " Cerrar Sesión") hyprctl dispatch exit ;;
esac
