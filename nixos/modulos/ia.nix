# =============================================================================
# IA: agentes de IA (Hermes Agent)
# =============================================================================
# Hermes Agent sale del flake oficial de Nous Research, fijado a un commit. El sistema
# no se construye con flakes: builtins.getFlake lo trae porque base.nix habilita "flakes".
# Para actualizar: cambiar el commit (y la versión del comentario) por el de un tag nuevo.

{ pkgs, ... }:

let
  hermes = builtins.getFlake "github:NousResearch/hermes-agent/f97608f178d1ffeca59860195ab7da295f7c8e5f";   # v2026.9.24
in
{
  environment.systemPackages = [
    hermes.packages.${pkgs.stdenv.hostPlatform.system}.default   # Hermes Agent: hermes, hermes-agent, hermes-acp (config en ~/.hermes)
    pkgs.uv       # Gestor de entornos Python (google-antigravity y otros SDKs de IA)
    pkgs.python3  # Intérprete base para los entornos virtuales
  ];

  environment.shellAliases = {
    ag-setup    = "~/dotfiles/utils/antigravity-setup.sh";
    ag-activate = "source ~/.local/share/antigravity/venv/bin/activate";
  };
}
