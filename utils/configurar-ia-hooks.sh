#!/usr/bin/env bash
# Configura los hooks Stop de agentes de IA (Claude Code, Antigravity y Cursor).
# Idempotente: no duplica si los hooks ya están registrados.
# Compatible con Node.js y Python 3.
# Llamado por: nixos/modulos/ia.nix (userActivationScripts) e init.sh (paso_usuario).

CLAUDE_SETTINGS="$HOME/.claude/settings.json"
AGY_HOOKS="$HOME/.gemini/config/hooks.json"
CURSOR_HOOKS="$HOME/.cursor/hooks.json"
HOOK_BASE="~/dotfiles/utils/ia-notificacion.sh"

mkdir -p "$(dirname "$CLAUDE_SETTINGS")" "$(dirname "$AGY_HOOKS")" "$(dirname "$CURSOR_HOOKS")"

_configurar_con_node() {
    node - "$CLAUDE_SETTINGS" "$AGY_HOOKS" "$CURSOR_HOOKS" "$HOOK_BASE" <<'JSEOF'
const fs = require('fs');
const [claudeFile, agyFile, cursorFile, hookBase] = process.argv.slice(2);

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
  const claudeCmd = `${hookBase} --agente Claude`;

  let updated = false;
  settings.hooks.Stop = settings.hooks.Stop.map(entry => {
    const hooks = (entry.hooks || []).map(h => {
      if ((h.command || '').includes('ia-notificacion.sh')) {
        updated = true;
        return { ...h, command: claudeCmd };
      }
      return h;
    });
    return { ...entry, hooks };
  });

  if (!updated) {
    settings.hooks.Stop.push({
      matcher: '',
      hooks: [{ type: 'command', command: claudeCmd }]
    });
  }
  fs.writeFileSync(claudeFile, JSON.stringify(settings, null, 2) + '\n');
  console.log(`Hook Stop configurado en Claude Code: ${claudeFile}`);
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
  const agyCmd = `${hookBase} --agente Antigravity`;

  let updated = false;
  hooks['ia-notificacion'].Stop = hooks['ia-notificacion'].Stop.map(h => {
    if ((h.command || '').includes('ia-notificacion.sh')) {
      updated = true;
      return { ...h, command: agyCmd };
    }
    return h;
  });

  if (!updated) {
    hooks['ia-notificacion'].Stop.push({
      type: 'command',
      command: agyCmd
    });
  }
  fs.writeFileSync(agyFile, JSON.stringify(hooks, null, 2) + '\n');
  console.log(`Hook Stop configurado en Antigravity: ${agyFile}`);
} catch (err) {
  console.error(`Error al configurar Antigravity: ${err.message}`);
}

// 3. Cursor Agent
try {
  let cursorHooks = {};
  try {
    cursorHooks = JSON.parse(fs.readFileSync(cursorFile, 'utf8'));
  } catch (e) {
    cursorHooks = { version: 1, hooks: {} };
  }
  if (!cursorHooks.hooks) cursorHooks.hooks = {};
  if (!cursorHooks.hooks.stop) cursorHooks.hooks.stop = [];
  const cursorCmd = `${hookBase} --agente Cursor`;

  let updated = false;
  cursorHooks.hooks.stop = cursorHooks.hooks.stop.map(h => {
    if ((h.command || '').includes('ia-notificacion.sh')) {
      updated = true;
      return { ...h, command: cursorCmd };
    }
    return h;
  });

  if (!updated) {
    cursorHooks.hooks.stop.push({ command: cursorCmd });
  }
  fs.writeFileSync(cursorFile, JSON.stringify(cursorHooks, null, 2) + '\n');
  console.log(`Hook Stop configurado en Cursor: ${cursorFile}`);
} catch (err) {
  console.error(`Error al configurar Cursor: ${err.message}`);
}
JSEOF
}

_configurar_con_python() {
    python3 - "$CLAUDE_SETTINGS" "$AGY_HOOKS" "$CURSOR_HOOKS" "$HOOK_BASE" <<'PYEOF'
import json, sys, os

claude_file, agy_file, cursor_file, hook_base = sys.argv[1:5]

# 1. Claude Code
try:
    try:
        with open(claude_file) as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        settings = {}

    stop_hooks = settings.setdefault("hooks", {}).setdefault("Stop", [])
    claude_cmd = f"{hook_base} --agente Claude"
    updated = False
    for entry in stop_hooks:
        for h in entry.get("hooks", []):
            if "ia-notificacion.sh" in h.get("command", ""):
                h["command"] = claude_cmd
                updated = True
    if not updated:
        stop_hooks.append({
            "matcher": "",
            "hooks": [{"type": "command", "command": claude_cmd}]
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
    agy_cmd = f"{hook_base} --agente Antigravity"
    updated = False
    for h in stop_list:
        if "ia-notificacion.sh" in h.get("command", ""):
            h["command"] = agy_cmd
            updated = True
    if not updated:
        stop_list.append({"type": "command", "command": agy_cmd})
    with open(agy_file, "w") as f:
        json.dump(hooks, f, indent=2)
        f.write("\n")
    print(f"Hook Stop configurado en Antigravity: {agy_file}")
except Exception as e:
    print(f"Error al configurar Antigravity: {e}", file=sys.stderr)

# 3. Cursor Agent
try:
    try:
        with open(cursor_file) as f:
            cursor_hooks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cursor_hooks = {"version": 1, "hooks": {}}

    stop_cursor = cursor_hooks.setdefault("hooks", {}).setdefault("stop", [])
    cursor_cmd = f"{hook_base} --agente Cursor"
    updated = False
    for h in stop_cursor:
        if "ia-notificacion.sh" in h.get("command", ""):
            h["command"] = cursor_cmd
            updated = True
    if not updated:
        stop_cursor.append({"command": cursor_cmd})
    with open(cursor_file, "w") as f:
        json.dump(cursor_hooks, f, indent=2)
        f.write("\n")
    print(f"Hook Stop configurado en Cursor: {cursor_file}")
except Exception as e:
    print(f"Error al configurar Cursor: {e}", file=sys.stderr)
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
