#!/usr/bin/env bash
# Ocultar o mostrar las notificaciones de Mako (SUPER + F4).
# El modo "ocultas" las deja invisibles; al quitarlo vuelven las que no caducaron.
# El aviso de estado usa app-name Notificaciones para seguir viéndose en ese modo.
# aplicar-tema.sh escribe el modo en todas las PCs. Si esta aún no ha vuelto a
# aplicar el tema, se añade a su config generada (no se versiona).

CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/mako/config"

if ! command -v makoctl > /dev/null; then
    echo "Mako no está disponible" >&2
    exit 1
fi

if ! makoctl mode > /dev/null 2>&1; then
    notify-send -u critical "Notificaciones" "Mako no está en marcha" 2>/dev/null || true
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    notify-send -u critical "Notificaciones" "Falta la config de Mako. Ejecuta tema-aplicar." 2>/dev/null || true
    exit 1
fi

if ! grep -q '^\[mode=ocultas\]$' "$CONFIG"; then
    cat >> "$CONFIG" <<'EOF'

# SUPER + F4: modo "ocultas" esconde las que hay y las nuevas. El aviso de estado sigue visible.
[mode=ocultas]
invisible=1

[mode=ocultas app-name=Notificaciones]
invisible=0
EOF
    makoctl reload > /dev/null
fi

if makoctl mode | grep -qx 'ocultas'; then
    makoctl mode -r ocultas > /dev/null
    notify-send -a Notificaciones -t 4000 "Notificaciones" "Visibles"
else
    makoctl mode -a ocultas > /dev/null
    notify-send -a Notificaciones -t 4000 "Notificaciones" "Ocultas"
fi
