#!/usr/bin/env bash
# Comparte el escritorio por VNC solo en la red de Tailscale (alias: remote-conexion).
# Sin contraseña: solo llegan los dispositivos de la tailnet, y la VPN cifra la conexión.
# Desde el celular (AVNC): Tailscale activo y conectar a <IP de Tailscale de este equipo>:5900.
set -euo pipefail

pidof wayvnc > /dev/null && { echo "WayVNC ya está corriendo"; exit 0; }

# Tras el login la red puede tardar más de un minuto. En pc-casa (2026-10-16) Hyprland
# arrancó a las 23:18 y la IP de Tailscale llegó a las 23:20: el tope de 60 s salía antes
# y exec-once no vuelve a lanzar el script. Por eso se espera sin límite.
avisado=0
while true; do
    ip=$(tailscale ip -4 2> /dev/null | head -n 1 || true)
    if [ -n "$ip" ]; then
        break
    fi
    if [ "$avisado" -eq 0 ]; then
        notify-send "WayVNC" "Esperando la IP de Tailscale para compartir el escritorio" 2> /dev/null || true
        avisado=1
    fi
    sleep 2
done

notify-send "WayVNC" "Escuchando en ${ip}:5900" 2> /dev/null || true
exec wayvnc "$ip" 5900
