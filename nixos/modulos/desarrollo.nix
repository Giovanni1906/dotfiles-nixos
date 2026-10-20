# =============================================================================
# DESARROLLO: contenedores, Kubernetes local, máquinas virtuales y editores
# =============================================================================

{ config, pkgs, ... }:

let
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
  # Dominios locales de la capa k8s/ (Ingress de Kind en 127.0.0.1); los mismos hosts
  # que k8s/ingress.yaml de siad.inscripciones
  networking.extraHosts = ''
    127.0.0.1 postula.admision.dev
    127.0.0.1 panel.postula.admision.dev
    127.0.0.1 credential.postula.admision.dev
    127.0.0.1 valida.postula.admision.dev
    127.0.0.1 puntaje.postula.admision.dev
    127.0.0.1 imagen.postula.admision.dev
    127.0.0.1 asisto.admision.dev
  '';

  # Kind y la sincronización de archivos de Skaffold necesitan más inotify
  boot.kernel.sysctl = {
    "fs.inotify.max_user_watches" = 524288;
    "fs.inotify.max_user_instances" = 512;
  };

  # El binario de Sublime Text (sublime4) enlaza OpenSSL 1.1 para su host de plugins
  nixpkgs.config.permittedInsecurePackages = [ "openssl-1.1.1w" ];

  environment.systemPackages = with pkgs; [
    vscode                      # Editor de código con Copilot
    cursor                      # Editor de código con IA (versión fijada arriba)
    sublime4                    # Sublime Text
    figma-linux                 # Cliente de escritorio de Figma
    filezilla
    navicat-premium
    postman
    kubectl                     # Cliente de Kubernetes (alias k)
    kind                        # Clúster de Kubernetes dentro de Docker
    skaffold                    # Construye y despliega en el clúster mientras se edita
    gnumake                     # make para los Makefile de los proyectos
    nodejs                      # Node.js con npm y npx para ejecutar programas o paquetes
  ];

  environment.shellAliases = {
    k  = "kubectl";
    d  = "docker";
    dc-up = "docker compose up -d";
    dc-down = "docker compose down";
    reset-trial-navicat = "~/dotfiles/utils/reset-trial-navicat.sh";
  };
}
