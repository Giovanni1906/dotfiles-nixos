#!/usr/bin/env bash
# Módulo de voz reutilizable: pitido y/o texto en español.
# Uso:
#   voz.sh "texto"            → pitido + habla el texto
#   voz.sh --sonido           → solo pitido (complete.oga)
#   voz.sh --alerta           → solo pitido de alerta (dialog-warning.oga)
#   voz.sh --silencio "texto" → solo habla, sin pitido
#
# Motor TTS: espeak-ng (nixos/modulos/ia.nix).
# Mejora futura: piper-tts con modelo es_ES-mls-medium para voz más natural.

SONIDOS="/run/current-system/sw/share/sounds/freedesktop/stereo"

_pitido() {
    local archivo="${1:-$SONIDOS/complete.oga}"
    paplay "$archivo" 2>/dev/null \
        || paplay "$SONIDOS/message-new-instant.oga" 2>/dev/null \
        || true
}

_hablar() {
    local texto="${1:-}"
    [ -z "$texto" ] && return
    command -v espeak-ng >/dev/null 2>&1 \
        && espeak-ng -v es+m1 -s 145 -a 90 -- "$texto" 2>/dev/null \
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
