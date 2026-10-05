#!/usr/bin/env bash
# Lista de atajos de utils/atajos.txt en Rofi (SUPER + F1). Escribir filtra; Enter ejecuta el atajo.
#
# De dónde sale la acción de cada fila:
#   - 4.ª columna de atajos.txt, si existe: comando de shell (lo usa Waybar).
#   - Hyprland: el bind con esas teclas (hyprctl binds), así el comando no se repite aquí.
#   - Kitty: las teclas se envían a la ventana de Kitty enfocada (hyprctl dispatch sendshortcut).
# Los grupos ("SUPER + 0-9", "CTRL + Flechas") preguntan después qué número o dirección.
# Las filas sin acción (ratón, o Kitty sin una ventana de Kitty enfocada) se muestran atenuadas.

ATAJOS_FILE="$HOME/dotfiles/utils/atajos.txt"

declare -A MODS=([SUPER]=64 [SHIFT]=1 [CTRL]=4 [ALT]=8)
declare -A GRUPOS=([0-9]="1 2 3 4 5 6 7 8 9 0" [flechas]="left right up down")
declare -A PREGUNTAS=([0-9]="Workspace" [flechas]="Dirección")
declare -A NOMBRES=([left]="← Izquierda" [right]="→ Derecha" [up]="↑ Arriba" [down]="↓ Abajo" [0]="10")

# "SUPER + SHIFT + S" -> "65<TAB>s" (máscara de Hyprland y tecla o grupo en minúsculas); falla si no son teclas
teclas() {
    local -a partes
    local mascara=0 tecla parte
    IFS='+' read -ra partes <<< "$1"
    tecla=$(sed -E 's/\(.*\)//; s/^ +| +$//g' <<< "${partes[-1]}")
    unset 'partes[-1]'
    for parte in "${partes[@]}"; do
        parte=${parte// /}
        [ -n "${MODS[$parte]:-}" ] || return 1
        mascara=$((mascara | MODS[$parte]))
    done
    case "$tecla" in
        "Impr Pant") tecla="Print" ;;
        Enter) tecla="Return" ;;
    esac
    [[ "$tecla" =~ ^([A-Za-z0-9]|F[0-9]+|Print|Return|Escape|Flechas|0-9)$ ]] || return 1
    printf '%s\t%s' "$mascara" "${tecla,,}"
}

# Binds de Hyprland: "máscara<TAB>tecla" -> "dispatcher<TAB>argumento"
declare -A BINDS
while IFS=$'\t' read -r mascara tecla dispatcher argumento; do
    BINDS["$mascara"$'\t'"$tecla"]="$dispatcher"$'\t'"$argumento"
done < <(hyprctl binds | awk '
    /^\tmodmask:/    { m = $2 }
    /^\tkey:/        { k = tolower($2) }
    /^\tdispatcher:/ { d = $2 }
    /^\targ:/        { sub(/^\targ: ?/, ""); print m "\t" k "\t" d "\t" $0 }')

# Ventana enfocada: los atajos de Kitty solo se pueden enviar si es Kitty
ventana=$(hyprctl activewindow | awk 'NR == 1 { print $2 } /^\tclass:/ { print $2 }')
direccion=$(sed -n 1p <<< "$ventana")
en_kitty=0
[ "$(sed -n 2p <<< "$ventana")" = "kitty" ] && en_kitty=1

# ¿Tiene acción? Para un grupo basta con que exista el bind de su primer miembro
ejecutable() {
    local seccion="$1" mascara="$2" tecla="$3" primera bind
    primera=${GRUPOS[$tecla]:-$tecla}
    primera=${primera%% *}
    case "$seccion" in
        Hyprland)
            bind=${BINDS[$mascara$'\t'$primera]:-}
            # Abrir esta misma lista no tiene sentido desde la lista
            [ -n "$bind" ] && [[ "$bind" != *atajos.sh* ]] ;;
        Kitty) [ "$en_kitty" = 1 ] ;;
        *) return 1 ;;
    esac
}

escapar() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' <<< "$1"; }

acciones=()
filas=""
while IFS=$'\x1f' read -r seccion atajo comando texto; do
    accion=""
    if [ -n "$comando" ]; then
        accion="exec"$'\t'"$comando"
    elif t=$(teclas "$atajo") && ejecutable "$seccion" "${t%%$'\t'*}" "${t#*$'\t'}"; then
        accion="$seccion"$'\t'"$t"
    fi
    fila=$(escapar "$texto")
    [ -n "$accion" ] || fila="<span alpha='45%'>$fila</span>"
    acciones+=("$accion")
    filas+="$fila"$'\n'
done < <(awk -F'|' '
    /^[[:space:]]*(#|$)/ { next }
    {
        # El comando puede contener "|": es todo lo que sigue a la 3.ª columna
        comando = ""
        for (i = 4; i <= NF; i++) comando = comando (i > 4 ? "|" : "") $i
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", comando)
        for (i = 1; i <= 3; i++) gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
        printf "%s\037%s\037%s\037%-10s %-28s %s\n", $1, $2, comando, $1, $2, $3
    }' "$ATAJOS_FILE")

mensaje="Enter ejecuta el atajo · los atenuados solo funcionan con el teclado o el ratón"
[ "$en_kitty" = 1 ] || mensaje+=" · los de Kitty, abriendo la lista desde Kitty"

eleccion=$(printf '%s' "$filas" | rofi -dmenu -i -p "Atajos" -no-custom -markup-rows -format i \
    -mesg "$mensaje" \
    -theme-str "window { width: 55%; }" \
    -theme-str "mainbox { children: [inputbar, message, listview]; }" \
    -theme-str "listview { lines: 18; }" \
    -theme-str "element { padding: 6px 10px; }")

[ -n "$eleccion" ] || exit 0
IFS=$'\t' read -r tipo dato1 dato2 <<< "${acciones[$eleccion]}"
[ -n "$tipo" ] || exit 0

if [ "$tipo" = "exec" ]; then
    hyprctl dispatch exec "$dato1" > /dev/null
    exit 0
fi

mascara="$dato1"
tecla="$dato2"
if [ -n "${GRUPOS[$tecla]:-}" ]; then
    read -ra miembros <<< "${GRUPOS[$tecla]}"
    nombres=""
    for m in "${miembros[@]}"; do nombres+="${NOMBRES[$m]:-$m}"$'\n'; done
    i=$(printf '%s' "$nombres" | rofi -dmenu -i -p "${PREGUNTAS[$tecla]}" -no-custom -format i \
        -theme-str "window { width: 20%; }" \
        -theme-str "mainbox { children: [inputbar, listview]; }" \
        -theme-str "listview { lines: ${#miembros[@]}; }")
    [ -n "$i" ] || exit 0
    tecla="${miembros[$i]}"
fi

case "$tipo" in
    Hyprland)
        IFS=$'\t' read -r dispatcher argumento <<< "${BINDS[$mascara$'\t'$tecla]:-}"
        [ -n "$dispatcher" ] || exit 0
        if [ -n "$argumento" ]; then
            hyprctl dispatch "$dispatcher" "$argumento" > /dev/null
        else
            hyprctl dispatch "$dispatcher" > /dev/null
        fi
        ;;
    Kitty)
        mods=""
        for m in SUPER SHIFT CTRL ALT; do
            (( mascara & MODS[$m] )) && mods+="$m "
        done
        hyprctl dispatch sendshortcut "${mods% }, ${tecla^}, address:0x$direccion" > /dev/null
        ;;
esac
