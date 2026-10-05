# =============================================================================
# EQUIPO: PC de admisión (Intel, NVMe)
# =============================================================================
# Solo lo propio de esta máquina: qué módulos usa, nombre, arranque y versión.
# El hardware (discos, módulos del kernel) NO está en el repo: es el
# /etc/nixos/hardware-configuration.nix que generó la instalación de esta PC.

{ ... }:

{
  imports = [
    ../../modulos/base.nix
    ../../modulos/escritorio.nix
    ../../modulos/tema.nix
    ../../modulos/desarrollo.nix
    ../../modulos/remoto.nix
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

  # Atajos de la infraestructura de admisión
  environment.shellAliases = {
    k-prod = "kubectl --kubeconfig=\"/home/admision/.kube/dalthon-server-kubeconfig.yaml\"";
    open-conexion = "/home/admision/Utilidades/open-conexion.sh";
    local-open-conexion = "/home/admision/Utilidades/local_open-conexion.sh";
  };

  # Versión de NixOS con la que se instaló esta PC. No cambiarla al actualizar.
  system.stateVersion = "26.05";
}
