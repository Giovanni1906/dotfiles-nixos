#!/usr/bin/env bash
# =============================================================================
# Puente lanzador de Bugsito (antes Jarvis) desde Dotfiles (SUPER + SPACE)
# =============================================================================
# Busca el repositorio o ejecutable de Bugsito instalado en:
#   1. ~/dotfiles/bugsito/bugsito.sh  (submódulo integrado en dotfiles)
#   2. ~/.local/bin/bugsito
#   3. ~/Proyectos/bugsito/bugsito.sh
#   4. ~/Proyectos/personal/bugsito/bugsito.sh
#   5. ~/.local/share/bugsito/bugsito.sh
# Si no está instalado en esta máquina, avisa con notify-send cómo instalarlo.

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for cand in \
    "$DOTFILES_DIR/bugsito/bugsito.sh" \
    "$HOME/.local/bin/bugsito" \
    "$HOME/Proyectos/bugsito/bugsito.sh" \
    "$HOME/Proyectos/personal/bugsito/bugsito.sh" \
    "$HOME/.local/share/bugsito/bugsito.sh"; do
    if [[ -x "$cand" ]]; then
        exec "$cand" "$@"
    fi
done

if command -v bugsito >/dev/null 2>&1; then
    exec bugsito "$@"
fi

if command -v notify-send >/dev/null 2>&1; then
    notify-send -u normal "Bugsito no instalado" "Ejecuta: ~/dotfiles/init.sh bugsito"
fi
printf 'Bugsito no está instalado. Instálalo ejecutando: ~/dotfiles/init.sh bugsito\n' >&2
exit 1
