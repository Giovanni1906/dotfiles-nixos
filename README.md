# Dotfiles NixOS

Mi configuración personal de NixOS + Hyprland, pensada para varias máquinas (PC, laptop...) que comparten lo mismo y solo cambian en lo que cada una soporta. `init.sh` instala y actualiza todo.

## Cómo está organizado

```
dotfiles/
├── init.sh            # Instala y actualiza (./init.sh --help)
├── nixos/             # Sistema (root): se aplica con nix-switch
│   ├── modulos/       # Piezas por función: base, escritorio, tema, desarrollo, remoto, juegos
│   └── equipos/       # Una carpeta por máquina: qué módulos usa, nombre, arranque
│       ├── pc-asus/
│       └── plantilla/ # Base para equipos nuevos (./init.sh nuevo-equipo <nombre>)
├── config/            # Configuración de cada app, enlazada en ~/.config/<app>
├── tema/temas/        # Temas completos (colores, fuente, fondo); se eligen con SUPER + F2
├── utils/             # Scripts: tema, selector de temas, lista de atajos, Kitty, Valent
├── applications/      # Accesos directos .desktop (Thorium)
├── public/            # Fondos de pantalla y logos
└── docs/contexto/     # Arquitectura, convenciones y decisiones del proyecto
```

- **Lo compartido** entre máquinas son los módulos de `nixos/modulos/` y todo `config/`: un `git pull` lo lleva a todas.
- **Lo propio de cada máquina** es su carpeta en `nixos/equipos/`. Ahí elige qué módulos importa: por ejemplo, la PC importa `juegos.nix` y la laptop no.
- **El hardware nunca está en el repo.** Cada máquina usa el `/etc/nixos/hardware-configuration.nix` que generó su instalación; así una configuración no puede arrancar con los discos de otra PC.
- **Lo local** no se versiona: el tema elegido (`tema/tema.conf`), los monitores o el touchpad (`config/hypr/local.conf`), `.env` y los archivos que genera el tema.

`/etc/nixos/configuration.nix` lo escribe `init.sh` y solo contiene esto:

```nix
{ imports = [ ./hardware-configuration.nix /home/nova/dotfiles/nixos/equipos/pc-asus ]; }
```

## Instalación en una máquina nueva

> Instala NixOS con la opción "No Desktop" y "Allow unfree software". Usa el usuario `nova` (lo definen los módulos).

```bash
nix-shell -p git
git clone https://github.com/Giovanni1906/dotfiles-nixos.git ~/dotfiles
cd ~/dotfiles
./init.sh
```

`init.sh` pregunta qué equipo es esta máquina. Si eliges "Nuevo equipo", crea `nixos/equipos/<nombre>` desde la plantilla, con la versión de NixOS de la instalación. Después:

1. Enlaza `config/` en `~/.config`, aplica el tema y crea los archivos locales (`.env`, `config/hypr/local.conf`).
2. Escribe `/etc/nixos/configuration.nix` apuntando al equipo, conserva el `hardware-configuration.nix` de la máquina y ejecuta `nixos-rebuild switch`. Lo que reemplaza lo deja en `/etc/nixos/*.respaldo-<fecha>`.
3. Instala Zen Browser (Flatpak) y Thorium (AppImage) si faltan.
4. Inicia sesión en Tailscale si no hay sesión.

Si creaste un equipo nuevo, revisa qué módulos importa (`nix-config`), vuelve a ejecutar `nix-switch` si cambiaste algo y súbelo: `git add nixos/equipos/<nombre> && git commit -m "feat: equipo <nombre>" && git push`.

Luego completa `.env` (ver más abajo), configura GitHub y reinicia.

### Acceso a GitHub (para `git push`)

`gh` viene instalado. Inicia sesión (GitHub.com, HTTPS, "Login with a web browser") y deja que git use esas credenciales:

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

## Día a día

