#!/usr/bin/env bash
# Historial de notificaciones de Mako (SUPER + F3).
# Lista en Rofi las que ya se cerraron. Enter vuelve a mostrar la elegida.

if ! command -v makoctl > /dev/null; then
    echo "Mako no está disponible" >&2
    exit 1
fi

if ! historial=$(makoctl history -j 2>/dev/null); then
    notify-send -u critical "Notificaciones" "Mako no está en marcha" 2>/dev/null || true
    exit 1
fi

if ! command -v perl > /dev/null; then
    echo "Falta perl para leer el historial" >&2
    exit 1
fi

if ! registros_raw=$(printf '%s' "$historial" | perl -MJSON::PP -e '
    binmode STDIN, ":raw";
    binmode STDOUT, ":utf8";
    local $/;
    my $items = decode_json(<STDIN> || "[]");
    for my $n (@$items) {
        my ($summary, $body, $icon, $app, $urgency) = map {
            my $v = $n->{$_} // "";
            $v =~ s/[\r\n\t]+/ /g;
            $v;
        } qw(summary body app_icon app_name urgency);
        $urgency = "normal" unless $urgency =~ /^(low|normal|critical)$/;
        print join("\x1f", $urgency, $app, $icon, $summary, $body), "\n";
    }
'); then
    echo "No se pudo leer el historial" >&2
    exit 1
fi

registros=()
if [ -n "$registros_raw" ]; then
    mapfile -t registros <<< "$registros_raw"
fi

filas=()
for registro in "${registros[@]}"; do
    IFS=$'\x1f' read -r _urgency _app _icon summary body <<< "$registro"
    texto=$summary
    [ -n "$body" ] && texto="$summary — $body"
    [ -n "$texto" ] || texto="(sin texto)"
    if [ "${#texto}" -gt 110 ]; then
        texto="${texto:0:107}…"
    fi
    filas+=("$texto")
done

lineas=${#filas[@]}
if [ "$lineas" -eq 0 ]; then
    filas=("No hay notificaciones en el historial")
    lineas=1
fi
[ "$lineas" -gt 12 ] && lineas=12

indice=$(printf '%s\n' "${filas[@]}" | rofi -dmenu -i -p "Notificaciones" -no-custom -format i \
    -theme-str "window { width: 46%; }" \
    -theme-str "listview { lines: $lineas; }")
[ -n "${indice:-}" ] || exit 0
[ "$lineas" -eq 1 ] && [ ${#registros[@]} -eq 0 ] && exit 0

IFS=$'\x1f' read -r urgency app icon summary body <<< "${registros[$indice]}"
[ -n "$summary" ] || summary="Notificación"

args=(-u "$urgency")
[ -n "$app" ] && args+=(-a "$app")
[ -n "$icon" ] && args+=(-i "$icon")
notify-send "${args[@]}" "$summary" "$body"
