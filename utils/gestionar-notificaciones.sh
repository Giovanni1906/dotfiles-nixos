#!/usr/bin/env bash
# Gestiona qué categorías de notificaciones están activas (SUPER + F4).
# Abre un menú Rofi con checkboxes; el cambio se aplica al instante en Mako.
#
# --solo-reglas  Solo escribe las reglas en la config de Mako sin abrir Rofi.
#                Llamado por utils/aplicar-tema.sh tras regenerar la config.
#
# Categorías:
#   ia       → notificaciones de Claude Code, Agy, Cursor y Hermes (app-name=ia)
#   sistema  → todas las demás apps (usa mode=ocultas internamente)
#
# Estado persistente en: ~/.config/mako/notif-estado.state

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ESTADO="$HOME/.config/mako/notif-estado.state"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/mako/config"
MARCA_INI="# FILTROS-NOTIF:INI"
MARCA_FIN="# FILTROS-NOTIF:FIN"

# ------------------------------------------------------------------
# Helpers de estado
# ------------------------------------------------------------------
init_estado() {
    mkdir -p "$(dirname "$ESTADO")"
    [ -f "$ESTADO" ] || printf 'ia=1\nsistema=1\n' > "$ESTADO"
}

get_val() {
    grep "^${1}=" "$ESTADO" 2>/dev/null | cut -d= -f2 || echo 1
}

set_val() {
    local k="$1" v="$2"
    if grep -q "^${k}=" "$ESTADO" 2>/dev/null; then
        sed -i "s|^${k}=.*|${k}=${v}|" "$ESTADO"
    else
        echo "${k}=${v}" >> "$ESTADO"
    fi
}

toggle_val() {
    local actual
    actual=$(get_val "$1")
    [ "$actual" = "1" ] && set_val "$1" 0 || set_val "$1" 1
}

# ------------------------------------------------------------------
# Reglas dinámicas en la config de Mako
# ------------------------------------------------------------------
escribir_reglas() {
    [ ! -f "$CONFIG" ] && return 0

    # Eliminar sección dinámica previa
    sed -i "/^${MARCA_INI}$/,/^${MARCA_FIN}$/d" "$CONFIG"

    local ia sistema
    ia=$(get_val ia)
    sistema=$(get_val sistema)

    {
        echo ""
        echo "$MARCA_INI"

        # IA visible dentro del mode=ocultas (caso "solo IA")
        if [ "$ia" = "1" ]; then
            printf '[mode=ocultas app-name=ia]\ninvisible=0\n\n'
        fi

        # IA bloqueada (caso "solo Sistema" o "todo oculto")
        if [ "$ia" = "0" ]; then
            printf '[app-name=ia]\ninvisible=1\n\n'
        fi

        echo "$MARCA_FIN"
    } >> "$CONFIG"
}

aplicar_modo_ocultas() {
    command -v makoctl >/dev/null 2>&1 || return 0
    makoctl mode >/dev/null 2>&1 || return 0

    local sistema
    sistema=$(get_val sistema)
    local modos_activos
    modos_activos=$(makoctl mode 2>/dev/null | tr '\n' ' ')

    if [ "$sistema" = "0" ]; then
        echo "$modos_activos" | grep -qw ocultas \
            || makoctl mode -a ocultas >/dev/null 2>&1 || true
    else
        echo "$modos_activos" | grep -qw ocultas \
            && makoctl mode -r ocultas >/dev/null 2>&1 || true
    fi
}

aplicar_todo() {
    escribir_reglas
    makoctl reload 2>/dev/null || true
    aplicar_modo_ocultas
}

# ------------------------------------------------------------------
# Modo --solo-reglas (sin Rofi, para aplicar-tema.sh)
# ------------------------------------------------------------------
if [ "${1:-}" = "--solo-reglas" ]; then
    init_estado
    escribir_reglas
    exit 0
fi

# ------------------------------------------------------------------
# Verificaciones previas al menú
# ------------------------------------------------------------------
if ! command -v makoctl >/dev/null 2>&1; then
    notify-send -u critical "Notificaciones" "Mako no disponible" 2>/dev/null || true
    exit 1
fi
if ! makoctl mode >/dev/null 2>&1; then
    notify-send -u critical "Notificaciones" "Mako no está en marcha" 2>/dev/null || true
    exit 1
