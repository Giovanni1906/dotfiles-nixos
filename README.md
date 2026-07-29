## Configuración del cursor: 
### Para configurar el cursor se debe instalar el paquete desde:
~/dotfiles/[tipo-de-equipo]/configuration.nix

 environment.systemPackages = with pkgs; [
    kitty
    waybar
    ...
    pulsemixer 			   # Mezclador interactivo ultra ligero
    catppuccin-cursors.mochaSky     # paquete de cursor bibata
    glib                      # Provee el comando gsettings
    kdePackages.breeze        # Tema nativo de Dolphin
    kdePackages.breeze-icons  # Iconos oficiales para que no falten carpetas
    gsettings-desktop-schemas # El diccionario de reglas visuales
    adwaita-icon-theme        # Iconos y cursores base oscuros

### luego configurar el nombre del paquete desde index.themes
~/dotfiles/icons/default/index.theme

[Icon Theme]
Name=Default
Comment=Default Cursor Theme
Inherits=catppuccin-mocha-sky-cursors

### Y hyprland.conf
~/dotfiles/config/hypr/hyprland.conf

env = HYPRCURSOR_THEME,catppuccin-mocha-sky-cursors
env = XCURSOR_THEME,catppuccin-mocha-sky-cursors
env = HYPRCURSOR_SIZE,24
env = XCURSOR_SIZE,24
... 

# Preferencias del sistema (modo oscuro)
exec-once = gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
exec-once = gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark'
exec-once = gsettings set org.gnome.desktop.interface cursor-theme 'catppuccin-mocha-sky-cursors'

# Comandos para valent
### Bloquear pantalla
swaylock --screenshots --clock --indicator --effect-blur 7x5 --effect-vignette 0.5:0.5 --fade-in 0.2
### Desbloquear pantalla
killall swaylock
### Apagar pc
systemctl poweroff
### Suspender pc
swaylock -f --screenshots --clock --indicator --effect-blur 7x5 --effect-vignette 0.5:0.5 --fade-in 0.2 && sleep 1 && systemctl suspend

# Environents
#### copiar y pegar el .env.example y cambiar los datos a los reales
