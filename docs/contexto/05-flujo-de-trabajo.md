# Flujo de Trabajo y Comandos Comunes

## Requisitos Previos

- PC x86_64 con NixOS instalado con la opción **"No Desktop"** y **"Allow unfree software"** marcados, y usuario `nova`.
- Repo clonado en `~/dotfiles` (las rutas son absolutas).
- Conexión a internet (Nix, Flathub, descarga de Thorium desde GitHub, Tailscale).
- Cuenta de Tailscale (el login se hace con GitHub durante `init.sh`).
- Celular con Valent/KDE Connect si se quieren los comandos remotos.

## Gestión de tareas (tablero kanban)

Las tareas del proyecto viven en el tablero de Notion [nixos](https://app.notion.com/p/nixos-3f0bf08bb2f880849364ea3f4cb40c2d), con los estados Not started → In progress → In revision → Done. Cada tarjeta lleva diagnóstico, pasos y verificación. El agente mueve las tarjetas hasta In revision; el usuario las revisa y las pasa a Done. La regla `.cursor/rules/kanban-notion.mdc` lo aplica en cada sesión de Cursor.

## Instalación en una máquina nueva

1. Clonar y ejecutar:
   ```bash
   nix-shell -p git
   git clone https://github.com/Giovanni1906/dotfiles-nixos.git ~/dotfiles
   cd ~/dotfiles && ./init.sh
   ```
2. `init.sh` pregunta el equipo. Para una máquina que aún no existe en el repo, elegir "Nuevo equipo": copia `nixos/equipos/plantilla` con el nombre y la `stateVersion` de la instalación. Si la máquina arranca en BIOS (sin `/sys/firmware/efi`), avisa para cambiar el cargador de arranque.
3. El script enlaza `config/`, aplica el tema, escribe `/etc/nixos/configuration.nix` (importa el `hardware-configuration.nix` que generó el instalador y el equipo), ejecuta `nixos-rebuild switch`, instala Zen y Thorium y abre el login de Tailscale. Al final resume los avisos.
4. Equipo nuevo: revisar qué módulos importa (`nix-config`), `nix-switch` si se cambió algo, y subirlo (`git add nixos/equipos/<equipo>`).
5. Completar `.env` (lo crea `init.sh` desde `.env.example`).
6. Acceso a GitHub para `git push`: `gh auth login` + `gh auth setup-git`, y cambiar en `~/.gitconfig` la ruta de `/nix/store/…/gh` por `!gh auth git-credential` (ver README; si no, deja de funcionar tras actualizar `gh` + GC).
7. Reiniciar. Entrar desde la pantalla de login (`nwg-hello`).
8. Pasos manuales que el repo no automatiza: emparejar el celular en Valent, configurar sus comandos remotos (ver README) y actualizar el ID de dispositivo en `utils/valent-clipboard.sh`.

## Llevar cambios de una máquina a otra

1. En la máquina donde se hizo el cambio: `git add … && git commit -m "…" && git push`.
2. En las demás: `dotfiles-actualizar` (= `./init.sh actualizar`): `git pull --rebase --autostash`, vuelve a enlazar y aplicar el tema y ejecuta `nixos-rebuild switch` con el equipo de esa máquina.

Lo que cambia en `config/` se aplica en cuanto llega el `pull` (las carpetas están enlazadas); lo de `nixos/` necesita el `switch`. Cada máquina solo recibe lo que importa su equipo: un paquete añadido a `juegos.nix` no llega a un equipo que no importa ese módulo.

## Ciclo de cambios diario

| Qué cambias | Dónde | Cómo se aplica |
| --- | --- | --- |
| Tema completo | `SUPER + F2` o `tema-aplicar <nombre>` | Escritorio al instante; `nix-switch` para GRUB y login |
| Valores del tema activo | `tema-config` (o "Editar el tema activo" en el selector) | `tema-aplicar` (el selector lo hace solo) |
| Nuevo tema | Copiar `tema/temas/nova.conf` a `tema/temas/<nombre>.conf` | Aparece en el selector |
| Diseño de GRUB o del login | `nixos/modulos/tema.nix` | `nix-switch`; se ve en el próximo arranque |
| Paquete o servicio común | El módulo de `nixos/modulos/` que corresponda | `nix-switch` (y `dotfiles-actualizar` en las demás) |
| Paquete o servicio de una máquina | `nixos/equipos/<equipo>/default.nix` (`nix-config`) | `nix-switch` |
| Activar o quitar un grupo de funciones | Comentar o descomentar el módulo en `imports` del equipo | `nix-switch` |
| Atajos, autoarranque, reglas de ventanas | `config/hypr/hyprland.conf` (+ `utils/atajos.txt`) | Hyprland recarga solo al guardar; `exec-once` requiere cerrar sesión (`SUPER + M`) |
| Monitores, touchpad u otro ajuste de una máquina | `config/hypr/local.conf` (no se versiona) | Hyprland recarga solo |
| Barra | `config/waybar/{config,style.css}` | `pkill -USR2 -f '^waybar( \|$)'` |
| Terminal | `config/kitty/kitty.conf` | `ctrl+shift+F5` en Kitty o abrir una ventana nueva |
| Lanzador y menús | `config/rofi/` (diseño en `themes/nova.rasi`), `config/waybar/scripts/powermenu.sh` | Inmediato en la siguiente apertura |
| Temas GTK | `nwg-look` (reescribe `config/gtk-*`; `tema-aplicar` vuelve a poner tema, iconos y cursor) | Reiniciar la app |
| Secretos | `.env` | Inmediato (se lee con `source` en cada uso) |

Después de cada cambio que funcione: `git add -A && git commit -m "feat|fix|docs: …" && git push`. Si el cambio altera la arquitectura, actualizar `docs/contexto/`.

## `init.sh`

| Comando | Qué hace |
| --- | --- |
| `./init.sh` | Todo: usuario, sistema, apps y red (pregunta el equipo si no lo sabe) |
| `./init.sh usuario` | Enlaces en `~/.config`, `.env` y `local.conf`, permisos, tema. Sin `sudo` |
| `./init.sh sistema [equipo]` | Escribe `/etc/nixos/configuration.nix`, migra symlinks antiguos, conserva o regenera el hardware y `nixos-rebuild switch` |
| `./init.sh apps` | Flathub + Zen Browser y Thorium, si faltan |
| `./init.sh red` | `tailscale up` si no hay sesión |
| `./init.sh actualizar` | `git pull` + usuario + sistema |
| `./init.sh nuevo-equipo <nombre>` | Crea `nixos/equipos/<nombre>` desde la plantilla |
| `--simular` | Muestra los comandos con `sudo` sin ejecutarlos |

Todo es repetible: lo que ya está hecho se salta, y lo que se reemplaza se respalda en `~/.local/state/dotfiles/respaldo/` o `/etc/nixos/*.respaldo-<fecha>`.

## Aliases disponibles

| Alias | Comando | Módulo |
| --- | --- | --- |
| `nix-switch` | `sudo nixos-rebuild switch` | base |
| `nix-clean` | Borra las generaciones viejas y los paquetes sin uso (`nix-collect-garbage -d`) y rehace el menú de GRUB (`nixos-rebuild boot`) | base |
| `nix-config` | Abre `nixos/equipos/<equipo actual>/default.nix` | base |
| `dotfiles-actualizar` | `~/dotfiles/init.sh actualizar` | base |
| `ll` | `ls -lha` | base |
| `ip-public` | `curl -s ipinfo.io/ip` | base |
| `tema-config` | Abre el tema activo (`tema/tema.conf`) | escritorio |
| `tema-aplicar [nombre]` | `utils/aplicar-tema.sh` (genera los `tema.*` y recarga el escritorio) | escritorio |
| `hypr-config`, `kitty-config`, `waybar-config` | Abren la config correspondiente con `micro` | escritorio |
| `d`, `dc-up`, `dc-down` | Docker / `docker compose up -d` / `down` | desarrollo |
| `k` | `kubectl` (no instalado actualmente) | desarrollo |
| `reset-trial-navicat` | `utils/reset-trial-navicat.sh` | desarrollo |
| `remote-conexion` | `utils/wayvnc-tailscale.sh` (WayVNC solo en la IP de Tailscale; ya arranca al iniciar sesión) | remoto |

## Atajos

La lista completa (Hyprland, Kitty y Waybar) está en `utils/atajos.txt` y se ve con **`SUPER + F1`** o con el botón del teclado en Waybar (módulo `custom/atajos`); ambos ejecutan `utils/atajos.sh` (Rofi; escribir filtra y Enter ejecuta el atajo). Es la única fuente: no duplicarla aquí. Al añadir, quitar o cambiar un atajo, actualizar ese archivo en el mismo cambio (ver `.cursor/rules/docs-y-filosofia.mdc`).

## Comandos de Valent (comandos remotos desde el celular)

```bash
# Bloquear (hypridle abre hyprlock; diseño en config/hypr/hyprlock.conf)
loginctl lock-session
# Desbloquear
source ~/dotfiles/.env && wtype "$PASS_SWAYLOCK" && wtype -k Return
# Apagar
systemctl poweroff
# Suspender
systemctl suspend   # hypridle bloquea antes de dormir
```

## Diagnóstico rápido

```bash
hyprctl configerrors                 # errores de sintaxis en hyprland.conf
./init.sh sistema --simular          # qué haría init.sh con /etc/nixos
cat /etc/nixos/configuration.nix     # qué equipo usa esta máquina
pgrep -af wayvnc; pgrep -af waybar   # verificar el autoarranque (los procesos se llaman .x-wrapped)
journalctl --user -b | grep -i <app> # logs de la sesión
sudo nixos-rebuild dry-build         # validar la configuración sin activar
nixos-rebuild list-generations       # ver generaciones para hacer rollback
sudo nixos-rebuild switch --rollback # volver a la generación anterior
```

## Testing y Despliegue

- **Tests**: no existen. La validación es manual: `nixos-rebuild dry-build` para Nix, `hyprctl configerrors` para Hyprland, `bash -n`/`shellcheck` para scripts y probar en la sesión.
- **CI/CD**: no hay pipeline. El "despliegue" es `dotfiles-actualizar` en cada máquina.
- **Rollback**: a nivel de sistema, las generaciones de NixOS (submenú de GRUB o `--rollback`); a nivel de usuario, `git revert`/`git checkout` del archivo (los symlinks aplican el cambio al instante).
