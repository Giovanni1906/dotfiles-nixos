# Flujo de Trabajo y Comandos Comunes

## Requisitos Previos

- PC x86_64 con NixOS instalado con la opción **"No Desktop"** y **"Allow unfree software"** marcados.
- Conexión a internet (Nix, Flathub, descarga de Thorium desde GitHub, Tailscale).
- Cuenta de Tailscale (el login se hace con GitHub durante `init.sh`).
- Celular con Valent/KDE Connect si se quieren los comandos remotos.

## Instalación en una máquina nueva

1. Clonar el repositorio:
   ```bash
   nix-shell -p git
   git clone https://github.com/Giovanni1906/dotfiles-nixos.git ~/dotfiles
   ```
2. Crear la carpeta del equipo con el hardware **de la máquina nueva** (no reutilizar el `hardware-configuration.nix` de otro equipo):
   ```bash
   mkdir ~/dotfiles/nixos-<equipo>
   cp /etc/nixos/hardware-configuration.nix ~/dotfiles/nixos-<equipo>/
   cp ~/dotfiles/nixos-pc-asus/configuration.nix ~/dotfiles/nixos-<equipo>/
   ```
   Revisar en `configuration.nix`: `imports = [ ./hardware-configuration.nix ];`, `networking.hostName`, usuario y `system.stateVersion`.
3. Hacer que `/etc/nixos` apunte al repo (así está el equipo actual) **o** copiar los archivos (lo que recomienda el README):
   ```bash
   sudo ln -sfn ~/dotfiles/nixos-<equipo>/configuration.nix /etc/nixos/configuration.nix
   sudo ln -sfn ~/dotfiles/nixos-<equipo>/hardware-configuration.nix /etc/nixos/hardware-configuration.nix
   ```
4. Aplicar el sistema: `sudo nixos-rebuild switch`
5. Secretos: `cp ~/dotfiles/.env.example ~/dotfiles/.env && micro ~/dotfiles/.env`
6. Capa de usuario: `cd ~/dotfiles && bash init.sh` (pide `sudo` al inicio y lo mantiene vivo; al final abre el login de Tailscale).
7. Acceso a GitHub para `git push`: `gh auth login` + `gh auth setup-git`, y cambiar en `~/.gitconfig` la ruta de `/nix/store/…/gh` por `!gh auth git-credential` (ver README, paso 7; si no, deja de funcionar tras actualizar `gh` + GC).
8. Reiniciar. Entrar desde `tuigreet`.
9. Pasos manuales que el repo no automatiza: emparejar el celular en Valent, configurar sus comandos remotos (ver README) y actualizar el ID de dispositivo en `utils/valent-clipboard.sh`.

## Ciclo de cambios diario

| Qué cambias | Dónde | Cómo se aplica |
| --- | --- | --- |
| Paquetes, servicios, firewall, aliases | `nixos-pc-asus/configuration.nix` | `nix-switch` (abre una nueva generación) |
| Atajos, autoarranque, reglas de ventanas | `config/hypr/hyprland.conf` | Hyprland recarga solo al guardar; `exec-once` requiere cerrar sesión (`SUPER + M`) |
| Barra | `config/waybar/{config,style.css}` | `pkill waybar && waybar &` (o `pkill -SIGUSR2 waybar`) |
| Terminal | `config/kitty/kitty.conf` | `ctrl+shift+F5` en Kitty o abrir una ventana nueva |
| Lanzador / menú de apagado | `config/rofi/`, `config/waybar/scripts/powermenu.sh` | Inmediato en la siguiente apertura |
| Temas GTK | `nwg-look` (reescribe `config/gtk-*`) | Reiniciar la app |
| Secretos | `.env` | Inmediato (se lee con `source` en cada uso) |

Después de cada cambio que funcione: `git add -A && git commit -m "feat|fix|docs: …" && git push`. Si el cambio altera la arquitectura, actualizar `docs/contexto/`.

## Aliases disponibles (definidos en `configuration.nix`)

| Alias | Comando |
| --- | --- |
| `nix-switch` | `sudo nixos-rebuild switch` |
| `nix-clean` | Borra generaciones viejas, `nixos-rebuild boot` y `nix-store --gc` |
| `nix-config` | `sudo micro /etc/nixos/configuration.nix` (en este equipo es el mismo archivo del repo) |
| `hypr-config`, `kitty-config`, `waybar-config` | Abren la config correspondiente con `sudo micro` |
| `ll` | `ls -lha` |
| `d`, `dc-up`, `dc-down` | Docker / `docker compose up -d` / `down` |
| `k` | `kubectl` (no instalado actualmente) |
| `remote-conexion` | `wayvnc 0.0.0.0` |
| `reset-trial-navicat` | `~/dotfiles/utils/reset-trial-navicat.sh` |
| `ip-public` | `curl -s ipinfo.io/ip` |

## Atajos

La lista completa (Hyprland, Kitty y Waybar) está en `utils/atajos.txt` y se ve con **`SUPER + F1`** o con el botón del teclado en Waybar (módulo `custom/atajos`); ambos ejecutan `utils/atajos.sh` (Rofi; escribir filtra). Es la única fuente: no duplicarla aquí. Al añadir, quitar o cambiar un atajo, actualizar ese archivo en el mismo cambio (ver `.cursor/rules/docs-y-filosofia.mdc`).

## Comandos de Valent (comandos remotos desde el celular)

```bash
# Bloquear
swaylock --screenshots --clock --indicator --effect-blur 7x5 --effect-vignette 0.5:0.5 --fade-in 0.2
# Desbloquear
source ~/dotfiles/.env && wtype "$PASS_SWAYLOCK" && wtype -k Return
# Apagar
systemctl poweroff
# Suspender
swaylock -f --screenshots --clock --indicator --effect-blur 7x5 --effect-vignette 0.5:0.5 --fade-in 0.2 && sleep 1 && systemctl suspend
```

## Diagnóstico rápido

```bash
hyprctl configerrors                 # errores de sintaxis en hyprland.conf
hyprctl version
pgrep -a wayvnc; pgrep -a polkit     # verificar que el autoarranque funcionó
journalctl --user -b | grep -i <app> # logs de la sesión
sudo nixos-rebuild dry-build         # validar configuration.nix sin activar
nixos-rebuild list-generations       # ver generaciones para hacer rollback
sudo nixos-rebuild switch --rollback # volver a la generación anterior
```

## Testing y Despliegue

- **Tests**: no existen. La validación es manual: `nixos-rebuild dry-build` para Nix, `hyprctl configerrors` para Hyprland y probar en la sesión.
- **CI/CD**: no hay pipeline (no existe `.github/workflows/`). El "despliegue" es `git pull` en la máquina + `nix-switch` y/o volver a ejecutar `init.sh`.
- **Rollback**: a nivel de sistema, las generaciones de NixOS (menú de systemd-boot o `--rollback`); a nivel de usuario, `git revert`/`git checkout` del archivo (los symlinks aplican el cambio al instante).
