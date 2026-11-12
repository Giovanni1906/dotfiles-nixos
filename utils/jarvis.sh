#!/usr/bin/env bash
# =============================================================================
# Jarvis Voice Assistant Launcher (SUPER + SPACE)
# =============================================================================
# Activa el asistente de voz Jarvis con bola de energía flotante en Hyprland.
# - Primer toque (SUPER + SPACE): inicia la escucha y muestra la bola de energía.
# - Segundo toque (SUPER + SPACE o Espacio): finaliza la escucha y procesa la orden.
# - Escape o clic: cancela o cierra.

PIDFILE="/tmp/jarvis_${USER}.pid"
STOPFILE="/tmp/jarvis_${USER}.stop"
LOG="/tmp/jarvis_${USER}.log"
SCRIPT_PY="$HOME/dotfiles/utils/jarvis.py"

# Si ya está corriendo, enviar señal de terminación de escucha (toggle)
if [[ -f "$PIDFILE" ]]; then
    pid=$(<"$PIDFILE")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        touch "$STOPFILE"
        kill -USR1 "$pid" 2>/dev/null || true
        exit 0
    fi
    rm -f "$PIDFILE" "$STOPFILE"
fi

ejecutar_jarvis() {
    # Reutiliza el entorno Python + GTK3 + GtkLayerShell configurado en NixOS
    local cal_bin python_gtk
    cal_bin=$(command -v calendario 2>/dev/null || true)
    if [[ -n "$cal_bin" && -f "$cal_bin" ]]; then
        eval "$(grep '^export ' "$cal_bin")"
        python_gtk=$(awk '/^exec / { print $2 }' "$cal_bin")
        if [[ -n "$python_gtk" && -x "$python_gtk" ]]; then
            exec "$python_gtk" "$SCRIPT_PY" "$@"
        fi
    fi

    # Fallback con python3 directo si tiene los typelibs en el entorno
    exec python3 "$SCRIPT_PY" "$@"
}

ejecutar_jarvis >"$LOG" 2>&1 &
echo $! >"$PIDFILE"
disown
