#!/usr/bin/env bash
# Comparte el escritorio por VNC solo en la red de Tailscale (alias: remote-conexion).
# Sin contraseña: solo llegan los dispositivos de la tailnet, y la VPN cifra la conexión.
# Desde el celular (AVNC): Tailscale activo y conectar a <IP de Tailscale de este equipo>:5900.
set -euo pipefail

pidof wayvnc > /dev/null && { echo "WayVNC ya está corriendo"; exit 0; }

# Al iniciar sesión Tailscale puede tardar unos segundos en tener IP
for _ in $(seq 30); do
    ip=$(tailscale ip -4 2> /dev/null | head -n 1) && [ -n "$ip" ] && break
    sleep 2
done
if [ -z "${ip:-}" ]; then
    notify-send -u critical "WayVNC" "Tailscale no tiene IP: no se comparte el escritorio" 2> /dev/null || true
    echo "Tailscale no tiene IP (¿sudo tailscale up?): no se comparte el escritorio" >&2
    exit 1
fi

exec wayvnc "$ip" 5900
