#!/usr/bin/env bash
# =============================================================================
# INSTALADOR Y ACTUALIZADOR DE LOS DOTFILES
# =============================================================================
# Uso: ./init.sh [paso] [opciones]
#
#   (sin paso) | todo [equipo]  Máquina nueva: usuario, sistema, apps y red
#   usuario                     Enlaces de config/, tema, permisos y archivos locales
#   sistema [equipo]            /etc/nixos usa el equipo del repo + nixos-rebuild switch
#   apps                        Zen Browser (Flatpak) y Thorium (AppImage), si faltan
#   red                         Inicia sesión en Tailscale, si no hay sesión
#   actualizar                  git pull + usuario + sistema (alias dotfiles-actualizar)
#   nuevo-equipo <nombre>       Crea nixos/equipos/<nombre> desde la plantilla
#
#   --simular                   Muestra lo que haría con sudo, sin ejecutarlo
#   -h, --help                  Esta ayuda
#
# Se puede ejecutar las veces que haga falta: cada paso comprueba antes de cambiar
# algo y lo que reemplaza lo respalda en ~/.local/state/dotfiles/respaldo/.

set -euo pipefail

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FECHA="$(date +%Y%m%d-%H%M%S)"
RESPALDO="$HOME/.local/state/dotfiles/respaldo/$FECHA"
THORIUM_URL="https://github.com/Alex313031/Thorium/releases/download/M128.0.6613.189/Thorium_Browser_128.0.6613.189_AVX2.AppImage"
SIMULAR=0
AVISOS=()

