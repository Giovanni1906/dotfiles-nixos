#!/usr/bin/env bash
# Comparte el escritorio por VNC solo en la red de Tailscale (alias: remote-conexion).
# Sin contraseña: solo llegan los dispositivos de la tailnet, y la VPN cifra la conexión.
# Desde el celular (AVNC): Tailscale activo y conectar a <IP de Tailscale de este equipo>:5900.
set -euo pipefail

# Evitar instancias duplicadas del propio script o de wayvnc del mismo usuario
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/wayvnc-tailscale.lock"
exec 9>"$LOCK_FILE"
flock -n 9 || { echo "WayVNC ya está gestionado por otra instancia"; exit 0; }

# Tras el arranque o login la red puede tardar, y `tailscale ip -4` puede devolver la IP
# un segundo antes de que el kernel la asigne a `tailscale0` (causando fallo en bind).
# Además, si wayvnc sale (por reinicio de red o al cambiar del greeter a la sesión),
# el bucle vuelve a esperar y reintentar mientras la sesión Wayland siga activa.
avisado=0
notificado_escucha=0

while true; do
    # Si la sesión Wayland terminó, salir limpiamente
    if [ -n "${WAYLAND_DISPLAY:-}" ] && [ -n "${XDG_RUNTIME_DIR:-}" ] && [ ! -S "${XDG_RUNTIME_DIR}/${WAYLAND_DISPLAY}" ]; then
        exit 0
    fi

    ip=$(ip -4 -o addr show dev tailscale0 2> /dev/null | awk '{split($4, a, "/"); print a[1]; exit}' || true)
    if [ -z "$ip" ]; then
        if [ "$avisado" -eq 0 ]; then
            notify-send "WayVNC" "Esperando la IP de Tailscale para compartir el escritorio" 2> /dev/null || true
            avisado=1
        fi
        sleep 2
        continue
    fi

    if [ "$notificado_escucha" -eq 0 ]; then
        notify-send "WayVNC" "Escuchando en ${ip}:5900" 2> /dev/null || true
        notificado_escucha=1
    fi

    wayvnc "$ip" 5900 2> /dev/null || true
    sleep 1
done
