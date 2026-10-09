#!/usr/bin/env bash
# Mueve la ventana activa en una dirección (SUPER + SHIFT + flechas) con la misma lógica
# sea cual sea el número de ventanas del workspace:
#   1. Si hay otra ventana en esa dirección, intercambia el sitio con ella (swapwindow).
#   2. Si no la hay y la ventana aún no ocupa todo ese borde del workspace, la lleva a ese
#      borde a todo lo ancho (arriba/abajo) o a todo lo alto (izquierda/derecha); las demás
#      quedan juntas al otro lado.
#   3. Si ya ocupa todo el borde, o está sola, pasa al monitor de al lado (movewindow); si no
#      hay monitor en esa dirección, no hace nada.
# Flotantes y pantalla completa: movewindow de siempre.
# Necesita dwindle:preserve_split; sin él Hyprland deshace la división al recalcular.
#   mover-ventana.sh l|r|u|d

dir="${1:-}"
[[ "$dir" =~ ^[lrud]$ ]] || { echo "Uso: $0 l|r|u|d" >&2; exit 1; }

TOL=2    # px de margen al comparar bordes

# Ventanas en mosaico del workspace activo: "activa x y ancho alto dirección" (activa = 1 o 0)
ventanas() {
    local activa
    activa=$(hyprctl activewindow | awk 'NR == 1 { print $2 }')
    hyprctl clients | awk -v activa="$activa" -v ws="$(hyprctl activeworkspace | awk 'NR == 1 { print $3 }')" '
        function guardar() {
            if (id != "" && mapeada && !oculta && !flotante && espacio == ws)
                print (id == activa), x, y, w, h, id
            id = ""
        }
        /^Window /        { guardar(); id = $2 }
        /^\tmapped: /     { mapeada = $2 }
        /^\thidden: /     { oculta = $2 }
        /^\tfloating: /   { flotante = $2 }
        /^\tworkspace: /  { espacio = $2 }
        /^\tat: /         { split($2, p, ","); x = p[1]; y = p[2] }
        /^\tsize: /       { split($2, p, ","); w = p[1]; h = p[2] }
        END { guardar() }'
}

# Situación de la activa respecto a las demás: "vecina ancho_completo alto_completo en_inicio"
#   vecina: hay otra ventana en la dirección pedida
#   ancho/alto_completo: ocupa todo el ancho/alto del conjunto
#   en_inicio: está arriba (u/d) o a la izquierda (l/r) del conjunto
situacion() {
    ventanas | awk -v dir="$dir" -v tol="$TOL" '
        { a[NR] = $1; x[NR] = $2; y[NR] = $3; w[NR] = $4; h[NR] = $5 }
        $1 == 1 { yo = NR }
        END {
            if (!yo || NR < 2) { print "solo"; exit }
            minx = miny = 1e9; maxx = maxy = -1e9
            for (i = 1; i <= NR; i++) {
                if (x[i] < minx) minx = x[i]; if (y[i] < miny) miny = y[i]
                if (x[i] + w[i] > maxx) maxx = x[i] + w[i]; if (y[i] + h[i] > maxy) maxy = y[i] + h[i]
                if (i == yo) continue
                solapa_h = x[i] < x[yo] + w[yo] && x[i] + w[i] > x[yo]
                solapa_v = y[i] < y[yo] + h[yo] && y[i] + h[i] > y[yo]
                if (dir == "d" && solapa_h && y[i] >= y[yo] + h[yo] - tol) vecina = 1
                if (dir == "u" && solapa_h && y[i] + h[i] <= y[yo] + tol) vecina = 1
                if (dir == "r" && solapa_v && x[i] >= x[yo] + w[yo] - tol) vecina = 1
                if (dir == "l" && solapa_v && x[i] + w[i] <= x[yo] + tol) vecina = 1
            }
            ancho = x[yo] <= minx + tol && x[yo] + w[yo] >= maxx - tol
            alto = y[yo] <= miny + tol && y[yo] + h[yo] >= maxy - tol
            inicio = (dir == "u" || dir == "d") ? y[yo] <= miny + tol : x[yo] <= minx + tol
            print vecina + 0, ancho, alto, inicio
        }'
}

# ¿Hay un monitor al lado del enfocado en la dirección pedida? (sin él, movewindow reordena el mosaico)
hay_monitor() {
    hyprctl monitors | awk -v dir="$dir" '
        /^Monitor /   { n++ }
        /^\t[0-9]+x[0-9]+@/ {
            split($1, t, /[x@]/); split($3, p, "x")
            w[n] = t[1]; h[n] = t[2]; x[n] = p[1]; y[n] = p[2]
        }
        /^\tscale: /  { w[n] /= $2; h[n] /= $2 }
        /^\tfocused: yes/ { yo = n }
        END {
            for (i = 1; i <= n; i++) {
                if (i == yo) continue
                solapa_h = x[i] < x[yo] + w[yo] && x[i] + w[i] > x[yo]
                solapa_v = y[i] < y[yo] + h[yo] && y[i] + h[i] > y[yo]
                if ((dir == "d" && solapa_h && y[i] >= y[yo] + h[yo]) || (dir == "u" && solapa_h && y[i] + h[i] <= y[yo]) ||
                    (dir == "r" && solapa_v && x[i] >= x[yo] + w[yo]) || (dir == "l" && solapa_v && x[i] + w[i] <= x[yo]))
                    hay = 1
            }
            exit !hay
        }'
}

