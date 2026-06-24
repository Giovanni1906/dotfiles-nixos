# copiar el archivo de configuración de nixos a /etc/nixos
sudo ln -s ~/dotfiles/nixos-[equipo] /etc/nixos
# crear enlaces simbólicos para los archivos de configuración de hypr, waybar y kitty
ln -s ~/dotfiles/config/hypr ~/.config/hypr
ln -s ~/dotfiles/config/waybar ~/.config/waybar
ln -s ~/dotfiles/config/kitty ~/.config/kitty

# dar permisos de ejecución a los scripts
chmod +x ~/dotfiles/config/waybar/scripts/pomo.sh
chmod +x ~/dotfiles/config/waybar/scripts/powermenu.sh
