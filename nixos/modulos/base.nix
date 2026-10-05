# =============================================================================
# BASE: lo que necesita cualquier equipo (Nix, idioma, red, audio, usuario)
# =============================================================================

{ config, lib, pkgs, ... }:

{
  options.dotfiles.equipo = lib.mkOption {
    type = lib.types.str;
    description = "Nombre de la carpeta del equipo en nixos/equipos/ (lo usan los alias).";
  };

  options.dotfiles.usuario = lib.mkOption {
    type = lib.types.str;
    default = "nova";
    description = "Usuario principal del equipo (los módulos le añaden grupos y paquetes).";
  };

  config = {
    # --------------------------------------------------
    # ---          Nix y limpieza automática         ---
    # --------------------------------------------------
    nixpkgs.config.allowUnfree = true;      # Habilitar software privativo
    nix.settings.experimental-features = [ "nix-command" "flakes" ];
    nix.settings.auto-optimise-store = true;
    nix.gc = {
      automatic = true;
      dates = "weekly";
      options = "--delete-older-than 7d";
    };

    # --------------------------------------------------
    # ---        Idioma, hora y distribución         ---
    # --------------------------------------------------
    time.timeZone = "America/Lima";
    i18n.defaultLocale = "es_MX.UTF-8";
    services.xserver.xkb = {
      layout = "latam";
      variant = "";
    };
    console.keyMap = "la-latin1";

    # --------------------------------------------------
    # ---               Conectividad                 ---
    # --------------------------------------------------
    networking.networkmanager.enable = true;   # Gestor de redes (cable y wifi)
    networking.firewall.enable = true;         # Los puertos los abre cada módulo
    hardware.bluetooth.enable = true;
    hardware.bluetooth.powerOnBoot = true;

    # --------------------------------------------------
    # ---          Audio (PipeWire) e impresión      ---
    # --------------------------------------------------
    services.pulseaudio.enable = false;
    security.rtkit.enable = true;
    services.pipewire = {
      enable = true;
      alsa.enable = true;
      alsa.support32Bit = true;
      pulse.enable = true;
      #jack.enable = true;   # Para aplicaciones JACK
    };
    services.printing.enable = true;           # CUPS

    # --------------------------------------------------
    # ---                  Usuario                   ---
    # --------------------------------------------------
    # Contraseña con `passwd`. Los grupos de Docker, libvirt, etc. los añade cada módulo.
    users.users.${config.dotfiles.usuario} = {
      isNormalUser = true;
      description = "Jorge Velasquez Valdivia";
      extraGroups = [ "networkmanager" "wheel" "input" ];
    };

    # --------------------------------------------------
    # ---         Herramientas de terminal           ---
    # --------------------------------------------------
    environment.systemPackages = with pkgs; [
      git
      gh                        # GitHub CLI (credenciales para git push)
      htop
      wget                      # Descarga de páginas web
      micro                     # Editor de texto para terminal más cómodo que nano
      fastfetch                 # Información del sistema
      rclone                    # Para montar Google Drive en una carpeta local
      _7zip-zstd                # Descomprimir (7z x nombrearchivo)
      libqalculate              # Calculadora para terminal
      rename                    # Renombrar archivos
      ffmpeg                    # Manejo de formatos de video
      yt-dlp                    # Descargar videos de YouTube
      poppler-utils             # Utilidades para pdf (pdfunite, pdfseparate, pdftotext, pdfimages, etc)
      bitwarden-cli             # CLI de Bitwarden
    ];

    # --------------------------------------------------
    # ---                   Alias                    ---
    # --------------------------------------------------
    environment.shellAliases = {
      # Mantenimiento de NixOS
      nix-switch = "sudo nixos-rebuild switch";
      # Como root borra las generaciones viejas de todos los perfiles, también la del sistema;
      # "boot" rehace el menú de GRUB sin ellas
      nix-clean  = "sudo nix-collect-garbage -d && sudo nixos-rebuild boot";
      nix-config = "micro ~/dotfiles/nixos/equipos/${config.dotfiles.equipo}/default.nix";
      # git pull + enlaces y tema + nixos-rebuild switch
      dotfiles-actualizar = "~/dotfiles/init.sh actualizar";

      ll = "ls -lha";
      ip-public = "curl -s ipinfo.io/ip";
    };
  };
}
