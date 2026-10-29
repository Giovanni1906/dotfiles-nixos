# =============================================================================
# IA: agentes de IA (Hermes Agent, Antigravity CLI)
# =============================================================================
# Los agentes salen de flakes oficiales, fijados a un commit. El sistema no se
# construye con flakes: builtins.getFlake los trae porque base.nix habilita "flakes".
# Para actualizar: cambiar el commit (y la versión del comentario) por el de un tag nuevo.

{ pkgs, ... }:

let
  hermes = builtins.getFlake "github:NousResearch/hermes-agent/f97608f178d1ffeca59860195ab7da295f7c8e5f";   # v2026.9.24
  agy    = builtins.getFlake "github:nklmilojevic/antigravity-cli-nix/420b870443784434047aa9d0748c04bb7058963f";  # v2026.10.29
in
{
  environment.systemPackages = [
    hermes.packages.${pkgs.stdenv.hostPlatform.system}.default   # Hermes Agent: hermes, hermes-agent, hermes-acp (config en ~/.hermes)
    agy.packages.${pkgs.stdenv.hostPlatform.system}.default      # Antigravity CLI: agy (login con cuenta Google)
  ];
}
