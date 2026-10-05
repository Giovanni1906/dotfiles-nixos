#!/usr/bin/env bash
# Selector de temas en Rofi (SUPER + F2): lista tema/temas/*.conf con una vista
# del fondo y la paleta, y aplica el elegido con utils/aplicar-tema.sh.
# GRUB y la pantalla de inicio de sesión cambian con el siguiente nix-switch.

DOTFILES="$HOME/dotfiles"
TEMAS="$DOTFILES/tema/temas"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/temas"
mkdir -p "$CACHE"

ACTIVO=$(basename "$(readlink "$DOTFILES/tema/tema.conf" 2>/dev/null)" .conf)
[ -n "$ACTIVO" ] || ACTIVO="nova"

# Valor de una variable de un archivo de tema (en un subshell, sin tocar las de este script)
leer() {
    (
        # shellcheck source=/dev/null
        source "$1"
        printf '%s' "${!2:-}"
    )
}

# Vista de 128x128: el fondo arriba y franjas con acento, secundario, superficie y fondo.
# Se regenera solo si cambia el archivo del tema (el nombre incluye su hash).
vista() {
    local archivo="$1" salida
    salida="$CACHE/$(basename "$archivo" .conf)-$(md5sum < "$archivo" | cut -c1-8).png"
    if [ ! -f "$salida" ] && command -v magick > /dev/null; then
        (
            # shellcheck source=../tema/temas/nova.conf
            source "$archivo"
            magick "$DOTFILES/$FONDO_PANTALLA" -resize 128x88^ -gravity center -extent 128x88 \
                \( -size 32x40 "xc:$ACENTO" "xc:$SECUNDARIO" "xc:$SUPERFICIE" "xc:$FONDO" +append \) \
                -append "$salida" 2> /dev/null
        )
    fi
    printf '%s' "$salida"
}

nombres=()
filas=""
activo_idx=0
for archivo in "$TEMAS"/*.conf; do
    id=$(basename "$archivo" .conf)
    titulo=$(leer "$archivo" NOMBRE)
    descripcion=$(leer "$archivo" DESCRIPCION)
    marca=""
    if [ "$id" = "$ACTIVO" ]; then
        marca="  ·  activo"
        activo_idx=${#nombres[@]}
    fi
    nombres+=("$id")
    filas+="<b>${titulo:-$id}</b>   <span alpha='65%'>$descripcion$marca</span>\0icon\x1f$(vista "$archivo")\n"
done
EDITAR=${#nombres[@]}
filas+="<b>Editar el tema activo</b>   <span alpha='65%'>Abre tema/tema.conf y lo aplica al cerrar</span>\0icon\x1faccessories-text-editor\n"

eleccion=$(printf '%b' "$filas" | rofi -dmenu -i -p "Temas" -markup-rows -format i \
    -a "$activo_idx" \
    -theme-str "window { width: 46%; }" \
    -theme-str "mainbox { children: [inputbar, listview]; }" \
    -theme-str "listview { lines: $((EDITAR + 1)); }" \
    -theme-str "element { padding: 8px 12px; spacing: 16px; }" \
    -theme-str "element-icon { size: 64px; }")

[ -n "$eleccion" ] || exit 0

if [ "$eleccion" -eq "$EDITAR" ]; then
    kitty --class tema-editor -e sh -c "micro '$DOTFILES/tema/tema.conf' && '$DOTFILES/utils/aplicar-tema.sh'" &
    exit 0
fi

id="${nombres[$eleccion]}"
if salida=$("$DOTFILES/utils/aplicar-tema.sh" "$id" 2>&1); then
    titulo=$(leer "$TEMAS/$id.conf" NOMBRE)
    notify-send -i "$(vista "$TEMAS/$id.conf")" "Tema ${titulo:-$id} aplicado" \
        "GRUB y la pantalla de inicio de sesión cambian con nix-switch."
else
    notify-send -u critical "No se pudo aplicar el tema $id" "$salida"
fi
