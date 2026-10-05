# =============================================================================
# JUEGOS: Steam y lanzadores (solo para equipos que lo soporten)
# =============================================================================

{ config, pkgs, ... }:

{
  # Steam con optimizaciones de red y rendimiento
  programs.steam = {
    enable = true;
    remotePlay.openFirewall = true;
  };

  environment.systemPackages = with pkgs; [
    heroic                      # Launcher para Epic Games
    lutris                      # Para gestionar el prefijo de Battle.net / WoW
    protonup-qt                 # Para bajar las últimas versiones de GE-Proton y Wine-GE
  ];
}