fi
if [ ! -f "$CONFIG" ]; then
    notify-send -u critical "Notificaciones" "Falta config de Mako. Ejecuta tema-aplicar." 2>/dev/null || true
    exit 1
fi

init_estado

# Asegurar que las reglas base del modo=ocultas están en el config
if ! grep -q '^\[mode=ocultas\]$' "$CONFIG"; then
    cat >> "$CONFIG" <<'EOF'

[mode=ocultas]
invisible=1

[mode=ocultas app-name=Notificaciones]
invisible=0
EOF
    makoctl reload >/dev/null 2>&1 || true
fi

# ------------------------------------------------------------------
# Selector de voz neuronal (Piper TTS)
# ------------------------------------------------------------------
elegir_voz() {
    local piper_dir="${XDG_DATA_HOME:-$HOME/.local/share}/piper"
    local config_voz="${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/voz.conf"
    mkdir -p "$(dirname "$config_voz")"

    local opciones=(
        "Claude (Latino neutro — Femenina natural)"
        "Ald (Latino — Masculina)"
        "Sharvard (España — Femenina natural)"
        "Dave (España — Masculina)"
        "Espeak (Robótica sintética)"
    )

    local sel
    sel=$(printf '%s\n' "${opciones[@]}" \
        | rofi -dmenu -i -p "Elegir voz" -format i \
            -theme-str 'window { width: 500px; }' 2>/dev/null) || return 0

    case "$sel" in
        0) echo "modelo=$piper_dir/es_MX-claude-high.onnx" > "$config_voz" ;;
        1) echo "modelo=$piper_dir/es_MX-ald-medium.onnx" > "$config_voz" ;;
        2) echo "modelo=$piper_dir/es_ES-sharvard-medium.onnx" > "$config_voz" ;;
        3) echo "modelo=$piper_dir/es_ES-davefx-medium.onnx" > "$config_voz" ;;
        4) echo "modelo=" > "$config_voz" ;;
    esac

    "$SCRIPT_DIR/voz.sh" --silencio "Voz seleccionada correctamente" 2>/dev/null &
}

# ------------------------------------------------------------------
# Menú Rofi interactivo (loop hasta Escape)
# ------------------------------------------------------------------
icono() { [ "$(get_val "$1")" = "1" ] && echo "✓" || echo "✗"; }

ITEMS=(
    ""                                           # 0: IA (texto dinámico, se rellena en el loop)
    ""                                           # 1: Sistema (ídem)
    "───────────────────────────────────"        # 2: separador
    "  Cambiar voz TTS (Piper neuronal)"         # 3: selector de voz
    "───────────────────────────────────"        # 4: separador
    "  Mostrar todo"                             # 5
    "  Ocultar todo"                             # 6
)

while true; do
    ITEMS[0]="$(icono ia)  IA — Claude Code · Agy · Cursor · Hermes"
    ITEMS[1]="$(icono sistema)  Sistema — todas las demás apps"

    indice=$(printf '%s\n' "${ITEMS[@]}" \
        | rofi -dmenu -i -p "Notificaciones" -no-custom -format i \
            -theme-str 'window { width: 500px; }' 2>/dev/null) || break

    case "$indice" in
        0) toggle_val ia;      aplicar_todo ;;
        1) toggle_val sistema; aplicar_todo ;;
        2) continue ;;  # separador
        3) elegir_voz ;;
        4) continue ;;  # separador
        5) set_val ia 1; set_val sistema 1; aplicar_todo ;;
        6) set_val ia 0; set_val sistema 0; aplicar_todo ;;
        *) break ;;
    esac
done

# Notificación de estado al cerrar
ia=$(get_val ia); sistema=$(get_val sistema)
if   [ "$ia" = "1" ] && [ "$sistema" = "1" ]; then MSG="Todo visible"
elif [ "$ia" = "1" ] && [ "$sistema" = "0" ]; then MSG="Solo IA visible"
elif [ "$ia" = "0" ] && [ "$sistema" = "1" ]; then MSG="IA oculta"
else                                                MSG="Todo oculto"
fi
notify-send -a Notificaciones -t 4000 "Notificaciones" "$MSG" 2>/dev/null || true