| Quiero... | Hago |
| --- | --- |
| Traer a esta máquina lo que cambié en otra | `dotfiles-actualizar` (`git pull` + enlaces y tema + `nixos-rebuild switch`) |
| Cambiar la config de una app | Editar `config/<app>/` (se aplica al recargar la app) y hacer commit |
| Un paquete o servicio para todas las máquinas | Añadirlo al módulo que corresponda en `nixos/modulos/` y `nix-switch` |
| Un paquete solo para esta máquina | Añadirlo en `nixos/equipos/<equipo>/default.nix` (`nix-config`) y `nix-switch` |
| Activar o quitar un grupo de cosas (juegos, desarrollo) | Comentar o descomentar su módulo en `imports` del equipo |
| Ajustar monitores o touchpad de esta máquina | `config/hypr/local.conf` (no se versiona) |
| Cambiar el tema | `SUPER + F2` |

Cada paso de `init.sh` se puede ejecutar por separado (`./init.sh usuario`, `./init.sh sistema`, `./init.sh apps`...) y repetir sin romper nada. `./init.sh sistema --simular` muestra lo que haría con `sudo` sin ejecutarlo.

## Tema: colores, tipografía, cursor y fondo

Cada archivo de `tema/temas/` es un tema completo: colores, transparencias, radio de las esquinas, borde, fuente, fondo de pantalla, cursor e iconos. Al elegir uno se actualizan juntos Hyprland, la pantalla de bloqueo (hyprlock), Waybar, Kitty, Rofi, las notificaciones (Mako), GTK y, tras `nix-switch`, el menú de GRUB y la pantalla de inicio de sesión.

- **`SUPER + F2`** abre el selector (`utils/elegir-tema.sh`): muestra cada tema con su fondo y su paleta, y aplica el elegido al instante. La última opción abre el tema activo en un editor y lo aplica al cerrarlo.
- **Temas incluidos:** Nova (por defecto), Carmesí, Violeta, Noche, Neón y Relámpago.
- **Crear un tema:** copiar `tema/temas/nova.conf` (tiene comentada cada variable) a `tema/temas/<nombre>.conf` y cambiar los valores. Aparece solo en el selector.
- **Por terminal:** `tema-config` abre el tema activo, `tema-aplicar` lo vuelve a aplicar y `tema-aplicar <nombre>` cambia de tema.

Cómo funciona:

- `tema/tema.conf` es un enlace local al tema elegido en esta máquina, así cada máquina puede tener su tema sin chocar en `git pull`.
- `utils/aplicar-tema.sh` genera desde el tema un archivo por app: `config/hypr/tema.conf`, `config/waybar/tema.css`, `config/kitty/tema.conf`, `config/rofi/tema.rasi` y `config/mako/config`. No se versionan ni se editan a mano.
- `nixos/modulos/tema.nix` lee el mismo tema y construye GRUB (fondo, fuentes, iconos y cajas redondeadas) y el inicio de sesión (greetd + nwg-hello sobre un Hyprland mínimo con el fondo desenfocado).
- La pantalla de bloqueo (`config/hypr/hyprlock.conf`) tiene el mismo diseño que el inicio de sesión. `hypridle` (`config/hypr/hypridle.conf`) la abre antes de cada suspensión.
- El cursor y los iconos de un tema deben estar instalados (`nixos/modulos/escritorio.nix`); por defecto `catppuccin-cursors.mochaSky` y `papirus-icon-theme`.

## Variables de entorno y `.env`

`.env` guarda valores sensibles (hoy `PASS_SWAYLOCK`, la contraseña para el desbloqueo remoto). `init.sh` lo crea desde `.env.example` con permisos `600`; edítalo con tus valores.

- No subas `.env` (está en `.gitignore`).
- Mantén `.env.example` con placeholders y documenta aquí cada variable nueva.

## Comandos para Valent

```bash
# Bloquear (hypridle abre hyprlock)
loginctl lock-session
# Desbloquear
source ~/dotfiles/.env && wtype "$PASS_SWAYLOCK" && wtype -k Return
# Apagar
systemctl poweroff
# Suspender (la pantalla se bloquea sola antes de dormir)
systemctl suspend
```

## Atajos

La lista completa está en `utils/atajos.txt` y se ve con `SUPER + F1` o con el botón del teclado en Waybar. Al elegir un atajo con Enter se ejecuta: los de Hyprland y Waybar siempre, los de Kitty si la lista se abrió desde una ventana de Kitty. Los grupos (`SUPER + 0-9`, `Flechas`) preguntan después el número o la dirección; los de ratón aparecen atenuados.
