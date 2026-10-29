# =============================================================================
# EQUIPO: PC de admisión (Intel, NVMe)
# =============================================================================
# Solo lo propio de esta máquina: qué módulos usa, nombre, arranque y versión.
# El hardware (discos, módulos del kernel) NO está en el repo: es el
# /etc/nixos/hardware-configuration.nix que generó la instalación de esta PC.

{ pkgs, ... }:

{
  imports = [
    ../../modulos/base.nix
    ../../modulos/escritorio.nix
    ../../modulos/tema.nix
    ../../modulos/desarrollo.nix
    ../../modulos/remoto.nix
    ../../modulos/ia.nix           # Agentes de IA y MCP context-hub
    # ../../modulos/juegos.nix     # Steam, Heroic, Lutris
  ];

  dotfiles.equipo = "pc-admision-jorge";
  dotfiles.usuario = "admision";
  networking.hostName = "nixos";

  # Arranque: systemd-boot (el de la instalación). El tema de GRUB de tema.nix no se usa aquí.
  boot.loader.systemd-boot = {
    enable = true;
    configurationLimit = 10;   # Generaciones en el menú (para volver atrás si una falla)
  };
  boot.loader.efi.canTouchEfiVariables = true;

  # Cliente Qsync: el espacio de la NAS no se ve al entrar por IP. El .deb es de
  # Ubuntu 22.04, así que corre en un Ubuntu aparte (Docker ya está en desarrollo.nix).
  environment.systemPackages = with pkgs; [
    distrobox                   # Ubuntu aparte para el cliente Qsync
  ];

  # Atajos de la infraestructura de admisión
  environment.shellAliases = {
    k-prod = "kubectl --kubeconfig=\"/home/admision/.kube/dalthon-server-kubeconfig.yaml\"";
    open-conexion = "/home/admision/Utilidades/open-conexion.sh";
    local-open-conexion = "/home/admision/Utilidades/local_open-conexion.sh";
    backups-dev-restore = "/home/admision/Utilidades/backups_impresiones_local.sh";
    qsync = "~/dotfiles/utils/qsync.sh";
  };

  # Versión de NixOS con la que se instaló esta PC. No cambiarla al actualizar.
  system.stateVersion = "26.05";
}
