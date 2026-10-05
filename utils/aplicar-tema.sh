#!/usr/bin/env bash
# Aplica tema/tema.conf a la capa de usuario (alias: tema-aplicar).
# Escribe los archivos tema.* de config/ y recarga las apps abiertas.
# GRUB y la pantalla de inicio de sesión los genera Nix: aplicar con nix-switch.
set -euo pipefail

DOTFILES="$HOME/dotfiles"
TEMA="$DOTFILES/tema/tema.conf"
CABECERA="Generado por utils/aplicar-tema.sh desde tema/tema.conf. No editar: cambiar el tema allí."

# shellcheck source=../tema/tema.conf
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

# --- CONVERSIONES ---
# "#3399cc" -> "3399cc"
hex() { printf '%s' "${1#\#}"; }
# 0.70 -> "b3" (canal alfa en hexadecimal)
alfa() { awk -v o="$1" 'BEGIN { printf "%02x", int(o * 255 + 0.5) }'; }
# Escribe stdin en $1 de una sola vez: Hyprland recarga al detectar cambios y no
# debe leer el archivo a medio escribir (vería las variables sin definir).
escribir() { cat > "$1.tmp" && mv -f "$1.tmp" "$1"; }

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
\$iconos = $ICONOS
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

# --- GTK, CURSOR Y FASTFETCH (solo las claves del tema; el resto lo gestiona nwg-look) ---
sed -i -E \
    -e "s|^(gtk-icon-theme-name=).*|\1$ICONOS|" \
    -e "s|^(gtk-cursor-theme-name=).*|\1$CURSOR|" \
    -e "s|^(gtk-cursor-theme-size=).*|\1$CURSOR_TAMANO|" \
    "$DOTFILES/config/gtk-3.0/settings.ini" "$DOTFILES/config/gtk-4.0/settings.ini"
sed -i -E \
    -e "s|^(gtk-icon-theme-name=).*|\1\"$ICONOS\"|" \
    -e "s|^(gtk-cursor-theme-name=).*|\1\"$CURSOR\"|" \
    -e "s|^(gtk-cursor-theme-size=).*|\1$CURSOR_TAMANO|" \
    "$DOTFILES/config/gtkrc-2.0"
sed -i -E "s|^(Inherits=).*|\1$CURSOR|" "$DOTFILES/icons/default/index.theme"
sed -i -E "s|(\"keys\": )\"[^\"]*\"|\1\"$ACENTO\"|" "$DOTFILES/config/fastfetch/config.jsonc"

echo "Tema escrito en config/ (Hyprland y hyprlock, Waybar, Kitty, Rofi, Mako, GTK, fastfetch)."

# --- RECARGAR LO QUE ESTÉ ABIERTO ---
if command -v dconf > /dev/null; then
    dconf write /org/gnome/desktop/interface/icon-theme "'$ICONOS'" || true
    dconf write /org/gnome/desktop/interface/cursor-theme "'$CURSOR'" || true
    dconf write /org/gnome/desktop/interface/cursor-size "$CURSOR_TAMANO" || true
fi
if [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
    hyprctl reload > /dev/null
    hyprctl setcursor "$CURSOR" "$CURSOR_TAMANO" > /dev/null
    pkill -x swaybg || true
    hyprctl dispatch exec "swaybg -i '$WALLPAPER' -m fill" > /dev/null
fi
pkill -USR2 -x waybar || true
# Kitty se recarga por su socket de control remoto (listen_on en kitty.conf)
for socket in "${XDG_RUNTIME_DIR:-/run/user/$UID}"/kitty-*; do
    [ -S "$socket" ] && kitty @ --to "unix:$socket" load-config > /dev/null 2>&1 || true
done
makoctl reload 2> /dev/null || true

echo "Escritorio recargado. Para GRUB y la pantalla de inicio de sesión: nix-switch"
