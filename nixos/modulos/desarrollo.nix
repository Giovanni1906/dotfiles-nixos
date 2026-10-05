# =============================================================================
# DESARROLLO: contenedores, Kubernetes local, máquinas virtuales y editores
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

  users.users.${config.dotfiles.usuario}.extraGroups = [ "docker" "libvirtd" "kvm" ];

  # --------------------------------------------------
  # ---     Kubernetes local (Kind + Skaffold)     ---
  # --------------------------------------------------
  # Dominios locales de la capa k8s/ (Ingress de Kind en 127.0.0.1)
  networking.extraHosts = ''
    127.0.0.1 postula.admision.dev panel.postula.admision.dev credential.postula.admision.dev valida.postula.admision.dev asisto.admision.dev
  '';

  # Kind y la sincronización de archivos de Skaffold necesitan más inotify
  boot.kernel.sysctl = {
    "fs.inotify.max_user_watches" = 524288;
    "fs.inotify.max_user_instances" = 512;
  };

  environment.systemPackages = with pkgs; [
    vscode                      # Editor de código con Copilot
    code-cursor
    filezilla
    navicat-premium
    postman
    kubectl                     # Cliente de Kubernetes (alias k)
    kind                        # Clúster de Kubernetes dentro de Docker
    skaffold                    # Construye y despliega en el clúster mientras se edita
    gnumake                     # make para los Makefile de los proyectos
  ];

  environment.shellAliases = {
    k  = "kubectl";
    d  = "docker";
    dc-up = "docker compose up -d";
    dc-down = "docker compose down";
    reset-trial-navicat = "~/dotfiles/utils/reset-trial-navicat.sh";
  };
}
