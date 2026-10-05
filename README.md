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
Abre el archivo recién copiado y asegúrate de que la línea de `imports` solo llame al hardware local y no a configuraciones de otras PCs. El módulo del tema (GRUB, login y cursor) se importa con ruta absoluta, porque la ruta relativa `../tema/tema.nix` solo funciona dentro del repo:
```bash
sudo nano /etc/nixos/configuration.nix
# Debe decir:
# imports = [ ./hardware-configuration.nix /home/<tu_usuario>/dotfiles/tema/tema.nix ];
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

## Tema: colores, tipografía, cursor y fondo

Todo el aspecto visual sale de un solo archivo, `tema/tema.conf`: colores, transparencias, radio de las esquinas, grosor del borde, fuente, fondo de pantalla, cursor e iconos. Al cambiarlo se actualizan juntos Hyprland, Waybar, Kitty, Rofi, Mako (notificaciones), swaylock, GTK, fastfetch, el menú de GRUB y la pantalla de inicio de sesión.

```bash
tema-config    # Abre tema/tema.conf
tema-aplicar   # Regenera los archivos tema.* de config/ y recarga el escritorio al instante
nix-switch     # Reconstruye GRUB y la pantalla de inicio de sesión (se ven en el próximo arranque)
```

- `utils/aplicar-tema.sh` (alias `tema-aplicar`) escribe `config/hypr/tema.conf`, `config/waybar/tema.css`, `config/kitty/tema.conf`, `config/rofi/tema.rasi`, `config/mako/config` y `config/swaylock/config`, y ajusta los ajustes de GTK y fastfetch. Esos archivos son generados: no se editan a mano.
- `tema/tema.nix` es un módulo de NixOS que lee el mismo archivo y construye el tema de GRUB (fondo, fuentes, iconos y cajas redondeadas) y el inicio de sesión (greetd + nwg-hello sobre un Hyprland mínimo con el fondo de pantalla desenfocado).
- El cursor y los iconos deben estar instalados en `environment.systemPackages` de `configuration.nix` (por defecto `catppuccin-cursors.mochaSky` y `papirus-icon-theme`), y la fuente en `fonts.packages`.

## Comandos para valent

### Bloquear pantalla

```bash
swaylock
```

Las opciones (reloj, desenfoque y colores) están en `config/swaylock/config`, generado desde el tema.

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
swaylock -f && sleep 1 && systemctl suspend
```
