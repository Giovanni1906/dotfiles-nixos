# =============================================================================
# EQUIPO: PC de escritorio ASUS (AMD, NVMe)
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

  dotfiles.equipo = "pc-asus";
  networking.hostName = "nixos";

  # Arranque: GRUB en modo EFI (el aspecto lo define ../../modulos/tema.nix)
  boot.loader.grub = {
    enable = true;
    efiSupport = true;
    device = "nodev";
    configurationLimit = 10;   # Generaciones en el submenú (para volver atrás si una falla)
  };
  boot.loader.efi.canTouchEfiVariables = true;

  # La controladora SATA pide arranque escalonado y el kernel revisa sus 6 puertos (vacíos)
  # uno a uno: el montaje del NVMe raíz espera ~3 s. Así los revisa en paralelo.
  boot.kernelParams = [ "libahci.ignore_sss=1" ];

  # Versión de NixOS con la que se instaló esta PC. No cambiarla al actualizar.
  system.stateVersion = "26.05";
}
