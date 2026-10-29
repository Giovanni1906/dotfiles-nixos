#!/usr/bin/env bash
# Leer el texto que wl-paste nos envía
texto="$(cat)"

[ -f "$HOME/dotfiles/.env" ] && source "$HOME/dotfiles/.env"
[ -n "${VALENT_DEVICE_ID:-}" ] || exit 0

# Escapar comillas dobles para mantener la sintaxis de gdbus intacta
texto_escapado="${texto//\"/\\\"}"

# Inyectar el texto directamente a Valent
gdbus call --session --dest ca.andyholmes.Valent --object-path "/ca/andyholmes/Valent/Device/$VALENT_DEVICE_ID" --method org.gtk.Actions.Activate "share.text" "[<\"$texto_escapado\">]" "{}" > /dev/null 2>&1
