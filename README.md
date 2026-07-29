# Dotfiles NixOS

Este repositorio contiene mi configuración personal de NixOS, Hyprland y varias herramientas de escritorio. La instalación está pensada para simplificarse con `init.sh`, que crea enlaces simbólicos y deja listo el entorno base.

## Instalación rápida

1. Clona el repositorio en `~/dotfiles`.
2. Revisa y ajusta tu archivo `.env` a partir de `.env.example`.
3. Ejecuta el script de inicio:

```bash
bash ~/dotfiles/init.sh
```

4. Reinicia la sesión o el sistema para aplicar los cambios.

> Nota: `init.sh` asume que el repositorio vive en `~/dotfiles`.

## Qué hace `init.sh`

El script de inicialización automatiza los pasos más repetitivos:

- crea carpetas base en `~/.config`, `~/.icons/default` y `~/.local/share/icons/default`
- prepara la configuración de NixOS
- enlaza los directorios de configuración de Hyprland, Waybar, Kitty, Fastfetch e iconos
- unifica la configuración GTK
- da permisos de ejecución a scripts auxiliares
- fuerza el uso del cursor Catppuccin desde el sistema
- agrega variables necesarias al perfil del usuario si no existen

Si quieres revisar o modificar el comportamiento del arranque, el punto principal es `init.sh`.

## Variables de entorno y `.env`

Este proyecto usa un `.env` para guardar valores sensibles o variables que pueden cambiar entre máquinas.

### Cómo configurarlo

Copia el archivo de ejemplo y renómbralo:

```bash
cp .env.example .env
```

Luego edita `.env` con tus valores reales.

### Buenas prácticas

- no subas `.env` con credenciales reales al repositorio
- mantén `.env.example` con valores de referencia o placeholders
- si agregas una nueva variable, documenta su uso en este archivo

## Cursor y temas visuales

Para que el cursor y el tema visual funcionen correctamente, asegúrate de incluir los paquetes necesarios en tu `configuration.nix`:

```nix
environment.systemPackages = with pkgs; [
  kitty
  waybar
  pulsemixer              # Mezclador interactivo ultra ligero
  catppuccin-cursors.mochaSky
  glib                    # Provee el comando gsettings
  kdePackages.breeze      # Tema nativo de Dolphin
  kdePackages.breeze-icons
  gsettings-desktop-schemas
  adwaita-icon-theme
];
```

Y revisa también estas rutas:

- `~/dotfiles/icons/default/index.theme`
- `~/dotfiles/config/hypr/hyprland.conf`

Ejemplo de variables para Hyprland:

```ini
env = HYPRCURSOR_THEME,catppuccin-mocha-sky-cursors
env = XCURSOR_THEME,catppuccin-mocha-sky-cursors
env = HYPRCURSOR_SIZE,24
env = XCURSOR_SIZE,24
```

## Preferencias del sistema

En Hyprland también se aplican preferencias visuales por defecto:

```ini
exec-once = gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
exec-once = gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark'
exec-once = gsettings set org.gnome.desktop.interface cursor-theme 'catppuccin-mocha-sky-cursors'
```

## Comandos para valent

### Bloquear pantalla

```bash
swaylock --screenshots --clock --indicator --effect-blur 7x5 --effect-vignette 0.5:0.5 --fade-in 0.2
```

### Desbloquear pantalla

```bash
source ~/dotfiles/.env && wtype "$PASS_SWAYLOCK" && wtype -k Return
```

### Apagar PC

```bash
systemctl poweroff
```

### Suspender PC

```bash
swaylock -f --screenshots --clock --indicator --effect-blur 7x5 --effect-vignette 0.5:0.5 --fade-in 0.2 && sleep 1 && systemctl suspend
```