# --- SALIDA ---
titulo() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
ok()     { printf '  \033[32m✓\033[0m %s\n' "$*"; }
aviso()  { printf '  \033[33m!\033[0m %s\n' "$*"; AVISOS+=("$*"); }
error()  { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

ayuda() { sed -n '5,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

# --- SUDO ---
SUDO_ACTIVO=0
pedir_sudo() {
    [ "$SIMULAR" = 1 ] && return
    [ "$SUDO_ACTIVO" = 1 ] && return
    sudo -v || error "Se necesita sudo para este paso"
    # Mantiene sudo vivo mientras dure el script
    while true; do sudo -n true; sleep 50; kill -0 "$$" 2> /dev/null || exit; done 2> /dev/null &
    SUDO_ACTIVO=1
}
como_root() {
    if [ "$SIMULAR" = 1 ]; then printf '  [simular] sudo %s\n' "$*"; else sudo "$@"; fi
}
# Escribe stdin en un archivo de root
escribir_root() {
    if [ "$SIMULAR" = 1 ]; then
        printf '  [simular] escribir %s:\n' "$1"; sed 's/^/      /'
    else
        sudo tee "$1" > /dev/null
    fi
}

# --- ENLACES ---
# Enlaza $1 en $2. Si $2 ya existe y no es el enlace correcto, lo mueve al respaldo.
enlazar() {
    local origen="$1" destino="$2"
    if [ -L "$destino" ] && [ "$(readlink "$destino")" = "$origen" ]; then
        return
    fi
    if [ -L "$destino" ]; then
        rm "$destino"
    elif [ -e "$destino" ]; then
        mkdir -p "$RESPALDO"
        mv "$destino" "$RESPALDO/"
        ok "Respaldado ${destino/#$HOME/\~} en ${RESPALDO/#$HOME/\~}"
    fi
    mkdir -p "$(dirname "$destino")"
    ln -s "$origen" "$destino"
    ok "Enlazado ${destino/#$HOME/\~}"
}

# =============================================================================
# EQUIPOS (nixos/equipos/<nombre>)
# =============================================================================

equipos_del_repo() {
    find "$DOTFILES/nixos/equipos" -mindepth 1 -maxdepth 1 -type d ! -name plantilla -printf '%f\n' | sort
}

# Equipo que usa esta máquina según /etc/nixos/configuration.nix
equipo_actual() {
    local conf=/etc/nixos/configuration.nix destino
    if [ -L "$conf" ]; then
        # Instalación antigua: enlace a nixos-<equipo>/configuration.nix del repo
        destino=$(readlink "$conf")
        if [[ "$destino" =~ /nixos-([a-z0-9-]+)/configuration\.nix$ ]]; then
            printf '%s' "${BASH_REMATCH[1]}"
        fi
    elif [ -f "$conf" ]; then
        grep -oP 'nixos/equipos/\K[a-z0-9-]+' "$conf" 2> /dev/null | head -1 || true
    fi
}

# Devuelve el nombre del equipo: el argumento, el de /etc/nixos o el que elija el usuario
elegir_equipo() {
    local equipo="${1:-}"
    [ -n "$equipo" ] || equipo=$(equipo_actual)
    if [ -z "$equipo" ]; then
        [ -t 0 ] || error "Indica el equipo: ./init.sh sistema <equipo>"
        local opciones
        mapfile -t opciones < <(equipos_del_repo)
        printf '  ¿Qué equipo es esta máquina?\n' >&2
        PS3="  Número: "
        select opcion in "${opciones[@]}" "Nuevo equipo..."; do
            [ -n "$opcion" ] && break
        done
        if [ "$opcion" = "Nuevo equipo..." ]; then
            read -rp "  Nombre del equipo nuevo (ej. laptop-hp): " equipo
        else
            equipo="$opcion"
        fi
    fi
    printf '%s' "$equipo"
}

nuevo_equipo() {
    local nombre="$1" destino="$DOTFILES/nixos/equipos/$1" version
    [[ "$nombre" =~ ^[a-z0-9][a-z0-9-]*$ ]] || error "Nombre de equipo inválido: '$nombre' (minúsculas, números y guiones)"
    [ "$nombre" != "plantilla" ] || error "'plantilla' está reservado"
    if [ -e "$destino" ]; then
        ok "El equipo $nombre ya existe"
        return
    fi
    # stateVersion: la de la instalación de esta máquina (configuration.nix del instalador)
    version=$(grep -oP 'system\.stateVersion\s*=\s*"\K[0-9.]+' /etc/nixos/configuration.nix 2> /dev/null || true)
    [ -n "$version" ] || version=$(nixos-version | cut -d. -f1,2)
    mkdir -p "$destino"
    sed -e "s/@EQUIPO@/$nombre/g" -e "s/@VERSION@/$version/g" \
        "$DOTFILES/nixos/equipos/plantilla/default.nix" > "$destino/default.nix"
    ok "Creado nixos/equipos/$nombre (stateVersion $version)"
    aviso "Revisa los módulos que importa nixos/equipos/$nombre/default.nix y súbelo con git"
    [ -d /sys/firmware/efi ] || aviso "Esta máquina arranca en modo BIOS: ajusta boot.loader.grub en nixos/equipos/$nombre/default.nix"
}

# =============================================================================
# PASOS
# =============================================================================

paso_usuario() {
    titulo "Usuario: config/, tema y archivos locales"
    mkdir -p "$HOME/.config" "$HOME/Imágenes/CapturasPantalla"

    for app in hypr waybar kitty rofi mako fastfetch gtk-3.0 gtk-4.0; do
        enlazar "$DOTFILES/config/$app" "$HOME/.config/$app"
    done
    enlazar "$DOTFILES/config/gtkrc-2.0" "$HOME/.gtkrc-2.0"
    enlazar "$DOTFILES/config/gtkrc-2.0" "$HOME/.config/gtkrc"
    ok "Configuraciones de config/ enlazadas en ~/.config"

    # Archivos locales de esta máquina (no versionados)
    if [ ! -f "$DOTFILES/config/hypr/local.conf" ]; then
        cat > "$DOTFILES/config/hypr/local.conf" <<'EOF'
# Ajustes solo de esta máquina (no se versiona; lo creó init.sh).
# Se carga al final de hyprland.conf, así que puede sobrescribir cualquier valor.
# Ejemplos:
# monitor = eDP-1, 1920x1080@60, 0x0, 1
# input {
#     touchpad {
#         natural_scroll = true
#     }
# }
EOF
        ok "Creado config/hypr/local.conf (monitores, touchpad de esta máquina)"
    fi
    if [ ! -f "$DOTFILES/.env" ]; then
        cp "$DOTFILES/.env.example" "$DOTFILES/.env"
        aviso "Creado .env desde .env.example: completa tus valores"
    fi
    chmod 600 "$DOTFILES/.env"

    find "$DOTFILES" -name '*.sh' -not -path '*/.git/*' -exec chmod +x {} +
    ok "Permisos de ejecución en los scripts"

    # Restos de versiones anteriores de init.sh
    if [ -L "$HOME/.local/share/icons/icons" ]; then
        rm "$HOME/.local/share/icons/icons"
        ok "Quitado el enlace antiguo ~/.local/share/icons/icons"
    fi
    if [ -f "$HOME/.bash_profile" ] && grep -q '^export XCURSOR_PATH=.*~/\.icons' "$HOME/.bash_profile"; then
        sed -i -e '/^export XCURSOR_PATH=.*~\/\.icons/d' -e '/^export XCURSOR_THEME=/d' "$HOME/.bash_profile"
        ok "Quitadas de ~/.bash_profile las variables del cursor (ya las define NixOS)"
    fi

    # Tema: crea tema/tema.conf si falta, genera los tema.* de config/ y el cursor
    if "$DOTFILES/utils/aplicar-tema.sh" > /dev/null; then
        ok "Tema aplicado ($(basename "$(readlink "$DOTFILES/tema/tema.conf")" .conf)); cambiarlo con SUPER + F2"
    else
        aviso "No se pudo aplicar el tema (utils/aplicar-tema.sh)"
    fi
}

paso_sistema() {
    titulo "Sistema: NixOS"
    local equipo
    equipo=$(elegir_equipo "${1:-}")
    [[ "$equipo" =~ ^[a-z0-9][a-z0-9-]*$ ]] || error "Equipo inválido o sin elegir: '$equipo'"
    [ -d "$DOTFILES/nixos/equipos/$equipo" ] || nuevo_equipo "$equipo"
    ok "Equipo: $equipo (nixos/equipos/$equipo)"
    pedir_sudo

    local hw=/etc/nixos/hardware-configuration.nix conf=/etc/nixos/configuration.nix

    # 1. Hardware: siempre el de ESTA máquina y fuera del repo. Un enlace al repo
    #    puede apuntar al hardware de otra PC (deja el sistema sin arrancar): se regenera.
    local regenerar=0
    if [ -L "$hw" ]; then
        if [ -f "$hw" ]; then
            como_root cp "$(readlink -f "$hw")" "$hw.respaldo-$FECHA"
        fi
        como_root rm "$hw"
        ok "Quitado el enlace de hardware-configuration.nix al repo"
        regenerar=1
    elif [ ! -f "$hw" ]; then
        regenerar=1
    fi
    if [ "$regenerar" = 0 ]; then
        ok "hardware-configuration.nix local de esta máquina (se conserva)"
    elif [ "$SIMULAR" = 1 ]; then
        printf '  [simular] sudo nixos-generate-config --show-hardware-config > %s\n' "$hw"
    else
        sudo nixos-generate-config --show-hardware-config | escribir_root "$hw"
        ok "Generado $hw para esta máquina"
    fi

    # 2. configuration.nix: solo importa el hardware local y el equipo del repo
    local contenido
    contenido="# Generado por $DOTFILES/init.sh: no editar.
# El sistema se define en el repo (equipo \"$equipo\"); el hardware es el archivo local de al lado.
{
  imports = [
    ./hardware-configuration.nix
    $DOTFILES/nixos/equipos/$equipo
  ];
}"
    if [ -f "$conf" ] && [ ! -L "$conf" ] && [ "$(cat "$conf")" = "$contenido" ]; then
        ok "$conf ya apunta al equipo $equipo"
    else
        if [ -L "$conf" ]; then
            como_root rm "$conf"
        elif [ -e "$conf" ]; then
            como_root mv "$conf" "$conf.respaldo-$FECHA"
            ok "Respaldado el configuration.nix anterior en $conf.respaldo-$FECHA"
        fi
        printf '%s\n' "$contenido" | escribir_root "$conf"
        ok "Escrito $conf"
    fi

    # 3. Construir y activar
    if como_root nixos-rebuild switch; then
        ok "Sistema actualizado (GRUB, login y paquetes)"
    else
        error "nixos-rebuild falló. Revisa el error; los archivos anteriores quedaron en /etc/nixos/*.respaldo-$FECHA"
    fi
}

paso_apps() {
    titulo "Aplicaciones fuera de nixpkgs"
    if command -v flatpak > /dev/null; then
        flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo \
            || aviso "No se pudo añadir Flathub"
        if flatpak info app.zen_browser.zen > /dev/null 2>&1; then
            ok "Zen Browser ya instalado"
        elif flatpak install -y --noninteractive flathub app.zen_browser.zen; then
            ok "Zen Browser instalado"
        else
            aviso "No se pudo instalar Zen Browser (flatpak install flathub app.zen_browser.zen)"
        fi
    else
        aviso "flatpak no está instalado: primero ./init.sh sistema"
    fi

    local appimage="$HOME/.local/bin/appimages/Thorium.AppImage"
    if [ -f "$appimage" ]; then
        ok "Thorium ya descargado"
    else
        mkdir -p "$(dirname "$appimage")"
        if wget -q --show-progress -O "$appimage.tmp" "$THORIUM_URL"; then
            mv "$appimage.tmp" "$appimage"
            chmod +x "$appimage"
            ok "Thorium descargado"
        else
            rm -f "$appimage.tmp"
            aviso "No se pudo descargar Thorium"
        fi
    fi
    [ -f "$appimage" ] && enlazar "$DOTFILES/applications/thorium.desktop" "$HOME/.local/share/applications/thorium.desktop"
    return 0
}

paso_red() {
    titulo "Red: Tailscale"
    if ! command -v tailscale > /dev/null; then
        aviso "tailscale no está instalado: primero ./init.sh sistema"
    elif tailscale status > /dev/null 2>&1; then
        ok "Tailscale ya tiene sesión"
    else
        pedir_sudo
        como_root tailscale up || aviso "No se pudo iniciar sesión en Tailscale (sudo tailscale up)"
    fi
}

paso_actualizar() {
    titulo "Actualizar el repo"
    git -C "$DOTFILES" pull --rebase --autostash || error "git pull falló: resuelve el conflicto y vuelve a ejecutar"
    ok "Repo al día"
    paso_usuario
    paso_sistema
}

resumen() {
    titulo "Listo"
    if [ "${#AVISOS[@]}" -gt 0 ]; then
        printf '  Revisar:\n'
        printf '    - %s\n' "${AVISOS[@]}"
    fi
    if [ "$SIMULAR" = 1 ]; then
        printf '  Modo simulación: no se ejecutó nada con sudo.\n'
    fi
}

# =============================================================================

main() {
    local args=()
    for arg in "$@"; do
        case "$arg" in
            --simular) SIMULAR=1 ;;
            -h | --help) ayuda; exit 0 ;;
            *) args+=("$arg") ;;
        esac
    done

    [ "$EUID" -ne 0 ] || error "Ejecuta ./init.sh con tu usuario (pide sudo cuando lo necesita)"
    [ "$DOTFILES" = "$HOME/dotfiles" ] || error "El repo debe estar en ~/dotfiles (las configs usan esa ruta); está en $DOTFILES"

    case "${args[0]:-todo}" in
        todo)         paso_usuario; paso_sistema "${args[1]:-}"; paso_apps; paso_red ;;
        usuario)      paso_usuario ;;
        sistema)      paso_sistema "${args[1]:-}" ;;
        apps)         paso_apps ;;
        red)          paso_red ;;
        actualizar)   paso_actualizar ;;
        nuevo-equipo) [ -n "${args[1]:-}" ] || error "Uso: ./init.sh nuevo-equipo <nombre>"
                      nuevo_equipo "${args[1]}" ;;
        *)            ayuda; exit 1 ;;
    esac
    resumen
}

main "$@"
