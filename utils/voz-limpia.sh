#!/usr/bin/env bash
# Abre o cierra la utilidad gráfica de limpieza de voz con IA y comparador A/B (SUPER + A).
# También admite pasar un archivo por argumento desde la terminal: voz-limpia [archivo].

PIDFILE="/tmp/voz_limpia_${USER}.pid"
LOG="/tmp/voz_limpia_${USER}.log"
SCRIPT_PY="$HOME/dotfiles/utils/voz-limpia.py"

# Si no se pasó archivo por argumento y la ventana ya está abierta, cerrarla (toggle)
if [[ $# -eq 0 && -f "$PIDFILE" ]]; then
    pid=$(<"$PIDFILE")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        rm -f "$PIDFILE"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

ejecutar_gui() {
    if command -v voz-limpia-bin >/dev/null 2>&1; then
        exec voz-limpia-bin "$@"
    fi

    # Si aún no se ha corrido nix-switch para crear el binario `voz-limpia-bin`,
    # reutiliza el entorno Python + GTK3 + Cairo ya instalado para `multimedia` o `calendario`.
    local ref_bin python_gtk
    ref_bin=$(command -v multimedia 2>/dev/null || command -v calendario 2>/dev/null || true)
    if [[ -n "$ref_bin" && -f "$ref_bin" ]]; then
        eval "$(grep '^export ' "$ref_bin")"
        python_gtk=$(awk '/^exec / { print $2 }' "$ref_bin")
        if [[ -n "$python_gtk" && -x "$python_gtk" ]]; then
            exec "$python_gtk" "$SCRIPT_PY" "$@"
        fi
    fi

    exec python3 "$SCRIPT_PY" "$@"
}

ejecutar_gui "$@" >"$LOG" 2>&1 &
echo $! >"$PIDFILE"
disown
