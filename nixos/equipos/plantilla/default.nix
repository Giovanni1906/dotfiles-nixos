# =============================================================================
# EQUIPO: @EQUIPO@
# =============================================================================
# Creado desde nixos/equipos/plantilla por `init.sh nuevo-equipo`.
# Solo lo propio de esta máquina: qué módulos usa, nombre, arranque y versión.
# El hardware (discos, módulos del kernel) NO está en el repo: es el
# /etc/nixos/hardware-configuration.nix que generó la instalación de esta máquina.

{ ... }:

{
  # Quitar o comentar los módulos que este equipo no necesite o no soporte
  imports = [
    ../../modulos/base.nix
    ../../modulos/escritorio.nix
    ../../modulos/tema.nix
    ../../modulos/desarrollo.nix
    ../../modulos/remoto.nix
    # ../../modulos/juegos.nix     # Steam, Heroic, Lutris
  ];

  dotfiles.equipo = "@EQUIPO@";
  dotfiles.usuario = "@USUARIO@";
  networking.hostName = "@EQUIPO@";

  # Arranque: GRUB en modo EFI. Para BIOS antiguo: efiSupport = false y
  # device = "/dev/sdX" (el disco, no la partición), y quitar la línea de efi.
  boot.loader.grub = {
    enable = true;
    efiSupport = true;
    device = "nodev";
    configurationLimit = 10;   # Generaciones en el submenú (para volver atrás si una falla)
  };
  boot.loader.efi.canTouchEfiVariables = true;

  # Portátil: touchpad y ahorro de energía
  # services.libinput.enable = true;
  # services.power-profiles-daemon.enable = true;

  # Versión de NixOS con la que se instaló esta máquina. No cambiarla al actualizar.
  system.stateVersion = "@VERSION@";
}
