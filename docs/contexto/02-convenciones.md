# Convenciones del Proyecto

*Reglas extraídas de cómo está escrito el repositorio hoy. Si una convención se rompe en algún archivo, se indica.*

## Idioma

- Comentarios, mensajes de commit, README y notificaciones al usuario: **español**.
- Identificadores técnicos (nombres de módulos Waybar, clases CSS, opciones Nix): en inglés, tal como los exige cada herramienta.
- Variables del tema en español: `ACENTO`, `FONDO`, `SUPERFICIE` en `tema/temas/*.conf`; `$acento`, `@acento`, `@fondo`, `@superficie` en los archivos generados.

## Estructura y nomenclatura de archivos

- `config/<app>/` replica exactamente la estructura de `~/.config/<app>/` para poder enlazar la carpeta completa.
- Sistema: módulos por función en `nixos/modulos/<funcion>.nix` y una carpeta por máquina en `nixos/equipos/<tipo>-<marca>/default.nix` (ej. `pc-asus`, `laptop-hp`; minúsculas, números y guiones).
- Qué va dónde en Nix: si lo quieren todas las máquinas que usan esa función, al módulo; si es de una sola máquina, al equipo; si depende del hardware, a ninguno (queda en `/etc/nixos/hardware-configuration.nix`).
- Temas: `tema/temas/<nombre>.conf`, con las mismas variables que `nova.conf` más `NOMBRE` y `DESCRIPCION` para el selector.
- Lo propio de una máquina que no es Nix va en archivos locales ignorados por git: `config/hypr/local.conf`, `tema/tema.conf`, `.env`.
- Scripts: `kebab-case.sh` (`valent-clipboard.sh`, `elegir-tema.sh`) o nombre corto (`pomo.sh`, `powermenu.sh`).
- Scripts ligados a Waybar viven en `config/waybar/scripts/`; scripts generales en `utils/`.
- Recursos estáticos en `public/` (`background/` para fondos, `png/` para logos). Nombres sin espacios ni paréntesis (el tema los usa como rutas).

## Estilo por lenguaje

### Nix (`nixos/`)
- Cada módulo empieza con un comentario que dice qué agrupa; los equipos importan con rutas relativas (`../../modulos/x.nix`).
- Un módulo que necesita grupos para `nova` los añade en su propio archivo (`users.users.nova.extraGroups`); Nix fusiona las listas.
- Secciones delimitadas con banners de comentarios:
  ```nix
  # --------------------------------------------------
  # ---               Conectividad                 ---
  # --------------------------------------------------
  ```
- Cada paquete en `environment.systemPackages` lleva un comentario en línea explicando para qué está.
- Lo desactivado se **comenta, no se borra** (KDE Plasma, SDDM, Dolphin, breeze, el módulo `juegos.nix` en `pc-asus`). Esto sirve de historial, pero añade ruido.
- Indentación: 2 espacios (hay tabs mezclados en la lista de paquetes y aliases; normalizar a espacios al editar).
- Aliases de sistema van en `environment.shellAliases`, agrupados por tema.

### Hyprland (`hyprland.conf`)
- Encabezados `# --- TÍTULO ---` en mayúsculas y bloques `# ====` para secciones grandes.
- Variables `$mainMod`, `$terminal`, `$fileManager`, `$menu`, `$browser` al inicio; los atajos las usan.
- Modificador principal: `SUPER`. Patrón de atajos: `SUPER + tecla` acción, `SUPER + SHIFT + tecla` variante "mover".
- Reglas de ventana con sintaxis nueva: `windowrule = <efecto>, match:class ^(clase)$`.
- Rutas a scripts absolutas vía `~/dotfiles/...` (no `~/.config/...`).

- Todo atajo nuevo, borrado o modificado se refleja en `utils/atajos.txt` (formato `Sección | Atajo | Descripción [| Comando]`) en el mismo cambio. Aplica también a `map` de Kitty y `on-click` de Waybar; las filas de Waybar repiten su comando en la 4.ª columna para que la lista pueda ejecutarlas.

### Waybar
- `config` en JSONC con comentarios `//`; módulos no usados se dejan comentados en `modules-*`.
- Módulos propios: `custom/<nombre>`; script en `scripts/<nombre>.sh` con `"return-type": "json"`.
- Contrato JSON de scripts: `{"text": "<icono>", "tooltip": "<detalle>", "class": "<estado>"}`. El texto visible es un icono Nerd Font; el detalle va al tooltip.
- `style.css`: colores solo vía las variables de `tema.css` (`@import "tema.css"`); estilos por ID (`#custom-pomo`, `#clock`) y estados por clase (`.work`, `.break`, `.idle`).

