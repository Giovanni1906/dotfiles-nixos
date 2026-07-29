# Edit this configuration file to define what should be installed on
# your system.  Help is available in the configuration.nix(5) man page
# and in the NixOS manual (accessible by running ‘nixos-help’).

{ config, pkgs, ... }:

{
  imports =
    [ # Include the results of the hardware scan.
      ./hardware-configuration.nix
    ];

  # Bootloader.
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  networking.hostName = "nixos"; # Define your hostname.
  # networking.wireless.enable = true;  # Enables wireless support via wpa_supplicant.

  # Configure network proxy if necessary
  # networking.proxy.default = "http://user:password@proxy:port/";
  # networking.proxy.noProxy = "127.0.0.1,localhost,internal.domain";

  # --------------------------------------------------
  # -- Variables del sistema y limpieza automática ---
  # --------------------------------------------------

  environment.variables = {
    XCURSOR_THEME = "catppuccin-mocha-sky-cursors";
    XCURSOR_SIZE = "24";
    HYPRCURSOR_THEME = "catppuccin-mocha-sky-cursors";
    HYPRCURSOR_SIZE = "24";
  };

  nixpkgs.config.allowUnfree = true;		# Habilitar software privativo
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  nix.settings.auto-optimise-store = true;
  nix.gc = {
    automatic = true;
    dates = "weekly";
    options = "--delete-older-than 7d";
  };
  services.flatpak.enable = true;

  # Configuración global de fuentes para el sistema
  fonts.packages = with pkgs; [
    font-awesome       # Iconos clásicos (batería, wifi, etc.)
    nerd-fonts.jetbrains-mono # La tipografía con iconos integrados
  ];
  
  # --------------------------------------------------

  # --------------------------------------------------
  # ---               Conectividad                 ---
  # --------------------------------------------------

  # Gestor de redes inalámbricas
  networking.networkmanager.enable = true;

  # Habilitar Bluetooth y su gestión de energía
  hardware.bluetooth.enable = true;
  hardware.bluetooth.powerOnBoot = true;

  # Activar KDE Connect (NixOS abrirá automáticamente los puertos del Firewall)
  # programs.kdeconnect.enable = true;

  # conexion con tailscale 
  services.tailscale.enable = true;  
  
  # --------------------------------------------------    

  # Set your time zone.
  time.timeZone = "America/Lima";

  # Select internationalisation properties.
  i18n.defaultLocale = "es_MX.UTF-8";

  # Enable the X11 windowing system.
  # You can disable this if you're only using the Wayland session.
  services.xserver.enable = true;

  
  # -------------------------------------------------
  # ---             Entorno Grafico               ---
  # -------------------------------------------------

  # --- Enable the KDE Plasma Desktop Environment. ---
  # services.displayManager.sddm = {
  #   enable = true;
  #   wayland.enable = true;      # Comunicacion directa con wayland (evita cuelgue)
  #   theme = "catppuccin-mocha"; # El diseño moderno y oscuro
  # };
  # services.desktopManager.plasma6.enable = true;

  # Gestor de inicio de sesión Greetd
  services.greetd = {
    enable = true;
    settings = {
      default_session = {
        command = "${pkgs.tuigreet}/bin/tuigreet --time --remember --asterisks --greeting 'Iniciando Sistema...' --theme 'prompt=cyan;text=cyan;input=white' --cmd start-hyprland";
        user = "greeter";
      };
    };
  };
  
  # --- Descarga de hyperland ---
  programs.hyprland.enable = true;

  # --- Gestor de preferencias ---
  programs.dconf.enable = true;
  # Forzar el motor de temas para aplicaciones Qt (Dolphin, etc.)
#  qt = {
#    enable = true;
#    platformTheme = "kde";
#    style = "breeze";
#  };  
  # -------------------------------------------------

  # Configure keymap in X11
  services.xserver.xkb = {
    layout = "latam";
    variant = "";
  };

  # Configure console keymap
  console.keyMap = "la-latin1";

  # Enable CUPS to print documents.
  services.printing.enable = true;

  # Enable sound with pipewire.
  services.pulseaudio.enable = false;
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
    # If you want to use JACK applications, uncomment this
    #jack.enable = true;

    # use the example session manager (no others are packaged yet so this is enabled by default,
    # no need to redefine it in your config for now)
    #media-session.enable = true;
  };

  # Para habilitar GVFS (GNOME Virtual File System)
  services.gvfs.enable = true;

  # --------------------------------------------------------
  # ---                    Desarrollo                     
  # --------------------------------------------------------

  # Habilitar entorno Docker
  virtualisation.docker.enable = true;

  # --------------------------------------------------------  

  # Enable touchpad support (enabled default in most desktopManager).
  # services.xserver.libinput.enable = true;

  # Define a user account. Don't forget to set a password with ‘passwd’.
  users.users."nova" = {
    isNormalUser = true;
    description = "Jorge Velasquez Valdivia";
    extraGroups = [ "networkmanager" "wheel" "docker" "input" ];
    packages = with pkgs; [
      kdePackages.kate
    #  thunderbird
    ];
  };

  # Install firefox.
  programs.firefox.enable = true;

  
  # -------------------------------------------------
  # --- List packages installed in system profile ---
  # ------------------------------------------------- 
  # To search, run:
  # $ nix search wget
  environment.systemPackages = with pkgs; [
    kitty
    waybar
    # vim # Do not forget to add an editor to edit configuration.nix! The Nano editor is also installed by default.

    # Utilidades de entorno Wayland / Hyprland
    rofi             	    # Lanzador de aplicaciones minimalista
    mako             	    # Demonio de notificaciones ligero (esencial para KDE Connect)
    wl-clipboard    	    # Gestión del portapapeles en Wayland
    rclone          	    # Para montar tu Google Drive en una carpeta local
    appimage-run     	    # Para ejecutar programas en formato AppImage sin problemas
    grim          		    # El capturador
    slurp  		            # El selector de área
    pulsemixer 			    # Mezclador interactivo ultra ligero
    catppuccin-cursors.mochaSky     # paquete de cursor catppuccin
    glib                      # Provee el comando gsettings
	swaybg					# fondo de pantalla
    # kdePackages.breeze        # Tema nativo para familia KDE - Qt (KDE connect, navicat, etc)
    # kdePackages.breeze-icons  # Iconos oficiales para que no falten carpetas
	papirus-icon-theme        # Para iconos 
    gsettings-desktop-schemas # El diccionario de reglas visuales
    adwaita-icon-theme        # Iconos y cursores base oscuros
    networkmanagerapplet      # Gestor de red
    gnome-themes-extra        # Aquí vive físicamente el código de Adwaita-dark
    nwg-look       		      # Gestor gráfico de apariencia exclusivo para Wayland/Hyprland
    # Herramientas básicas de terminal
    wget		 	        # Descarga de paginas web
    micro      		        # Un editor de texto para terminal mucho más cómodo que nano
    fastfetch 				# Monitoreo de PC
    # Utilidades
    # kdePackages.dolphin	# El gestor de archivos moderno de KDE (Qt6)
	thunar					# Gestor de archivos del entorno XFCE
    libnotify    		    # Proporciona el comando 'notify-send' (esencial para Mako)
    pulseaudio  		    # Proporciona el comando 'paplay' para reproducir el sonido (.oga)
    sound-theme-freedesktop	# Los sonidos base del sistema (/usr/share/sounds...)
    playerctl               # Modulo de musica
    valent					# Conectar con celular
    _7zip-zstd					# descomprimir (7z x nombrearchivo)
    libqalculate			# calculadora para terminal
	onlyoffice-desktopeditors	# editor de documentos
	wayvnc					# Conexion remota desde otro dispositivo
    # para informática
    git
    vscode					# Editor de código con copilot
    filezilla				# 
    navicat-premium			
    ];
  # --------------------------------------------------


  # --------------------------------------
  # ---      Ecosistema de juegos      ---
  # --------------------------------------

  # # Habilitar Steam con optimizaciones de red y rendimiento
  # programs.steam = {
  #   enable = true;
  #   remotePlay.openFirewall = true;
  # };

  # # Herramientas para juegos en el sistema
  # environment.systemPackages = [
  #   pkgs.heroic         # Launcher para Epic Games
  #   pkgs.lutris         # Excelente para gestionar el prefijo de Battle.net / WoW
  #   pkgs.protonup-qt    # Para bajar las últimas versiones de GE-Proton y Wine-GE
  # ];

  # --------------------------------------
  
  # --------------------------------------
  # ---              Alias             ---
  # --------------------------------------

  environment.shellAliases = {
    # Mantenimiento rápido de NixOS
    nix-switch = "sudo nixos-rebuild switch";
    nix-clean  = "sudo nix-env --delete-generations old && sudo nixos-rebuild boot && sudo nix-store --gc";
    nix-config = "sudo micro /etc/nixos/configuration.nix";

	hypr-config = "sudo micro ~/dotfiles/config/hypr/hyprland.conf";
	kitty-config = "sudo micro ~/dotfiles/config/kitty/kitty.conf";
	waybar-config = "sudo micro ~/dotfiles/config/waybar/config";
	
    # Atajos de desarrollo e infraestructura
    ll = "ls -lha";
    k  = "kubectl";
    d  = "docker";
    dc-up = "docker compose up -d";
    dc-down = "docker compose down";

	remote-conexion = "wayvnc 0.0.0.0";
    reset-trial-navicat = "~/dotfiles/utils/reset-trial-navicat.sh";

    ip-public= "curl -s ipinfo.io/ip";
  };

  # --------------------------------------



  # ----------------------------------------------------
  # ---              Firewall y permisos             ---
  # ----------------------------------------------------

  # Portales de XDG para compatibilidad en Wayland (necesario para Valent, OBS, etc.)
    xdg.portal = {
      enable = true;
      extraPortals = [ 
        pkgs.xdg-desktop-portal-hyprland 
        pkgs.xdg-desktop-portal-gtk 
      ];
    };

  # Some programs need SUID wrappers, can be configured further or are
  # started in user sessions.
  # programs.mtr.enable = true;
  # programs.gnupg.agent = {
  #   enable = true;
  #   enableSSHSupport = true;
  # };

  # List services that you want to enable:

  # Enable the OpenSSH daemon.
  # services.openssh.enable = true;

  # Abrir los puertos para que el celular encuentre a Valent
    networking.firewall = {
      enable = true;
      allowedTCPPorts = [ 5900 ]; # Puerto para la conexión remota WayVNC
      allowedTCPPortRanges = [ { from = 1714; to = 1764; } ];
      allowedUDPPortRanges = [ { from = 1714; to = 1764; } ];
    };

  # Open ports in the firewall.
  # networking.firewall.allowedTCPPorts = [ ... ];
  # networking.firewall.allowedUDPPorts = [ ... ];
  # Or disable the firewall altogether.
  # networking.firewall.enable = false;

  # ----------------------------------------------------

  # This value determines the NixOS release from which the default
  # settings for stateful data, like file locations and database versions
  # on your system were taken. It‘s perfectly fine and recommended to leave
  # this value at the release version of the first install of this system.
  # Before changing this value read the documentation for this option
  # (e.g. man configuration.nix or on https://nixos.org/nixos/options.html).
  system.stateVersion = "26.05"; # Did you read the comment?

}
