#!/bin/bash

echo "🚀 Iniciando configuración de dotfiles..."

# 1. Crear directorios base por si no existen en un sistema nuevo
mkdir -p ~/.config
mkdir -p ~/.icons/default
mkdir -p ~/.local/share/icons/default

# 2. Configuración de NixOS (Requiere permisos de administrador)
# Recomendación: Hacer backup de la carpeta original antes de enlazar
sudo mv /etc/nixos /etc/nixos.bak 2>/dev/null || true
# IMPORTANTE: Descomentar la siguiente línea y ajustar [equipo] cuando lo uses
# sudo ln -sfn ~/dotfiles/nixos-[equipo] /etc/nixos

# 3. Enlaces simbólicos de aplicaciones (Usamos -sfn para forzar y evitar anidaciones)
rm -rf ~/.config/hypr ~/.config/waybar ~/.config/kitty ~/.local/share/icons/icons
ln -sfn ~/dotfiles/config/hypr ~/.config/hypr
ln -sfn ~/dotfiles/config/waybar ~/.config/waybar
ln -sfn ~/dotfiles/config/kitty ~/.config/kitty
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

# 6. Forzar enlaces del cursor Catppuccin directo desde NixOS
rm -rf ~/.icons/catppuccin-mocha-sky-cursors ~/.local/share/icons/catppuccin-mocha-sky-cursors
ln -sfn /run/current-system/sw/share/icons/catppuccin-mocha-sky-cursors ~/.icons/catppuccin-mocha-sky-cursors
ln -sfn /run/current-system/sw/share/icons/catppuccin-mocha-sky-cursors ~/.local/share/icons/catppuccin-mocha-sky-cursors

# 7. Variables de entorno en .bash_profile (Con un candado de seguridad)
# Este 'if' verifica que no se dupliquen las líneas si ejecutas el script 2 veces
if ! grep -q "XCURSOR_PATH" ~/.bash_profile 2>/dev/null; then
    echo 'export XCURSOR_PATH="/run/current-system/sw/share/icons:~/.icons:~/.local/share/icons"' >> ~/.bash_profile
    echo 'export XCURSOR_THEME="catppuccin-mocha-sky-cursors"' >> ~/.bash_profile
    echo "Agregadas variables de entorno al .bash_profile"
fi

# 8. Forzar archivo index.theme por defecto a fuego
echo -e "[Icon Theme]\nInherits=catppuccin-mocha-sky-cursors" > ~/.icons/default/index.theme
echo -e "[Icon Theme]\nInherits=catppuccin-mocha-sky-cursors" > ~/.local/share/icons/default/index.theme

echo "✅ ¡Dotfiles instalados correctamente! Reinicia la sesión o aplica nix-switch."
