# =============================================================================
# DESARROLLO: contenedores, máquinas virtuales y editores
# =============================================================================

{ config, pkgs, ... }:

{
  virtualisation.docker.enable = true;

  # libvirtd y virt-manager (QEMU con TPM para Windows 11)
  virtualisation.libvirtd = {
    enable = true;
    qemu.swtpm.enable = true;
  };
  programs.virt-manager.enable = true;

  users.users."nova".extraGroups = [ "docker" "libvirtd" "kvm" ];

  environment.systemPackages = with pkgs; [
    vscode                      # Editor de código con Copilot
    code-cursor
    filezilla
    navicat-premium
    postman
  ];

  environment.shellAliases = {
    k  = "kubectl";
    d  = "docker";
    dc-up = "docker compose up -d";
    dc-down = "docker compose down";
    reset-trial-navicat = "~/dotfiles/utils/reset-trial-navicat.sh";
  };
}
