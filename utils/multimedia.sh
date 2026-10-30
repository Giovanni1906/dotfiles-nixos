#!/usr/bin/env bash
# Abre o cierra la utilidad gráfica de descargas (yt-dlp) y conversión (ffmpeg) con SUPER + D.
# Usa el entorno GTK3/PyGObject del sistema (módulo escritorio.nix).

PIDFILE="/tmp/multimedia_${USER}.pid"
LOG="/tmp/multimedia_${USER}.log"
SCRIPT_PY="$HOME/dotfiles/utils/multimedia.py"

if [[ -f "$PIDFILE" ]]; then
    pid=$(<"$PIDFILE")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        rm -f "$PIDFILE"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

ejecutar_gui() {
    if command -v multimedia >/dev/null 2>&1; then
        exec multimedia
    fi

    # Si aún no se ha corrido nix-switch para crear el binario `multimedia`,
    # reutiliza el entorno Python + GTK3 ya instalado para `calendario`.
    local cal_bin python_gtk
    cal_bin=$(command -v calendario 2>/dev/null || true)
    if [[ -n "$cal_bin" && -f "$cal_bin" ]]; then
        eval "$(grep '^export ' "$cal_bin")"
        python_gtk=$(awk '/^exec / { print $2 }' "$cal_bin")
        if [[ -n "$python_gtk" && -x "$python_gtk" ]]; then
            exec "$python_gtk" "$SCRIPT_PY"
        fi
    fi

    exec python3 "$SCRIPT_PY"
}

ejecutar_gui >"$LOG" 2>&1 &
echo $! >"$PIDFILE"
disown
