#!/usr/bin/env bash
# Abre o cierra el calendario flotante del reloj.
# El programa `calendario` lo instala nixos/modulos/escritorio.nix (nix-switch).

PIDFILE="/tmp/calendario_${USER}.pid"
LOG="/tmp/calendario_${USER}.log"

cerrar() {
    local pid="$1"
    kill "$pid" 2>/dev/null || true
    pkill -P "$pid" 2>/dev/null || true
    rm -f "$PIDFILE"
}

if [[ -f "$PIDFILE" ]]; then
    pid=$(<"$PIDFILE")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        cerrar "$pid"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

if ! command -v calendario >/dev/null 2>&1; then
    notify-send "Calendario" "Falta activarlo en el sistema: nix-switch. Después reinicia Waybar."
    exit 1
fi

calendario >"$LOG" 2>&1 &
echo $! >"$PIDFILE"
disown
