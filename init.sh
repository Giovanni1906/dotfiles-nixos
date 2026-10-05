echo "permisos ... "
# Pedir contraseña de administrador al inicio
sudo -v
# Mantener vivo a sudo mientras el script siga corriendo
while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &

echo "🚀 Iniciando configuración de dotfiles..."

# 1. Crear directorios base por si no existen en un sistema nuevo
mkdir -p ~/.config
mkdir -p ~/.icons/default
mkdir -p ~/.local/share/icons/default
mkdir -p ~/Imágenes/CapturasPantalla
# Archivo .env
echo "Creando archivo de .env"
## Crea el archivo vacío
touch ~/dotfiles/.env
## permisos de seguridad de inmediato
chmod 600 ~/dotfiles/.env

# 3. Enlaces simbólicos de aplicaciones (Usamos -sfn para forzar y evitar anidaciones)
rm -rf ~/.config/hypr ~/.config/waybar ~/.config/kitty ~/.config/rofi ~/.config/mako ~/.config/swaylock ~/.local/share/icons/icons
ln -sfn ~/dotfiles/config/hypr ~/.config/hypr
ln -sfn ~/dotfiles/config/waybar ~/.config/waybar
ln -sfn ~/dotfiles/config/kitty ~/.config/kitty
ln -sfn ~/dotfiles/config/fastfetch ~/.config/fastfetch
ln -sfn ~/dotfiles/config/rofi ~/.config/rofi
ln -sfn ~/dotfiles/config/mako ~/.config/mako
ln -sfn ~/dotfiles/config/swaylock ~/.config/swaylock
ln -sfn ~/dotfiles/icons ~/.local/share/icons

# 4. Enlaces simbólicos de GTK (Unificando todas las versiones)
rm -rf ~/.config/gtk-3.0 ~/.config/gtk-4.0 ~/.gtkrc-2.0 ~/.config/gtkrc
ln -sfn ~/dotfiles/config/gtk-3.0 ~/.config/gtk-3.0
ln -sfn ~/dotfiles/config/gtk-4.0 ~/.config/gtk-4.0
ln -sfn ~/dotfiles/config/gtkrc-2.0 ~/.gtkrc-2.0
ln -sfn ~/dotfiles/config/gtkrc-2.0 ~/.config/gtkrc

# 5. Permisos de ejecución a los scripts
chmod +x ~/dotfiles/config/waybar/scripts/pomo.sh
chmod +x ~/dotfiles/config/waybar/scripts/powermenu.sh
chmod +x ~/dotfiles/utils/reset-trial-navicat.sh
chmod +x ~/dotfiles/utils/valent-clipboard.sh
chmod +x ~/dotfiles/utils/kitty-zoom.sh
chmod +x ~/dotfiles/utils/atajos.sh
chmod +x ~/dotfiles/utils/aplicar-tema.sh

# Tema global: genera los archivos tema.* de config/ desde tema/tema.conf
~/dotfiles/utils/aplicar-tema.sh
source ~/dotfiles/tema/tema.conf

# 6. Forzar enlaces del cursor del tema directo desde NixOS
rm -rf ~/.icons/"$CURSOR" ~/.local/share/icons/"$CURSOR"
ln -sfn /run/current-system/sw/share/icons/"$CURSOR" ~/.icons/"$CURSOR"
ln -sfn /run/current-system/sw/share/icons/"$CURSOR" ~/.local/share/icons/"$CURSOR"

# 7. Variables de entorno en .bash_profile (Con un candado de seguridad)
# Este 'if' verifica que no se dupliquen las líneas si ejecutas el script 2 veces
if ! grep -q "XCURSOR_PATH" ~/.bash_profile 2>/dev/null; then
    echo 'export XCURSOR_PATH="/run/current-system/sw/share/icons:~/.icons:~/.local/share/icons"' >> ~/.bash_profile
    echo "export XCURSOR_THEME=\"$CURSOR\"" >> ~/.bash_profile
    echo "Agregadas variables de entorno al .bash_profile"
fi

# 8. Forzar archivo index.theme por defecto a fuego
echo -e "[Icon Theme]\nInherits=$CURSOR" > ~/.icons/default/index.theme
echo -e "[Icon Theme]\nInherits=$CURSOR" > ~/.local/share/icons/default/index.theme

echo "✅ ¡Dotfiles instalados correctamente! Reinicia la sesión o aplica nix-switch."

#9. intalación de paquetes desde Faltpak

# Se asegura que el repositorio principal de Flathub esté agregado
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

flatpak install -y flathub io.github.zen_browser.zen

#10. instalación de paquetes por AppImages
# carpeta oculta para los AppImages
mkdir -p ~/.local/bin/appimages

# Thorium: Descarga del programa real                                                            
echo "Descargando Thorium..."                                         
 wget -O ~/.local/bin/appimages/Thorium.AppImage "https://github.com/Alex313031/Thorium/releases/download/M128.0.6613.189/Thorium_Browser_128.0.6613.189_AVX2.AppImage"
 chmod +x ~/.local/bin/appimages/Thorium.AppImage                      

# Thorium: Creación del acceso directo en el menú (drun)
 echo "Enlazando acceso directo de Thorium..."
 mkdir -p ~/.local/share/applications
 ln -sf ~/dotfiles/applications/thorium.desktop ~/.local/share/applications/thorium.desktop

# ...

# Conectar tailscale
echo "Iniciando sesion en tailscale (github)"
sudo tailscale up

