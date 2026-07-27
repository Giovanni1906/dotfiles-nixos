# Leer el texto que wl-paste nos envía
texto="$(cat)"

# Escapar comillas dobles para mantener la sintaxis de gdbus intacta
texto_escapado="${texto//\"/\\\"}"

# Inyectar el texto directamente a Valent
gdbus call --session --dest ca.andyholmes.Valent --object-path /ca/andyholmes/Valent/Device/9f91b45437b94e139957b9d336079ea0 --method org.gtk.Actions.Activate "share.text" "[<\"$texto_escapado\">]" "{}" > /dev/null 2>&1
