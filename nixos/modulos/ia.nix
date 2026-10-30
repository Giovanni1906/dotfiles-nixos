# =============================================================================
# IA: agentes de IA (Antigravity, Claude Code, Cursor, Hermes) y MCP context-hub
# =============================================================================
# Centraliza todos los agentes de IA, el editor Cursor, el conector MCP hacia la
# Mac Mini (CONTEXT_HUB_URL en ~/dotfiles/.env vía Tailscale) y el comando `context-init`.
# Quitar este módulo de un equipo desactiva de golpe todos los agentes y el MCP.

{ pkgs, ... }:

let
  # ---     Versiones fijadas (flakes y Cursor)    ---
  # Agentes desde flakes oficiales, fijados a un commit (base.nix habilita "flakes").
  # Para actualizar: cambiar el commit (y la versión del comentario) por el de un tag nuevo.
  hermes = builtins.getFlake "github:NousResearch/hermes-agent/f97608f178d1ffeca59860195ab7da295f7c8e5f";   # v2026.9.24
  agy    = builtins.getFlake "github:nklmilojevic/antigravity-cli-nix/420b870443784434047aa9d0748c04bb7058963f";  # v2026.10.29

  # Cursor más nuevo que el del canal. Para actualizar: versión y URL de
  # https://www.cursor.com/api/download?platform=linux-x64&releaseTrack=stable
  # y el hash con: nix-prefetch-url <url> | xargs nix hash convert --hash-algo sha256
  cursor = pkgs.code-cursor.overrideAttrs (old: rec {
    version = "3.24.12";
    src = pkgs.appimageTools.extract {
      pname = "cursor";
      inherit version;
      src = pkgs.fetchurl {
        url = "https://downloads.cursor.com/production/37b865941ccb31e2fc90c685157534efca87f964/linux/x64/Cursor-${version}-x86_64.AppImage";
        hash = "sha256-JQn7QjetruZsUj744a8c2uH3ytX3AVnhGhfrYBBENjY=";
      };
    };
    sourceRoot = "cursor-${version}-extracted/usr/share/cursor";
  });
in
{
  # --------------------------------------------------
  # ---     Servidor MCP central (context-hub)     ---
  # --------------------------------------------------
  # Al activar el sistema o iniciar sesión, lee CONTEXT_HUB_URL desde ~/dotfiles/.env
  # y asegura que todos los agentes apunten al MCP context-hub sin exponer la IP en git.
  system.userActivationScripts.ia-mcp.text = ''
    [ -f "$HOME/dotfiles/.env" ] && . "$HOME/dotfiles/.env"
    mcp_url="''${CONTEXT_HUB_URL:-}"
    if [ -n "$mcp_url" ] && [[ "$mcp_url" != *"ip_tailscale"* ]]; then
      mkdir -p "$HOME/.gemini/config" "$HOME/.cursor" "$HOME/.codex"
      for mcp_file in "$HOME/.gemini/config/mcp_config.json" "$HOME/.cursor/mcp.json"; do
        if [ ! -s "$mcp_file" ]; then
          cat > "$mcp_file" <<EOF
{
  "mcpServers": {
    "context-hub": {
      "url": "$mcp_url"
    }
  }
}
EOF
        fi
      done

      if [ -d "$HOME/.hermes" ] && ! grep -q 'context-hub:' "$HOME/.hermes/config.yaml" 2>/dev/null; then
        cat >> "$HOME/.hermes/config.yaml" <<EOF

mcp_servers:
  context-hub:
    url: $mcp_url
    enabled: true
EOF
      fi

      if ! grep -q 'context-hub' "$HOME/.codex/config.toml" 2>/dev/null; then
        cat >> "$HOME/.codex/config.toml" <<EOF
[mcp_servers.context-hub]
url = "$mcp_url"
EOF
      fi

      if [ -f "$HOME/.claude.json" ] && ! grep -q '"context-hub"' "$HOME/.claude.json" 2>/dev/null; then
        ${pkgs.claude-code}/bin/claude mcp add --transport http --scope user context-hub "$mcp_url" >/dev/null 2>&1 || true
      fi
    fi
  '';

  # --------------------------------------------------
  # ---              Agentes y editores            ---
  # --------------------------------------------------
  environment.systemPackages = [
    agy.packages.${pkgs.stdenv.hostPlatform.system}.default      # Antigravity CLI: agy (login con cuenta Google)
    pkgs.claude-code                                             # Claude Code para terminal: claude
    cursor                                                       # Editor de código con IA (versión fijada arriba)
    hermes.packages.${pkgs.stdenv.hostPlatform.system}.default   # Hermes Agent: hermes, hermes-agent, hermes-acp (config en ~/.hermes)
  ];

  # --------------------------------------------------
  # ---                   Alias                    ---
  # --------------------------------------------------
  environment.shellAliases = {
    # Antigravity CLI sin pedir confirmaciones de permisos
    agy = "agy --dangerously-skip-permissions";
    # Conecta el proyecto de la carpeta actual al MCP context-hub de la Mac Mini
    context-init = "~/dotfiles/utils/context-init.sh";
  };
}