# Ventana cuya división hay que girar para que las demás no queden en franjas: deduce de la
# geometría cómo están divididas (el corte recto más centrado de cada grupo) y busca, de arriba
# abajo, una división a contrapelo de su hueco (lado a lado en uno alto o apiladas en uno ancho)
# con una sola ventana en una de sus mitades: togglesplit sobre esa ventana gira esa división.
#   a_girar <dirección de la ventana movida>
a_girar() {
    ventanas | awk -v tol="$TOL" -v movida="$1" '
        $6 == movida { next }
        { n++; x[n] = $2; y[n] = $3; w[n] = $4; h[n] = $5; id[n] = $6; todas = todas " " n }
        function analizar(lista,    v, k, i, j, c, minx, miny, maxx, maxy, mejor, d, tipo, a, b, ca, cb, r) {
            k = split(lista, v, " ")
            if (k < 2) return ""
            minx = miny = 1e9; maxx = maxy = -1e9
            for (i = 1; i <= k; i++) {
                j = v[i]
                if (x[j] < minx) minx = x[j]; if (y[j] < miny) miny = y[j]
                if (x[j] + w[j] > maxx) maxx = x[j] + w[j]; if (y[j] + h[j] > maxy) maxy = y[j] + h[j]
            }
            mejor = 1e9
            for (i = 1; i <= k; i++) {
                c = x[v[i]] + w[v[i]]; d = c - (minx + maxx) / 2; if (d < 0) d = -d
                if (d < mejor && cortar(v, k, c, "v")) { mejor = d; tipo = "v"; a = CA; b = CB }
                c = y[v[i]] + h[v[i]]; d = c - (miny + maxy) / 2; if (d < 0) d = -d
                if (d < mejor && cortar(v, k, c, "h")) { mejor = d; tipo = "h"; a = CA; b = CB }
            }
            if (tipo == "") return ""
            if ((tipo == "h") != (maxy - miny > maxx - minx)) {
                ca = split(a, r, " "); if (ca == 1) return id[r[1]]
                cb = split(b, r, " "); if (cb == 1) return id[r[1]]
            }
            c = analizar(a)
            return c != "" ? c : analizar(b)
        }
        # Reparte el grupo a ambos lados del corte c (vertical u horizontal) en CA y CB
        function cortar(v, k, c, eje,    i, j, ini, fin) {
            CA = CB = ""
            for (i = 1; i <= k; i++) {
                j = v[i]
                ini = eje == "v" ? x[j] : y[j]; fin = eje == "v" ? x[j] + w[j] : y[j] + h[j]
                if (fin <= c + tol) CA = CA " " j
                else if (ini >= c) CB = CB " " j
                else return 0
            }
            return CA != "" && CB != ""
        }
        END { print analizar(todas) }'
}

# Las demás conservan la división que tenían; se giran las que quedaron a contrapelo
enderezar() {
    local activa otra i
    activa=$(hyprctl activewindow | awk 'NR == 1 { print $2 }')
    for i in 1 2 3; do
        otra=$(a_girar "$activa")
        [ -n "$otra" ] || break
        hyprctl --batch "dispatch focuswindow address:0x$otra; dispatch layoutmsg togglesplit" > /dev/null
    done
    [ "$i" = 1 ] || hyprctl dispatch focuswindow "address:0x$activa" > /dev/null
}

flotante=$(hyprctl activewindow | awk '/^\tfloating: / { print $2 }')
pantalla_completa=$(hyprctl activewindow | awk '/^\tfullscreen: / { print $2 }')
if [ "$flotante" != 0 ] || [ "$pantalla_completa" != 0 ]; then
    exec hyprctl dispatch movewindow "$dir" > /dev/null
fi

read -r vecina ancho alto inicio <<< "$(situacion)"
case "$dir" in u | d) completo=$ancho ;; *) completo=$alto ;; esac

if [ "$vecina" = solo ] || { [ "$vecina" = 0 ] && [ "$completo" = 1 ]; }; then
    if hay_monitor; then hyprctl dispatch movewindow "$dir" > /dev/null; fi
elif [ "$vecina" = 1 ]; then
    hyprctl dispatch swapwindow "$dir" > /dev/null
else
    # Al borde: la activa pasa a ser hija de la raíz, con las demás en la otra mitad
    hyprctl dispatch layoutmsg movetoroot > /dev/null
    read -r _ ancho alto inicio <<< "$(situacion)"
    case "$dir" in u | d) completo=$ancho ;; *) completo=$alto ;; esac
    if [ "$completo" = 0 ]; then
        hyprctl dispatch layoutmsg togglesplit > /dev/null
        read -r _ ancho alto inicio <<< "$(situacion)"
    fi
    # u/l: la activa debe quedar al inicio; d/r: al final
    if { [[ "$dir" == [ul] ]] && [ "$inicio" = 0 ]; } || { [[ "$dir" == [dr] ]] && [ "$inicio" = 1 ]; }; then
        hyprctl dispatch layoutmsg swapsplit > /dev/null
    fi
    enderezar
fi
