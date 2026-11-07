#!/usr/bin/env bash
# Configura el hook Stop de Claude Code para notificaciones de IA.
# Idempotente: no duplica si el hook ya está registrado.
# Llamado por: nixos/modulos/ia.nix (userActivationScripts) e init.sh (paso_usuario).

SETTINGS="$HOME/.claude/settings.json"
HOOK_CMD="~/dotfiles/utils/ia-notificacion.sh"

mkdir -p "$(dirname "$SETTINGS")"

python3 - "$SETTINGS" "$HOOK_CMD" <<'PYEOF'
import json, os, sys

settings_file = sys.argv[1]
hook_command  = sys.argv[2]

try:
    with open(settings_file) as f:
        settings = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    settings = {}

stop_hooks = settings.setdefault("hooks", {}).setdefault("Stop", [])

already = any(
    h.get("command") == hook_command
    for entry in stop_hooks
    for h in entry.get("hooks", [])
)

if already:
    sys.exit(0)

stop_hooks.append({
    "matcher": "",
    "hooks": [{"type": "command", "command": hook_command}]
})

with open(settings_file, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")

print(f"Hook Stop configurado en {settings_file}")
PYEOF
