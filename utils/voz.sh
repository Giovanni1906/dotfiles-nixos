#!/usr/bin/env bash
# Módulo de voz reutilizable: pitido y/o texto en español.
# Uso:
#   voz.sh "texto"            → pitido + habla el texto
#   voz.sh --sonido           → solo pitido (complete.oga)
#   voz.sh --alerta           → solo pitido de alerta (dialog-warning.oga)
#   voz.sh --silencio "texto" → solo habla, sin pitido
#
# Motor TTS principal: Piper TTS (red neuronal local, voz natural).
# Modelos en: ~/.local/share/piper/
# Configuración opcional en: ~/.config/dotfiles/voz.conf (modelo=...)
# Respaldo: espeak-ng (si piper o el modelo no están disponibles).

SONIDOS="/run/current-system/sw/share/sounds/freedesktop/stereo"

_pitido() {
    local archivo="${1:-$SONIDOS/complete.oga}"
    paplay "$archivo" 2>/dev/null \
        || paplay "$SONIDOS/message-new-instant.oga" 2>/dev/null \
        || true
}

_buscar_piper() {
    if command -v piper >/dev/null 2>&1; then
        command -v piper
        return 0
    fi
    find /nix/store -maxdepth 3 -name piper -type f -executable 2>/dev/null | head -n1
}

_asegurar_modelo_piper() {
    local piper_dir="${XDG_DATA_HOME:-$HOME/.local/share}/piper"
    local modelo_defecto="$piper_dir/es_MX-claude-high.onnx"
    local json_defecto="$piper_dir/es_MX-claude-high.onnx.json"
    local base_url="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_MX/claude/high"

    if [ ! -f "$modelo_defecto" ] || [ ! -f "$json_defecto" ]; then
        if command -v curl >/dev/null 2>&1; then
            mkdir -p "$piper_dir"
            curl -sSL -o "$modelo_defecto.tmp" "$base_url/es_MX-claude-high.onnx" \
                && mv "$modelo_defecto.tmp" "$modelo_defecto" 2>/dev/null || rm -f "$modelo_defecto.tmp"
            curl -sSL -o "$json_defecto.tmp" "$base_url/es_MX-claude-high.onnx.json" \
                && mv "$json_defecto.tmp" "$json_defecto" 2>/dev/null || rm -f "$json_defecto.tmp"
        fi
    fi
}

_hablar() {
    local texto="${1:-}"
    [ -z "$texto" ] && return

    local piper_bin
    piper_bin=$(_buscar_piper)

    local piper_dir="${XDG_DATA_HOME:-$HOME/.local/share}/piper"
    # Prioridad de modelos naturales:
    # 1. Configurado por el usuario en ~/.config/dotfiles/voz.conf
    # 2. es_MX-claude-high (latino neutro/mexicano, alta fidelidad)
    # 3. es_ES-sharvard-medium (español peninsular natural)
    # 4. es_MX-ald-medium / es_ES-davefx-medium
    local modelo=""
    local config_voz="${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/voz.conf"
    if [ -f "$config_voz" ]; then
        local custom
        custom=$(grep "^modelo=" "$config_voz" 2>/dev/null | cut -d= -f2-)
        [ -n "$custom" ] && [ -f "$custom" ] && modelo="$custom"
    fi

    if [ -z "$modelo" ]; then
        _asegurar_modelo_piper
        for candidato in \
            "$piper_dir/es_MX-claude-high.onnx" \
            "$piper_dir/es_ES-sharvard-medium.onnx" \
            "$piper_dir/es_MX-ald-medium.onnx" \
            "$piper_dir/es_ES-davefx-medium.onnx"; do
            if [ -f "$candidato" ]; then
                modelo="$candidato"
                break
            fi
        done
    fi

    # 1. Intento con Piper TTS (Voz neuronal humana)
    if [ -n "$piper_bin" ] && [ -n "$modelo" ] && [ -f "$modelo" ] && command -v paplay >/dev/null 2>&1; then
        echo "$texto" | "$piper_bin" --model "$modelo" --output-raw 2>/dev/null \
            | paplay --raw --rate=22050 --channels=1 --format=s16le 2>/dev/null \
            && return 0
    fi

    # 2. Respaldo: espeak-ng
    command -v espeak-ng >/dev/null 2>&1 \
        && espeak-ng -v es-419 -s 145 -a 90 -- "$texto" 2>/dev/null \
        || true
}

case "${1:-}" in
    --sonido)
        _pitido
        ;;
    --alerta)
        _pitido "$SONIDOS/dialog-warning.oga"
        ;;
    --silencio)
        _hablar "${2:-}"
        ;;
    "")
        _pitido
        ;;
    *)
        _pitido
        sleep 0.4
        _hablar "$1"
        ;;
esac
