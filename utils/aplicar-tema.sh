#!/usr/bin/env bash
# Aplica el tema activo a la capa de usuario (alias: tema-aplicar).
#   aplicar-tema.sh           -> vuelve a aplicar tema/tema.conf
#   aplicar-tema.sh <nombre>  -> elige tema/temas/<nombre>.conf y lo aplica
# Escribe los archivos tema.* de config/ (no versionados) y recarga las apps abiertas.
# GRUB y la pantalla de inicio de sesión los genera Nix: aplicar con nix-switch.
set -euo pipefail

DOTFILES="$HOME/dotfiles"
TEMA="$DOTFILES/tema/tema.conf"
CABECERA="Generado por utils/aplicar-tema.sh desde tema/tema.conf. No editar: cambiar el tema allí."

# tema/tema.conf es un enlace local al tema elegido; sin elegir, el tema nova
if [ -n "${1:-}" ]; then
    [ -f "$DOTFILES/tema/temas/$1.conf" ] || { echo "No existe el tema: tema/temas/$1.conf" >&2; exit 1; }
    ln -sfn "temas/$1.conf" "$TEMA"
elif [ ! -e "$TEMA" ]; then
    ln -sfn "temas/nova.conf" "$TEMA"
fi

# shellcheck source=../tema/temas/nova.conf
source "$TEMA"

