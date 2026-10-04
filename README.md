# Dotfiles NixOS

Este repositorio contiene mi configuración personal de NixOS, Hyprland y varias herramientas de escritorio. La instalación está pensada para simplificarse con `init.sh`, que crea enlaces simbólicos y deja listo el entorno base.

## Instalación rápida en una PC Nueva (NixOS)

> **Importante:** Instala NixOS usando la opción "No Desktop" y activa "Allow unfree software".

**1. Clona el repositorio temporalmente**
Inicia sesión en tu nuevo sistema y descarga los dotfiles:
```bash
nix-shell -p git
git clone [https://github.com/tu_usuario/tu_repositorio.git](https://github.com/tu_usuario/tu_repositorio.git) ~/dotfiles
```

**2. Copia la configuración del sistema (¡No uses enlaces simbólicos!)**
Para evitar un pánico del kernel por incompatibilidad de discos, debes **copiar** tu configuración general respetando el hardware de la máquina nueva:
```bash
sudo cp ~/dotfiles/ruta_de_tu_carpeta/configuration.nix /etc/nixos/configuration.nix
```

**3. Verifica las importaciones**
Abre el archivo recién copiado y asegúrate de que la línea de `imports` solo llame al hardware local y no a configuraciones de otras PCs:
```bash
sudo nano /etc/nixos/configuration.nix
# Debe decir: imports = [ ./hardware-configuration.nix ];
```

**4. Aplica los cambios del sistema base**
Este paso descargará todos los paquetes esenciales, gestores de ventanas y dependencias necesarias (asegúrate de que `appimage-run` esté en tus systemPackages):
```bash
sudo nixos-rebuild switch
```

**5. Configura tus secretos**
Revisa y ajusta tu archivo `.env` a partir de `.env.example`:
```bash
cp ~/dotfiles/.env.example ~/dotfiles/.env
nano ~/dotfiles/.env
```

**6. Ejecuta el script de personalización**
Una vez que el sistema base está instalado, despliega tu entorno gráfico (Hyprland, Waybar, temas y AppImages):
```bash
cd ~/dotfiles
./init.sh
```

**7. Configura el acceso a GitHub (para hacer `git push`)**
`gh` ya viene instalado desde `configuration.nix`. Inicia sesión (elige GitHub.com, HTTPS y "Login with a web browser") y deja que git use esas credenciales:
```bash
gh auth login
gh auth setup-git
```
`gh auth setup-git` guarda en `~/.gitconfig` la ruta de `gh` dentro de `/nix/store`, que desaparece al actualizar `gh` y limpiar el store. Cámbiala por el comando `gh` del sistema:
```bash
for h in https://github.com https://gist.github.com; do
  git config --global --replace-all "credential.$h.helper" '!gh auth git-credential' '/nix/store/'
done
```
Comprueba que funciona con `git ls-remote origin HEAD` (debe responder sin pedir usuario).

**8. Reinicia el sistema**
Aplica todos los cambios y entra a tu nuevo entorno.

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
