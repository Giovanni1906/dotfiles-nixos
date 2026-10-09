# =============================================================================
# ESCRITORIO: Hyprland y las piezas de la sesión gráfica
# =============================================================================
# La configuración de cada app está en config/ (enlazada a ~/.config por init.sh).
# El aspecto de GRUB y del login está en tema.nix.

{ config, lib, pkgs, ... }:

{
  # --------------------------------------------------
  # ---             Sesión gráfica                 ---
  # --------------------------------------------------
  services.xserver.enable = true;
  programs.hyprland.enable = true;
  programs.dconf.enable = true;                # Gestor de preferencias (GTK, cursor, iconos)
  # Pantalla de bloqueo: instala hyprlock y su servicio PAM (diseño en config/hypr/hyprlock.conf)
  programs.hyprlock.enable = true;
  # hyprlock activa el servicio de hypridle, que espera graphical-session.target y esta sesión
  # no lo alcanza: hypridle arranca con exec-once en hyprland.conf.
  services.hypridle.enable = lib.mkForce false;
  # security.pam.services.swaylock = {};      # Permiso de swaylock (reemplazado por hyprlock)

  # Portales de XDG para compatibilidad en Wayland (necesario para Valent, OBS, etc.)
  xdg.portal = {
    enable = true;
    extraPortals = [
      pkgs.xdg-desktop-portal-hyprland
      pkgs.xdg-desktop-portal-gtk
    ];
  };

  # --- KDE Plasma + SDDM (reemplazado por Hyprland + greetd) ---
  # services.displayManager.sddm = {
  #   enable = true;
  #   wayland.enable = true;      # Comunicacion directa con wayland (evita cuelgue)
  #   theme = "catppuccin-mocha"; # El diseño moderno y oscuro
  # };
  # services.desktopManager.plasma6.enable = true;

  # Forzar el motor de temas para aplicaciones Qt (Dolphin, etc.)
  # qt = {
  #   enable = true;
  #   platformTheme = "kde";
  #   style = "breeze";
  # };

  # Fuentes del sistema (la del tema se elige en tema/tema.conf)
  fonts.packages = with pkgs; [
    font-awesome                # Iconos clásicos (batería, wifi, etc.)
    nerd-fonts.jetbrains-mono   # La tipografía con iconos integrados
  ];

  # --------------------------------------------------
  # ---       Archivos, navegador y Flatpak        ---
  # --------------------------------------------------
  programs.thunar.enable = true;
  programs.thunar.plugins = with pkgs; [
    thunar-archive-plugin       # Comprimir/descomprimir desde el menú
    thunar-volman
  ];
  services.tumbler.enable = true;              # Miniaturas de imágenes
  services.gvfs.enable = true;                 # Montajes (USB, red, papelera)
  programs.firefox.enable = true;
  services.flatpak.enable = true;              # Zen Browser (lo instala init.sh)

  users.users.${config.dotfiles.usuario}.packages = with pkgs; [
    kdePackages.kate
  ];

  # --------------------------------------------------
  # ---           Paquetes del escritorio          ---
  # --------------------------------------------------
  environment.systemPackages = with pkgs; [
    kitty
    waybar
    rofi                        # Lanzador de aplicaciones y menús
    mako                        # Demonio de notificaciones ligero (esencial para KDE Connect)
    libnotify                   # Proporciona el comando 'notify-send' (esencial para Mako)
    swaybg                      # Fondo de pantalla
    hypridle                    # Bloquea con hyprlock antes de suspender (config/hypr/hypridle.conf)
    # swaylock-effects          # Bloqueo de wayland (reemplazado por hyprlock, ver programs.hyprlock)
    wl-clipboard                # Gestión del portapapeles en Wayland
    grim                        # El capturador
    slurp                       # El selector de área
    networkmanagerapplet        # Gestor de red
    pwvucontrol                 # Gestor de volumen gráfico de PipeWire (clic en el volumen de Waybar)
    pulseaudio                  # Proporciona el comando 'paplay' para reproducir el sonido (.oga)
    sound-theme-freedesktop     # Los sonidos base del sistema
    playerctl                   # Módulo de música
    brightnessctl               # Utilidad para brillo
    appimage-run                # Para ejecutar programas en formato AppImage sin problemas
    imagemagick                 # Cambiar resolución, tamaño, formato (y vistas del selector de temas)

    # Apariencia (los nombres que se usan están en tema/tema.conf)
    catppuccin-cursors.mochaSky    # Cursor celeste (Nova)
    catppuccin-cursors.mochaRed    # Cursor rojo (Carmesí)
    catppuccin-cursors.mochaPink   # Cursor rosa (Neón)
    catppuccin-cursors.mochaBlue   # Cursor azul (Noche)
    catppuccin-cursors.mochaYellow # Cursor amarillo (Relámpago)
    catppuccin-cursors.mochaMauve  # Cursor malva (Violeta)
    papirus-icon-theme          # Iconos
    adwaita-icon-theme          # Iconos y cursores base oscuros
    gnome-themes-extra          # Adwaita-dark (solo para apps GTK2)
    adw-gtk3                    # Tema GTK3/GTK4 con colores redefinibles: los pone el tema (gtk.css)
    gsettings-desktop-schemas   # El diccionario de reglas visuales
    glib                        # Provee el comando gsettings
    nwg-look                    # Gestor gráfico de apariencia exclusivo para Wayland/Hyprland
    # kdePackages.breeze        # Tema nativo para familia KDE - Qt (KDE connect, navicat, etc)
    # kdePackages.breeze-icons  # Iconos oficiales para que no falten carpetas

    # Aplicaciones de escritorio
    # kdePackages.dolphin       # El gestor de archivos moderno de KDE (Qt6)
    file-roller                 # Interfaz gráfica para comprimir/descomprimir
    onlyoffice-desktopeditors   # Editor de documentos
    zathura                     # Para visualizar pdf
    imv                         # Para visualizar imágenes
  ];

  environment.shellAliases = {
    # Tema global (colores, fuente, fondo): elegir con SUPER + F2, o editar y aplicar
    tema-config = "micro ~/dotfiles/tema/tema.conf";
    tema-aplicar = "~/dotfiles/utils/aplicar-tema.sh";

    hypr-config = "micro ~/dotfiles/config/hypr/hyprland.conf";
    kitty-config = "micro ~/dotfiles/config/kitty/kitty.conf";
    waybar-config = "micro ~/dotfiles/config/waybar/config";
  };
}
