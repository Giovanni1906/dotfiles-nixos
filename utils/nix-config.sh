#!/usr/bin/env bash
# =============================================================================
# NIX-CONFIG: menú para elegir qué parte de la configuración de NixOS editar
# =============================================================================
# Uso: nix-config [equipo]   (sin equipo, usa el de /etc/nixos/configuration.nix)
#
# Muestra lo que se edita a mano: los módulos que usa el equipo, sus paquetes y
# alias propios, y las partes de cada módulo (secciones, paquetes, alias…).
# Abre micro en la línea elegida y ofrece aplicar con nixos-rebuild switch.

set -uo pipefail

DOTFILES="$HOME/dotfiles"
MODULOS="$DOTFILES/nixos/modulos"
EDITOR_NIX=$(command -v micro || printf '%s' "${EDITOR:-nano}")

# --- SALIDA ---
titulo() { printf '\n  \033[1;36m%s\033[0m\n' "$*"; }
ok()     { printf '  \033[32m✓\033[0m %s\n' "$*"; }
aviso()  { printf '  \033[33m!\033[0m %s\n' "$*"; }
error()  { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
tenue()  { printf '\033[2m%s\033[0m' "$*"; }
pausa()  { read -rp "  Enter para volver " _; }

[ -t 0 ] || error "nix-config es interactivo: ábrelo en una terminal"

EQUIPO="${1:-}"
[ -n "$EQUIPO" ] || EQUIPO=$(grep -oP 'nixos/equipos/\K[a-z0-9-]+' /etc/nixos/configuration.nix 2> /dev/null | head -1)
EQUIPO_NIX="$DOTFILES/nixos/equipos/$EQUIPO/default.nix"
[ -n "$EQUIPO" ] && [ -f "$EQUIPO_NIX" ] || error "No encuentro el equipo '$EQUIPO'. Uso: nix-config <equipo>"

# --- MÓDULOS ---
# Primero en el orden de imports del equipo (activos o comentados), luego el resto
modulos() {
    {
        grep -oP '^\s*(#\s*)?\.\./\.\./modulos/\K[a-z0-9-]+(?=\.nix)' "$EQUIPO_NIX"
        for f in "$MODULOS"/*.nix; do basename "$f" .nix; done
    } | awk '!visto[$0]++' | while read -r m; do
        [ -f "$MODULOS/$m.nix" ] && printf '%s\n' "$m"
    done
}

activo() { grep -qE "^[[:space:]]*\.\./\.\./modulos/$1\.nix" "$EQUIPO_NIX"; }

# La línea 2 de cada módulo: "# NOMBRE: descripción"
descripcion() { sed -n '2s/^# [^:]*: *//p' "$MODULOS/$1.nix"; }

# Comenta o descomenta el módulo en imports; si no está en la lista, lo añade
alternar_modulo() {
    local m="$1" n
    n=$(grep -nE "^[[:space:]]*(#[[:space:]]*)?\.\./\.\./modulos/$m\.nix" "$EQUIPO_NIX" | head -1 | cut -d: -f1)
    if [ -z "$n" ]; then
        n=$(awk '/^[[:space:]]*imports[[:space:]]*=/ { dentro = 1 }
                 dentro && /^[[:space:]]*\];/ { print NR; exit }' "$EQUIPO_NIX")
        [ -n "$n" ] || { aviso "No encuentro la lista imports del equipo"; pausa; return; }
        sed -i "${n}i\\    ../../modulos/$m.nix" "$EQUIPO_NIX"
    elif sed -n "${n}p" "$EQUIPO_NIX" | grep -qE '^[[:space:]]*#'; then
        sed -i -E "${n}s|#[[:space:]]*(\.\./\.\./modulos/)|\1|" "$EQUIPO_NIX"
    else
        sed -i "${n}s|\.\./\.\./modulos/|# ../../modulos/|" "$EQUIPO_NIX"
    fi
}

# --- PARTES DE UN ARCHIVO ---
# Imprime "línea<TAB>nombre" por cada sección con banner y cada bloque conocido
# (paquetes, alias, fuentes…). Un bloque justo debajo de un banner se une a él.
partes() {
    awk '
        function recortar(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }
        function guardar(linea, nombre) { n++; L[n] = linea; N[n] = nombre }
        function banner(linea, t) { if (en_let) t = t " (diseño)"; guardar(linea, t); ultimo_banner = n }

        /^let[[:space:]]*$/ { en_let = 1 }
        /^in[[:space:]]*$/  { en_let = 0 }

        # Banner de una línea: # --- Título ---
        /^[[:space:]]*# -{3}[[:space:]]+[^-[:space:]].*-{3}[[:space:]]*$/ {
            t = $0; sub(/^[[:space:]]*# -+/, "", t); sub(/-+[[:space:]]*$/, "", t)
            banner(NR, recortar(t)); next
        }
        # Banner de tres líneas: # ------ / # Título: detalle / # ------
        /^[[:space:]]*# -{20,}[[:space:]]*$/ {
            if (candidato != "" && linea_candidato == NR - 1) banner(linea_candidato, candidato)
            candidato = ""; raya = NR; next
        }
        raya && raya == NR - 1 && /^[[:space:]]*# [^-]/ {
            t = $0; sub(/^[[:space:]]*# /, "", t); sub(/:.*/, "", t)
            candidato = recortar(t); linea_candidato = NR; next
        }
        /^[[:space:]]*#/ { next }

        {
            nombre = ""
            if      ($0 ~ /^[[:space:]]*imports[[:space:]]*=/)                 nombre = "Módulos que importa"
            else if ($0 ~ /^[[:space:]]*dotfiles\.(equipo|usuario)[[:space:]]*=/) nombre = "Equipo y usuario"
            else if ($0 ~ /networking\.hostName[[:space:]]*=/)                nombre = "Nombre en la red"
            else if ($0 ~ /boot\.loader\./)                                   nombre = "Arranque"
            else if ($0 ~ /boot\.kernelParams[[:space:]]*=/)                  nombre = "Parámetros del kernel"
            else if ($0 ~ /environment\.systemPackages[[:space:]]*=/)         nombre = "Paquetes"
            else if ($0 ~ /environment\.shellAliases[[:space:]]*=/)           nombre = "Alias"
            else if ($0 ~ /users\.users\..*\.packages[[:space:]]*=/)          nombre = "Paquetes del usuario"
            else if ($0 ~ /users\.users\..*\.extraGroups[[:space:]]*=/)       nombre = "Grupos del usuario"
            else if ($0 ~ /fonts\.packages[[:space:]]*=/)                     nombre = "Fuentes"
            else if ($0 ~ /networking\.firewall/)                             nombre = "Firewall (puertos)"
            else if ($0 ~ /networking\.extraHosts[[:space:]]*=/)              nombre = "Dominios locales (hosts)"
            else if ($0 ~ /virtualisation\./)                                 nombre = "Virtualización"
            else if ($0 ~ /^[[:space:]]*services\./)                          nombre = "Servicios"
            else if ($0 ~ /^[[:space:]]*programs\./)                          nombre = "Programas"
            if (nombre == "" || visto[nombre]++) next
            # Tras el primer banner, las etiquetas genéricas ya quedan nombradas por él
            if (ultimo_banner && nombre ~ /^(Servicios|Programas|Virtualización)$/) next

            if (ultimo_banner && ultimo_banner == n && NR - L[n] <= 3) {
                if ((nombre == "Paquetes" || nombre == "Alias") && index(tolower(N[n]), tolower(nombre)) == 0)
                    N[n] = N[n] " (" tolower(nombre) ")"
                next
            }
            guardar(NR, nombre)
        }

        END { for (i = 1; i <= n; i++) printf "%d\t%s\n", L[i], N[i] }
    ' "$1"
}

editar() {
    if [ -n "${2:-}" ]; then "$EDITOR_NIX" "$1" "+$2"; else "$EDITOR_NIX" "$1"; fi
}

# --- CAMBIOS SIN APLICAR ---
huella() { md5sum "$MODULOS"/*.nix "$DOTFILES"/nixos/equipos/*/default.nix 2> /dev/null; }
APLICADO=$(huella)

# Archivos de nixos/ que cambiaron desde que se abrió el menú (o desde el último switch)
pendientes() {
    diff <(printf '%s\n' "$APLICADO") <(huella) | sed -n "s|^> [0-9a-f]*  $DOTFILES/nixos/||p"
}

aplicar() {
    titulo "nixos-rebuild switch"
    if sudo nixos-rebuild switch; then
        APLICADO=$(huella)
        ok "Sistema actualizado"
        local sin_subir
        sin_subir=$(git -C "$DOTFILES" status --short -- nixos)
        if [ -n "$sin_subir" ]; then
            aviso "Cambios sin subir a git (git add, commit y push para llevarlos a los otros equipos):"
            printf '%s\n' "$sin_subir" | sed 's/^/      /'
        fi
    else
        aviso "nixos-rebuild falló: corrige la parte que indica el error y vuelve a aplicar"
    fi
}

ver_cambios() {
    if git -C "$DOTFILES" diff --quiet -- nixos; then
        ok "nixos/ no tiene cambios respecto a git"
        pausa
    else
        git -C "$DOTFILES" diff -- nixos
    fi
}

salir() {
    local cambios r
    cambios=$(pendientes)
    if [ -n "$cambios" ]; then
        aviso "Sin aplicar: ${cambios//$'\n'/ }"
        read -rp "  ¿Aplicar ahora con nixos-rebuild switch? [s/N] " r
        [[ "$r" =~ ^[sS] ]] && aplicar
    fi
    exit 0
}

# --- PAQUETES Y ALIAS DEL EQUIPO ---
# Abre el bloque $1 del equipo en su primera entrada; si no existe, lo crea antes
# de system.stateVersion. Argumentos: atributo, apertura, cierre, nombre, comentario.
seccion_equipo() {
    local atributo="$1" apertura="$2" cierre="$3" nombre="$4" comentario="$5" n r tmp
    n=$(grep -nE "^[[:space:]]*${atributo//./\\.}[[:space:]]*=" "$EQUIPO_NIX" | head -1 | cut -d: -f1)
    if [ -z "$n" ]; then
        read -rp "  $EQUIPO aún no tiene $nombre propios. ¿Crear la sección? [S/n] " r
        [[ "$r" =~ ^[nN] ]] && return
        n=$(grep -nE '^[[:space:]]*# Versión de NixOS|^[[:space:]]*system\.stateVersion' "$EQUIPO_NIX" | head -1 | cut -d: -f1)
        [ -n "$n" ] || n=$(grep -n '^}' "$EQUIPO_NIX" | tail -1 | cut -d: -f1)
        tmp=$(mktemp)
        awk -v n="$n" -v bloque="  # $comentario\n  $atributo = $apertura\n\n  $cierre\n\n" \
            'NR == n { printf "%s", bloque } { print }' "$EQUIPO_NIX" > "$tmp"
        cat "$tmp" > "$EQUIPO_NIX"
        rm -f "$tmp"
        n=$((n + 1))
        # with pkgs necesita pkgs en los argumentos del archivo ({ ... }: → { pkgs, ... }:)
        if [[ "$apertura" == *pkgs* ]] && ! grep -qE '^\{[^}]*\bpkgs\b[^}]*\}:' "$EQUIPO_NIX"; then
            sed -i -E '0,/^\{ *(.*)\}:[[:space:]]*$/s//{ pkgs, \1}:/' "$EQUIPO_NIX"
        fi
    fi
    editar "$EQUIPO_NIX" "$((n + 1))"
}

# --- MENÚS ---
menu_modulos() {
    local op m i marca
    local -a lista
    while true; do
        clear
        titulo "Módulos de $EQUIPO"
        printf '  %s\n\n' "$(tenue "Escribe el número para activar o quitar un módulo.")"
        lista=()
        i=0
        while read -r m; do
            if [ "$m" = base ]; then
                printf '      \033[32m✓\033[0m %-12s %s\n' base "$(tenue "siempre (define el equipo y el usuario)")"
                continue
            fi
            i=$((i + 1))
            lista[i]="$m"
            if activo "$m"; then marca='\033[32m✓\033[0m'; else marca='\033[2m·\033[0m'; fi
            printf '  %2d) %b %-12s %s\n' "$i" "$marca" "$m" "$(descripcion "$m")"
        done < <(modulos)
        printf '\n'
        read -rp "  Módulo (Enter para volver): " op
        [ -n "$op" ] || return
        if [[ "$op" =~ ^[0-9]+$ ]] && [ -n "${lista[op]:-}" ]; then
            alternar_modulo "${lista[op]}"
        fi
    done
}

menu_partes() {
    local archivo="$1" nombre="$2" op i
    local -a lista
    while true; do
        clear
        titulo "$nombre"
        printf '  %s\n\n' "$(tenue "${archivo#"$DOTFILES"/}")"
        mapfile -t lista < <(partes "$archivo")
        for i in "${!lista[@]}"; do
            printf '  %2d) %s  %s\n' "$((i + 1))" "${lista[i]#*$'\t'}" "$(tenue "línea ${lista[i]%%$'\t'*}")"
        done
        printf '   0) Archivo completo\n\n'
        read -rp "  Parte (Enter para volver): " op
        [ -n "$op" ] || return
        if [ "$op" = 0 ]; then
            editar "$archivo"
        elif [[ "$op" =~ ^[0-9]+$ ]] && [ "$op" -le "${#lista[@]}" ]; then
            editar "$archivo" "${lista[op - 1]%%$'\t'*}"
        fi
    done
}

menu_principal() {
    local op m i cambios
    local -a opciones
    while true; do
        clear
        printf '\n  \033[1;36mnix-config\033[0m · equipo \033[1m%s\033[0m\n' "$EQUIPO"
        cambios=$(pendientes)
        [ -z "$cambios" ] || aviso "Sin aplicar: ${cambios//$'\n'/ }"

        printf '\n  \033[1mSolo esta máquina\033[0m  %s\n' "$(tenue "nixos/equipos/$EQUIPO/default.nix")"
        printf '   1) Activar o quitar módulos\n'
        printf '   2) Paquetes\n'
        printf '   3) Alias\n'
        printf '   4) Otras partes (arranque, nombre, usuario…)\n'

        printf '\n  \033[1mMódulos\033[0m  %s\n' "$(tenue "lo que cambies llega a todos los equipos que los usan")"
        opciones=()
        i=4
        while read -r m; do
            i=$((i + 1))
            opciones[i]="$m"
            if activo "$m" || [ "$m" = base ]; then
                printf '  %2d) %-12s %s\n' "$i" "$m" "$(descripcion "$m")"
            else
                printf '  %2d) %s\n' "$i" "$(tenue "$(printf '%-12s %s · no lo usa este equipo' "$m" "$(descripcion "$m")")")"
            fi
        done < <(modulos)

        printf '\n   d) Ver los cambios (git diff)\n'
        printf '   a) Aplicar los cambios (nixos-rebuild switch)\n\n'
        read -rp "  Opción (Enter para salir): " op
        case "$op" in
            "" | s | S | q | Q) salir ;;
            1) menu_modulos ;;
            2) seccion_equipo environment.systemPackages "with pkgs; [" "];" "paquetes" \
                   "Paquetes solo de esta máquina (cada uno con un comentario de para qué sirve)" ;;
            3) seccion_equipo environment.shellAliases "{" "};" "alias" "Alias solo de esta máquina" ;;
            4) menu_partes "$EQUIPO_NIX" "Equipo $EQUIPO" ;;
            d | D) ver_cambios ;;
            a | A) aplicar; pausa ;;
            *)
                if [[ "$op" =~ ^[0-9]+$ ]] && [ -n "${opciones[op]:-}" ]; then
                    m="${opciones[op]}"
                    menu_partes "$MODULOS/$m.nix" "Módulo $m · $(descripcion "$m")"
                fi
                ;;
        esac
    done
}

menu_principal
