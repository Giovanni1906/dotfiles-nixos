#!/usr/bin/env bash
# Configura los hooks Stop de agentes de IA (Claude Code y Antigravity).
# Idempotente: no duplica si los hooks ya están registrados.
# Compatible con Node.js y Python 3.
# Llamado por: nixos/modulos/ia.nix (userActivationScripts) e init.sh (paso_usuario).

CLAUDE_SETTINGS="$HOME/.claude/settings.json"
AGY_HOOKS="$HOME/.gemini/config/hooks.json"
HOOK_CMD="~/dotfiles/utils/ia-notificacion.sh"

mkdir -p "$(dirname "$CLAUDE_SETTINGS")" "$(dirname "$AGY_HOOKS")"

_configurar_con_node() {
    node - "$CLAUDE_SETTINGS" "$AGY_HOOKS" "$HOOK_CMD" <<'JSEOF'
const fs = require('fs');
const [claudeFile, agyFile, hookCmd] = process.argv.slice(2);

// 1. Claude Code
try {
  let settings = {};
  try {
    settings = JSON.parse(fs.readFileSync(claudeFile, 'utf8'));
  } catch (e) {
    settings = {};
  }
  if (!settings.hooks) settings.hooks = {};
  if (!settings.hooks.Stop) settings.hooks.Stop = [];

  const alreadyClaude = settings.hooks.Stop.some(entry =>
    (entry.hooks || []).some(h => (h.command || '').includes('ia-notificacion.sh'))
  );

  if (!alreadyClaude) {
    settings.hooks.Stop.push({
      matcher: '',
      hooks: [{ type: 'command', command: hookCmd }]
    });
    fs.writeFileSync(claudeFile, JSON.stringify(settings, null, 2) + '\n');
    console.log(`Hook Stop configurado en Claude Code: ${claudeFile}`);
  }
} catch (err) {
  console.error(`Error al configurar Claude Code: ${err.message}`);
}

// 2. Antigravity (agy)
try {
  let hooks = {};
  try {
    hooks = JSON.parse(fs.readFileSync(agyFile, 'utf8'));
  } catch (e) {
    hooks = {};
  }
  if (!hooks['ia-notificacion']) hooks['ia-notificacion'] = {};
  if (!hooks['ia-notificacion'].Stop) hooks['ia-notificacion'].Stop = [];

  const alreadyAgy = hooks['ia-notificacion'].Stop.some(h =>
    (h.command || '').includes('ia-notificacion.sh')
  );

  if (!alreadyAgy) {
    hooks['ia-notificacion'].Stop.push({
      type: 'command',
      command: hookCmd
    });
    fs.writeFileSync(agyFile, JSON.stringify(hooks, null, 2) + '\n');
    console.log(`Hook Stop configurado en Antigravity: ${agyFile}`);
  }
} catch (err) {
  console.error(`Error al configurar Antigravity: ${err.message}`);
}
JSEOF
}

_configurar_con_python() {
    python3 - "$CLAUDE_SETTINGS" "$AGY_HOOKS" "$HOOK_CMD" <<'PYEOF'
import json, sys, os

claude_file, agy_file, hook_cmd = sys.argv[1:4]

# 1. Claude Code
try:
    try:
        with open(claude_file) as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        settings = {}

    stop_hooks = settings.setdefault("hooks", {}).setdefault("Stop", [])
    already_claude = any(
        "ia-notificacion.sh" in h.get("command", "")
        for entry in stop_hooks
        for h in entry.get("hooks", [])
    )
    if not already_claude:
        stop_hooks.append({
            "matcher": "",
            "hooks": [{"type": "command", "command": hook_cmd}]
        })
        with open(claude_file, "w") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
        print(f"Hook Stop configurado en Claude Code: {claude_file}")
except Exception as e:
    print(f"Error al configurar Claude Code: {e}", file=sys.stderr)

# 2. Antigravity (agy)
try:
    try:
        with open(agy_file) as f:
            hooks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        hooks = {}

    stop_list = hooks.setdefault("ia-notificacion", {}).setdefault("Stop", [])
    already_agy = any("ia-notificacion.sh" in h.get("command", "") for h in stop_list)
    if not already_agy:
        stop_list.append({"type": "command", "command": hook_cmd})
        with open(agy_file, "w") as f:
            json.dump(hooks, f, indent=2)
            f.write("\n")
        print(f"Hook Stop configurado en Antigravity: {agy_file}")
except Exception as e:
    print(f"Error al configurar Antigravity: {e}", file=sys.stderr)
PYEOF
}

if command -v node >/dev/null 2>&1; then
    _configurar_con_node
elif command -v python3 >/dev/null 2>&1; then
    _configurar_con_python
else
    echo "Aviso: no se encontró node ni python3 para configurar hooks de IA" >&2
    exit 1
fi
