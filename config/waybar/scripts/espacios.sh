#!/usr/bin/env bash
# Números de workspace de Waybar con un tooltip que lista las ventanas de cada uno
# (el módulo nativo hyprland/workspaces no tiene tooltip en el número).
#   espacios.sh escuchar  -> módulo custom/workspaces (oculto): sigue los eventos de Hyprland,
#                            guarda el estado de los workspaces 1-10 y avisa a Waybar con una señal
#   espacios.sh <n>       -> módulo custom/workspace#<n>: JSON del workspace n
# Waybar exporta WAYBAR_OUTPUT_NAME: cada barra muestra solo los workspaces de su monitor.

ESTADO="/tmp/espacios_$USER"
SENAL=8          # "signal" de los módulos custom/workspace#<n> en config
MAX_TITULO=60    # Caracteres de cada título en el tooltip

declare -A URGENTES=()

# Escribe un archivo por workspace ("<monitor><TAB><json>", vacío si no existe) y avisa a Waybar si algo cambió
actualizar() {
    local activo salida n linea
    activo=$(hyprctl activeworkspace | awk 'NR == 1 { print $3 }')
    salida=$({ hyprctl workspaces; echo "@CLIENTES"; hyprctl clients; echo "@MONITORES"; hyprctl monitors; } | awk \
        -v activo="$activo" -v urgentes=" ${!URGENTES[*]} " -v max="$MAX_TITULO" '
        function texto(s) {
            if (length(s) > max) s = substr(s, 1, max - 1) "…"
            gsub(/[\001-\037]/, "", s)
            gsub(/&/, "\\&amp;", s); gsub(/</, "\\&lt;", s); gsub(/>/, "\\&gt;", s)
            gsub(/\\/, "\\\\", s); gsub(/"/, "\\\"", s)
            return s
        }
        function guardar() {
            if (ws >= 1 && ws <= 10) {
                ventanas[ws] = ventanas[ws] "\\n• " texto(titulo != "" ? titulo : clase)
                if (index(urgentes, " " dir " ")) urgente[ws] = 1
            }
            ws = 0
        }
        $0 == "@CLIENTES"  { seccion = "c"; next }
        $0 == "@MONITORES" { guardar(); seccion = "m"; next }
        seccion == "" && /^workspace ID / { sub(/:$/, "", $NF); monitor[$3] = $NF }
        seccion == "c" && /^Window /       { guardar(); dir = $2; titulo = ""; clase = "" }
        seccion == "c" && /^\tworkspace: / { ws = $2 + 0 }
        seccion == "c" && /^\tclass: /     { sub(/^\tclass: /, ""); clase = $0 }
        seccion == "c" && /^\ttitle: /     { sub(/^\ttitle: /, ""); titulo = $0 }
        seccion == "m" && /^\tactive workspace: / { visible[$3] = 1 }
        END {
            for (n = 1; n <= 10; n++) {
                if (!(n in monitor)) continue
                clases = ""
                if (n == activo) clases = clases ",\"active\""
                else if (n in visible) clases = clases ",\"visible\""
                if ((n in urgente) && n != activo) clases = clases ",\"urgent\""
                if (!(n in ventanas)) clases = clases ",\"empty\""
                printf "%d\t%s\t{\"text\": \"%d\", \"tooltip\": \"<b>Workspace %d</b>%s\", \"class\": [%s]}\n", \
                    n, monitor[n], n, n, (n in ventanas) ? ventanas[n] : "\\nSin ventanas", substr(clases, 2)
            }
        }')
    [ "$salida" != "${PREVIO:-}" ] || return 0
    PREVIO="$salida"
    for n in {1..10}; do
        linea=$(awk -F'\t' -v n="$n" '$1 == n { print $2 "\t" $3 }' <<< "$salida")
        printf '%s\n' "$linea" > "$ESTADO/$n.tmp" && mv -f "$ESTADO/$n.tmp" "$ESTADO/$n"
    done
    pkill -RTMIN+"$SENAL" -f '^waybar( |$)' || true
}

# Un urgente deja de serlo cuando su ventana recibe el foco o se cierra
registrar() {
    case "$1" in
        urgent\>\>*) URGENTES[${1#urgent>>}]=1 ;;
        activewindowv2\>\>* | closewindow\>\>*) unset "URGENTES[${1#*>>}]" ;;
    esac
}

escuchar() {
    mkdir -p "$ESTADO"
    # Waybar abre uno por barra: trabaja el primero y los demás esperan por si se cierra
    exec 9> "$ESTADO/escucha.lock"
    flock 9
    actualizar
    local evento
    while read -r evento; do
        registrar "$evento"
        # Los eventos llegan en ráfagas: se recalcula una vez cuando dejan de llegar
        while read -r -t 0.05 evento; do registrar "$evento"; done
        actualizar
    done < <(nc -U "$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock")
}

mostrar() {
    local linea=""
    [ -f "$ESTADO/$1" ] && linea=$(< "$ESTADO/$1")
    if [ -n "$linea" ] && [ "${linea%%$'\t'*}" = "${WAYBAR_OUTPUT_NAME:-${linea%%$'\t'*}}" ]; then
        printf '%s\n' "${linea#*$'\t'}"
    else
        echo '{"text": ""}'
    fi
}

case "${1:-}" in
    escuchar) escuchar ;;
    [1-9] | 10) mostrar "$1" ;;
    *) echo "Uso: $0 escuchar | <1-10>" >&2; exit 1 ;;
esac