### Kitty
- Atajos con `ctrl` (los comentarios dicen "SUPER", pero el código usa `ctrl`; el código es la verdad).
- Mismos verbos que Hyprland pero un modificador "abajo": `ctrl+flecha` foco, `ctrl+shift+flecha` mover, `ctrl+alt+flecha` redimensionar, `ctrl+f` zoom.

### Bash (scripts)
- Todos los scripts empiezan con `#!/usr/bin/env bash` y pueden usar bash-ismos (`$BASHPID`, `(( ))`, `<<<`, `[[ ]]`).
- Para buscar procesos por nombre usar la línea de comandos (`pkill -f '^waybar( |$)'`), no `pkill -x`: en NixOS muchos programas corren como `.<nombre>-wrapped`.
- Los archivos que una app recarga sola al cambiar (Hyprland) se escriben de forma atómica: archivo temporal + `mv`.
- Configuración arriba en MAYÚSCULAS (`WORK_TIME`, `DATA_FILE`, `MORADO`), lógica en `case "$1" in`.
- Estado efímero en `/tmp/<script>_*`.
- Avisos al usuario con `notify-send` y, si es importante, sonido con `paplay`.
- `init.sh` debe ser **idempotente**: comprobar antes de instalar (`flatpak info`, `[ -f ]`, `tailscale status`), usar `mkdir -p`, `ln -sfn`, y respaldar en vez de borrar (`~/.local/state/dotfiles/respaldo/`, `/etc/nixos/*.respaldo-<fecha>`). Todo comando con `sudo` pasa por `como_root`/`escribir_root` para que `--simular` lo muestre sin ejecutarlo.

## Paleta y apariencia

- **Ningún color, radio, fuente ni ruta de fondo se escribe a mano en una config**: se define en el tema y se usa como variable (`$acento` en Hyprland, `@acento` en Waybar/Rofi, `include tema.conf` en Kitty). Si una app necesita un valor nuevo, se añade a **todos** los `tema/temas/*.conf` y a `utils/aplicar-tema.sh` (y a `nixos/modulos/tema.nix` si lo usan GRUB o el login).
- Los archivos `tema.*`, `config/mako/config` y `config/gtk-4.0/gtk.css` son **generados** y no se versionan (`.gitignore`); `init.sh usuario` y `tema-aplicar` los crean.
- Tema por defecto (Nova): acento `#3399cc`, secundario `#cba6f7` (degradado secundario → acento en el borde de ventanas), fondo `#0a1e3c`, superficie `#133e7c`; estados urgente `#f38ba8`, éxito `#a6e3a1`, tenue `#6c7086`.
- Esquinas de 10 px, borde de 2 px, transparencias 0.70 (paneles), 0.85 (terminal) y 0.95 (menús); tema oscuro en todo.

## Secretos

- Todo valor sensible va en `.env` (ignorado en `.gitignore`) con formato `export NOMBRE="valor"`, y se documenta con un placeholder en `.env.example`.
- Consumo: `source ~/dotfiles/.env && … "$NOMBRE"`.
- Nunca versionar contraseñas, tokens ni IDs de dispositivos nuevos (hoy `valent-clipboard.sh` incumple esto con el ID del celular hardcodeado).

## Git y Commits

- Rama única: `main`. No hay ramas de desarrollo ni PRs.
- Conventional Commits en español, en minúscula: `feat:`, `fix:`, `docs:`, `refactor:`. Los commits hechos desde la web de GitHub no siguen la convención (`Update README.md`).
- Un commit agrupa los cambios de una funcionalidad a través de varias capas (Nix + Hyprland + init.sh + atajos).
- Nunca se versiona `hardware-configuration.nix` ni archivos generados o locales.

## Manejo de errores

- `init.sh` y `aplicar-tema.sh` usan `set -euo pipefail`; los pasos opcionales (recargar apps, Tailscale) avisan y siguen (`|| aviso`, `|| true`). El resto de scripts no tiene manejo formal de errores.
- Salida que no interesa se silencia con `> /dev/null 2>&1` (ej. `valent-clipboard.sh`), lo que oculta fallos: al tocar esos scripts, considerar registrar el error con `notify-send` o `logger`.