# --- VALIDACIÓN ---
for var in ACENTO SECUNDARIO FONDO SUPERFICIE TEXTO TEXTO_TENUE INACTIVO URGENTE EXITO AVISO INFO; do
    [[ "${!var:-}" =~ ^#[0-9a-fA-F]{6}$ ]] || { echo "tema.conf: $var debe ser un color #RRGGBB (es '${!var:-}')" >&2; exit 1; }
done
for var in OPACIDAD_PANEL OPACIDAD_MENU OPACIDAD_TERMINAL; do
    [[ "${!var:-}" =~ ^(0(\.[0-9]+)?|1(\.0+)?)$ ]] || { echo "tema.conf: $var debe estar entre 0 y 1 (es '${!var:-}')" >&2; exit 1; }
done
WALLPAPER="$DOTFILES/$FONDO_PANTALLA"
[ -f "$WALLPAPER" ] || { echo "tema.conf: no existe FONDO_PANTALLA ($WALLPAPER)" >&2; exit 1; }
LOGO="$DOTFILES/${LOGO_FASTFETCH:-public/png/blue_extorsist_blue.png}"
[ -f "$LOGO" ] || { echo "tema.conf: no existe LOGO_FASTFETCH ($LOGO)" >&2; exit 1; }
COLORES_PAPIRUS="adwaita black blue bluegrey breeze brown carmine cyan darkcyan deeporange green grey indigo magenta nordic orange palebrown paleorange pink red teal violet white yaru yellow"
COLOR_CARPETAS="${COLOR_CARPETAS:-blue}"
[[ " $COLORES_PAPIRUS " == *" $COLOR_CARPETAS "* ]] || { echo "tema.conf: COLOR_CARPETAS debe ser uno de: $COLORES_PAPIRUS" >&2; exit 1; }
# Un cursor que aún no está instalado (falta nix-switch) se vería como el de por defecto: se mantiene el actual
if [ ! -d "/run/current-system/sw/share/icons/$CURSOR" ]; then
    echo "Aviso: el cursor $CURSOR no está instalado (nix-switch): se mantiene ${XCURSOR_THEME:-el actual}" >&2
    [ -n "${XCURSOR_THEME:-}" ] && [ -d "/run/current-system/sw/share/icons/$XCURSOR_THEME" ] && CURSOR="$XCURSOR_THEME"
fi

# --- CONVERSIONES ---
# "#3399cc" -> "3399cc"
hex() { printf '%s' "${1#\#}"; }
# 0.70 -> "b3" (canal alfa en hexadecimal)
alfa() { awk -v o="$1" 'BEGIN { printf "%02x", int(o * 255 + 0.5) }'; }
# Escribe stdin en $1 de una sola vez: Hyprland recarga al detectar cambios y no
# debe leer el archivo a medio escribir (vería las variables sin definir).
escribir() { cat > "$1.tmp" && mv -f "$1.tmp" "$1"; }

# --- ICONOS: color de las carpetas ---
# Papirus trae las carpetas en varios colores y elige uno con enlaces (folder.svg -> folder-blue.svg).
# El tema de iconos "dotfiles-iconos" hereda de ICONOS y reapunta esos enlaces a COLOR_CARPETAS.
# Lo usa GTK (Thunar); Rofi y Mako siguen con ICONOS.
TEMA_ICONOS="$HOME/.local/share/icons/dotfiles-iconos"
DIR_ICONOS="/run/current-system/sw/share/icons/$ICONOS"
ICONOS_GTK="$ICONOS"
# Se regenera solo si cambian los iconos, el color o la versión instalada del tema
firma="$(readlink -f "$DIR_ICONOS" 2> /dev/null) $COLOR_CARPETAS"
if [ -f "$TEMA_ICONOS/index.theme" ] && [ "$(cat "$TEMA_ICONOS/.firma" 2> /dev/null)" = "$firma" ]; then
    ICONOS_GTK="dotfiles-iconos"
elif [ -f "$DIR_ICONOS/48x48/places/folder-$COLOR_CARPETAS.svg" ]; then
    rm -rf "$TEMA_ICONOS"
    patron="^(folder|user)-(${COLORES_PAPIRUS// /|})(-.*)?\.svg$"
    directorios=()
    for dir in "$DIR_ICONOS"/*/places; do
        tamano=$(basename "$(dirname "$dir")")
        declare -A enlaces=()
        while read -r nombre objetivo; do
            enlaces[$nombre]=$objetivo
        done < <(find "$dir/" -maxdepth 1 -type l -printf '%f %l\n')
        lista=""
        for nombre in "${!enlaces[@]}"; do
            # Sigue la cadena dentro del directorio (folder-downloads -> folder-download -> folder-blue-download)
            objetivo=${enlaces[$nombre]}
            for _ in 1 2 3 4; do [ -n "${enlaces[$objetivo]:-}" ] && objetivo=${enlaces[$objetivo]}; done
            [[ "$objetivo" =~ $patron ]] || continue
            nuevo="${BASH_REMATCH[1]}-$COLOR_CARPETAS${BASH_REMATCH[3]}.svg"
            [ -e "$dir/$nuevo" ] && lista+="$dir/$nuevo $TEMA_ICONOS/$tamano/places/$nombre"$'\n'
        done
        unset enlaces
        [ -n "$lista" ] || continue
        mkdir -p "$TEMA_ICONOS/$tamano/places"
        # Miles de enlaces: con un solo proceso en lugar de un ln por enlace
        printf '%s' "$lista" | perl -ne 'chomp; my ($o, $e) = split / /; symlink($o, $e) or die "$e: $!\n"'
        directorios+=("$tamano/places")
    done
    {
        printf '[Icon Theme]\nName=dotfiles-iconos\nComment=%s con carpetas %s (generado por utils/aplicar-tema.sh)\n' "$ICONOS" "$COLOR_CARPETAS"
        printf 'Inherits=%s\nDirectories=%s\n' "$ICONOS" "$(IFS=,; echo "${directorios[*]}")"
        for d in "${directorios[@]}"; do
            echo
            awk -v s="[$d]" '$0 == s { p = 1 } p && /^$/ { exit } p' "$DIR_ICONOS/index.theme"
        done
    } > "$TEMA_ICONOS/index.theme"
    echo "$firma" > "$TEMA_ICONOS/.firma"
    ICONOS_GTK="dotfiles-iconos"
else
    echo "Aviso: $ICONOS no tiene carpetas de color $COLOR_CARPETAS (solo Papirus): se dejan como están" >&2
fi

# --- HYPRLAND ---
escribir "$DOTFILES/config/hypr/tema.conf" <<EOF
# $CABECERA
\$acento = rgb($(hex "$ACENTO"))
\$secundario = rgb($(hex "$SECUNDARIO"))
\$inactivo = rgba($(hex "$INACTIVO")aa)
\$fondo = rgb($(hex "$FONDO"))
\$panel = rgba($(hex "$FONDO")$(alfa "$OPACIDAD_PANEL"))
\$superficie = rgba($(hex "$SUPERFICIE")$(alfa "$OPACIDAD_PANEL"))
\$texto = rgb($(hex "$TEXTO"))
\$texto_tenue = rgb($(hex "$TEXTO_TENUE"))
\$urgente = rgb($(hex "$URGENTE"))
\$exito = rgb($(hex "$EXITO"))
\$aviso = rgb($(hex "$AVISO"))
\$fuente = $FUENTE
\$radio = $RADIO
\$borde = $BORDE
\$fondo_pantalla = $WALLPAPER
\$cursor = $CURSOR
\$tamano_cursor = $CURSOR_TAMANO
\$iconos = $ICONOS_GTK
EOF

# --- WAYBAR ---
escribir "$DOTFILES/config/waybar/tema.css" <<EOF
/* $CABECERA */
@define-color acento $ACENTO;
@define-color secundario $SECUNDARIO;
@define-color fondo $FONDO;
@define-color superficie $SUPERFICIE;
@define-color texto $TEXTO;
@define-color texto_tenue $TEXTO_TENUE;
@define-color urgente $URGENTE;
@define-color exito $EXITO;
@define-color aviso $AVISO;
@define-color panel alpha(@superficie, $OPACIDAD_PANEL);

* {
    font-family: "$FUENTE", FontAwesome, sans-serif;
}

.module,
#tray,
#workspaces button {
    border-radius: ${RADIO}px;
}
EOF

# --- KITTY ---
escribir "$DOTFILES/config/kitty/tema.conf" <<EOF
# $CABECERA
font_family             $FUENTE
font_size               $FUENTE_TAMANO
background              $FONDO
foreground              $TEXTO
background_opacity      $OPACIDAD_TERMINAL
cursor                  $ACENTO
cursor_text_color       $FONDO
selection_background    $SUPERFICIE
selection_foreground    $TEXTO
url_color               $ACENTO
active_border_color     $ACENTO
inactive_border_color   $INACTIVO
bell_border_color       $AVISO
tab_bar_background      $FONDO
active_tab_background   $ACENTO
active_tab_foreground   $FONDO
inactive_tab_background $SUPERFICIE
inactive_tab_foreground $TEXTO

# Paleta ANSI (normal / brillante)
color0  $INACTIVO
color8  $TEXTO_TENUE
color1  $URGENTE
color9  $URGENTE
color2  $EXITO
color10 $EXITO
color3  $AVISO
color11 $AVISO
color4  $ACENTO
color12 $ACENTO
color5  $SECUNDARIO
color13 $SECUNDARIO
color6  $INFO
color14 $INFO
color7  $TEXTO
color15 $TEXTO
EOF

# --- ROFI ---
escribir "$DOTFILES/config/rofi/tema.rasi" <<EOF
/* $CABECERA */
configuration {
    font: "$FUENTE $FUENTE_TAMANO";
    icon-theme: "$ICONOS";
}

* {
    acento: $ACENTO;
    secundario: $SECUNDARIO;
    fondo: $FONDO$(alfa "$OPACIDAD_MENU");
    superficie: $SUPERFICIE$(alfa "$OPACIDAD_PANEL");
    texto: $TEXTO;
    texto-tenue: $TEXTO_TENUE;
    urgente: $URGENTE;
    exito: $EXITO;
    radio: ${RADIO}px;
    borde: ${BORDE}px;
}
EOF

# --- MAKO (notificaciones) ---
mkdir -p "$DOTFILES/config/mako"
escribir "$DOTFILES/config/mako/config" <<EOF
# $CABECERA
font=$FUENTE $FUENTE_TAMANO
background-color=$FONDO$(alfa "$OPACIDAD_MENU")
text-color=$TEXTO
border-color=$ACENTO
progress-color=over $SUPERFICIE
border-size=$BORDE
border-radius=$RADIO
padding=12
margin=10
width=360
max-icon-size=48
icon-path=/run/current-system/sw/share/icons/$ICONOS

[urgency=low]
border-color=$TEXTO_TENUE

[urgency=critical]
border-color=$URGENTE
EOF

# --- FASTFETCH ---
# config.jsonc usa este enlace; fastfetch cachea el logo por su ruta real, así que ve el cambio al momento
ln -sfn "$LOGO" "$DOTFILES/config/fastfetch/logo.png"

# --- COLORES DE GTK (Thunar y demás apps GTK3/GTK4) ---
# adw-gtk3 define sus colores como variables que se pueden redefinir. El tema GTK
# "dotfiles-tema" lo importa y pone la paleta: GTK vuelve a leer el tema al cambiar su nombre,
# así las ventanas abiertas se recolorean (el gtk.css del usuario solo se lee al abrir la app).
# Las apps de libadwaita (GTK4) ignoran el tema GTK y leen ~/.config/gtk-4.0/gtk.css.
TEMA_GTK="$HOME/.local/share/themes/dotfiles-tema"
ADW_GTK3=""
for dir in /run/current-system/sw/share/themes "$HOME/.local/share/themes"; do
    [ -d "$dir/adw-gtk3-dark" ] && { ADW_GTK3="$dir/adw-gtk3-dark"; break; }
done
colores_gtk() {
    cat <<EOF
@define-color accent_color $ACENTO;
@define-color accent_bg_color $ACENTO;
@define-color accent_fg_color $FONDO;
@define-color destructive_color $URGENTE;
@define-color destructive_bg_color $URGENTE;
@define-color destructive_fg_color $FONDO;
@define-color error_color $URGENTE;
@define-color error_bg_color $URGENTE;
@define-color error_fg_color $FONDO;
@define-color success_color $EXITO;
@define-color success_bg_color $EXITO;
@define-color success_fg_color $FONDO;
@define-color warning_color $AVISO;
@define-color warning_bg_color $AVISO;
@define-color warning_fg_color $FONDO;

@define-color window_bg_color $FONDO;
@define-color window_fg_color $TEXTO;
@define-color view_bg_color shade($FONDO, 0.8);
@define-color view_fg_color $TEXTO;
@define-color headerbar_bg_color mix($FONDO, $SUPERFICIE, 0.45);
@define-color headerbar_fg_color $TEXTO;
@define-color headerbar_backdrop_color $FONDO;
@define-color sidebar_bg_color mix($FONDO, $SUPERFICIE, 0.25);
@define-color sidebar_fg_color $TEXTO;
@define-color sidebar_backdrop_color mix($FONDO, $SUPERFICIE, 0.15);
@define-color card_bg_color alpha($SUPERFICIE, 0.35);
@define-color card_fg_color $TEXTO;
@define-color dialog_bg_color mix($FONDO, $SUPERFICIE, 0.3);
@define-color dialog_fg_color $TEXTO;
@define-color popover_bg_color mix($FONDO, $SUPERFICIE, 0.3);
@define-color popover_fg_color $TEXTO;
EOF
}
mkdir -p "$TEMA_GTK/gtk-3.0" "$TEMA_GTK/gtk-4.0"
printf '[Desktop Entry]\nType=X-GNOME-Metatheme\nName=dotfiles-tema\n\n[X-GNOME-Metatheme]\nGtkTheme=dotfiles-tema\n' \
    > "$TEMA_GTK/index.theme"
if [ -n "$ADW_GTK3" ]; then
    { echo "/* $CABECERA */"; echo "@import url(\"file://$ADW_GTK3/gtk-3.0/gtk.css\");"; colores_gtk; } \
        | escribir "$TEMA_GTK/gtk-3.0/gtk.css"
    { echo "/* $CABECERA */"; echo "@import url(\"file://$ADW_GTK3/gtk-4.0/gtk.css\");"; } \
        | escribir "$TEMA_GTK/gtk-4.0/gtk.css"
else
    # Sin adw-gtk3 (falta nix-switch): Adwaita oscuro de GTK, sin los colores del tema
    echo "Aviso: adw-gtk3 no está instalado (nix-switch): las apps GTK no toman los colores del tema" >&2
    echo '@import url("resource:///org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css");' \
        | escribir "$TEMA_GTK/gtk-3.0/gtk.css"
    : | escribir "$TEMA_GTK/gtk-4.0/gtk.css"
fi
{ echo "/* $CABECERA */"; colores_gtk; } | escribir "$DOTFILES/config/gtk-4.0/gtk.css"

# --- GTK Y CURSOR (solo las claves del tema; el resto lo gestiona nwg-look) ---
sed -i -E \
    -e "s|^(gtk-icon-theme-name=).*|\1$ICONOS_GTK|" \
    -e "s|^(gtk-cursor-theme-name=).*|\1$CURSOR|" \
    -e "s|^(gtk-cursor-theme-size=).*|\1$CURSOR_TAMANO|" \
    "$DOTFILES/config/gtk-3.0/settings.ini" "$DOTFILES/config/gtk-4.0/settings.ini"
sed -i -E \
    -e "s|^(gtk-icon-theme-name=).*|\1\"$ICONOS_GTK\"|" \
    -e "s|^(gtk-cursor-theme-name=).*|\1\"$CURSOR\"|" \
    -e "s|^(gtk-cursor-theme-size=).*|\1$CURSOR_TAMANO|" \
    "$DOTFILES/config/gtkrc-2.0"
# Cursor por defecto para Xwayland y apps que no leen GTK ni las variables XCURSOR_*
for dir in "$HOME/.icons" "$HOME/.local/share/icons"; do
    mkdir -p "$dir/default"
    printf '[Icon Theme]\nInherits=%s\n' "$CURSOR" > "$dir/default/index.theme"
    if [ -d "/run/current-system/sw/share/icons/$CURSOR" ]; then
        ln -sfn "/run/current-system/sw/share/icons/$CURSOR" "$dir/$CURSOR"
    fi
done

echo "Tema \"$NOMBRE\" escrito en config/ (Hyprland y hyprlock, Waybar, Kitty, Rofi, Mako, GTK, cursor, fastfetch)."

# --- RECARGAR LO QUE ESTÉ ABIERTO ---
if command -v dconf > /dev/null; then
    dconf write /org/gnome/desktop/interface/cursor-theme "'$CURSOR'" || true
    dconf write /org/gnome/desktop/interface/cursor-size "$CURSOR_TAMANO" || true
    # Cambiar el nombre de los temas GTK y de iconos y volver hace que las apps abiertas los relean
    dconf write /org/gnome/desktop/interface/gtk-theme "'adw-gtk3-dark'" || true
    dconf write /org/gnome/desktop/interface/icon-theme "'$ICONOS'" || true
    sleep 0.3
    dconf write /org/gnome/desktop/interface/gtk-theme "'dotfiles-tema'" || true
    dconf write /org/gnome/desktop/interface/icon-theme "'$ICONOS_GTK'" || true
fi
if [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
    hyprctl reload > /dev/null || echo "Aviso: no se pudo recargar Hyprland (hyprctl reload)" >&2
    hyprctl setcursor "$CURSOR" "$CURSOR_TAMANO" > /dev/null || true
    # Por línea de comandos: en NixOS el proceso se llama .swaybg-wrapped
    pkill -f '^swaybg( |$)' || true
    hyprctl dispatch exec "swaybg -i '$WALLPAPER' -m fill" > /dev/null
fi
pkill -USR2 -f '^waybar( |$)' || true
# Kitty se recarga por su socket de control remoto (listen_on en kitty.conf)
for socket in "${XDG_RUNTIME_DIR:-/run/user/$UID}"/kitty-*; do
    [ -S "$socket" ] && kitty @ --to "unix:$socket" load-config > /dev/null 2>&1 || true
done
makoctl reload 2> /dev/null || true

echo "Escritorio recargado. Para GRUB y la pantalla de inicio de sesión: nix-switch"
