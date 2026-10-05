# Convenciones del Proyecto

*Reglas extraídas de cómo está escrito el repositorio hoy. Si una convención se rompe en algún archivo, se indica.*

## Idioma

- Comentarios, mensajes de commit, README y notificaciones al usuario: **español**.
- Identificadores técnicos (nombres de módulos Waybar, clases CSS, opciones Nix): en inglés, tal como los exige cada herramienta.
- Variables del tema en español: `ACENTO`, `FONDO`, `SUPERFICIE` en `tema/tema.conf`; `$acento`, `@acento`, `@fondo`, `@superficie` en los archivos generados.

## Estructura y nomenclatura de archivos

- `config/<app>/` replica exactamente la estructura de `~/.config/<app>/` para poder enlazar la carpeta completa.
- Configuración de sistema por equipo: `nixos-<tipo>-<marca>/` (ej. `nixos-pc-asus`, antes `nixos-laptop-hp`).
- Scripts: `kebab-case.sh` (`valent-clipboard.sh`, `reset-trial-navicat.sh`) o nombre corto (`pomo.sh`, `powermenu.sh`).
- Scripts ligados a Waybar viven en `config/waybar/scripts/`; scripts generales en `utils/`.
- Recursos estáticos en `public/` (`background/` para fondos, `png/` para logos). Algunos nombres tienen espacios/paréntesis (`guts(1).jpg`, `demon-slayer(1).jpeg`): evitarlo en archivos nuevos.

## Estilo por lenguaje

### Nix (`configuration.nix`)
- Secciones delimitadas con banners de comentarios:
  ```nix
  # --------------------------------------------------
  # ---               Conectividad                 ---
  # --------------------------------------------------
  ```
- Cada paquete en `environment.systemPackages` lleva un comentario en línea explicando para qué está.
- Lo desactivado se **comenta, no se borra** (KDE Plasma, SDDM, Steam, Dolphin, breeze). Esto sirve de historial, pero añade ruido.
- Indentación: 2 espacios (hay tabs mezclados en la lista de paquetes y aliases; normalizar a espacios al editar).
- Aliases de sistema van en `environment.shellAliases`, agrupados por tema.

### Hyprland (`hyprland.conf`)
- Encabezados `# --- TÍTULO ---` en mayúsculas y bloques `# ====` para secciones grandes.
- Variables `$mainMod`, `$terminal`, `$fileManager`, `$menu`, `$browser` al inicio; los atajos las usan.
- Modificador principal: `SUPER`. Patrón de atajos: `SUPER + tecla` acción, `SUPER + SHIFT + tecla` variante "mover".
- Reglas de ventana con sintaxis nueva: `windowrule = <efecto>, match:class ^(clase)$`.
- Rutas a scripts absolutas vía `~/dotfiles/...` (no `~/.config/...`).

- Todo atajo nuevo, borrado o modificado se refleja en `utils/atajos.txt` (formato `Sección | Atajo | Descripción`) en el mismo cambio. Aplica también a `map` de Kitty y `on-click` de Waybar.

### Waybar
- `config` en JSONC con comentarios `//`; módulos no usados se dejan comentados en `modules-*`.
- Módulos propios: `custom/<nombre>`; script en `scripts/<nombre>.sh` con `"return-type": "json"`.
- Contrato JSON de scripts: `{"text": "<icono>", "tooltip": "<detalle>", "class": "<estado>"}`. El texto visible es un icono Nerd Font; el detalle va al tooltip.
- `style.css`: colores solo vía las variables de `tema.css` (`@import "tema.css"`); estilos por ID (`#custom-pomo`, `#clock`) y estados por clase (`.work`, `.break`, `.idle`).

### Kitty
- Atajos con `ctrl` (los comentarios dicen "SUPER", pero el código usa `ctrl`; el código es la verdad).
- Mismos verbos que Hyprland pero un modificador "abajo": `ctrl+flecha` foco, `ctrl+shift+flecha` mover, `ctrl+alt+flecha` redimensionar, `ctrl+f` zoom.

### Bash (scripts)
- Los scripts **no tienen shebang** y usan bash-ismos (`$BASHPID`, `(( ))`, `<<<`, `[[ ]]`). Funcionan porque en NixOS `/bin/sh` es bash. **Para scripts nuevos: añadir `#!/usr/bin/env bash`.**
- Configuración arriba en MAYÚSCULAS (`WORK_TIME`, `DATA_FILE`, `MORADO`), lógica en `case "$1" in`.
- Estado efímero en `/tmp/<script>_*`.
- Avisos al usuario con `notify-send` y, si es importante, sonido con `paplay`.
- `init.sh` debe ser **idempotente**: usar `mkdir -p`, `ln -sfn`, `--if-not-exists`, y guardas `if ! grep -q …` antes de añadir líneas a archivos.

## Paleta y apariencia

- **Ningún color, radio, fuente ni ruta de fondo se escribe a mano en una config**: se define en `tema/tema.conf` y se usa como variable (`$acento` en Hyprland, `@acento` en Waybar/Rofi, `include tema.conf` en Kitty). Si una app necesita un valor nuevo, se añade a `tema.conf` y a `utils/aplicar-tema.sh` (y a `tema/tema.nix` si lo usan GRUB o el login).
- Los archivos `tema.*`, `config/mako/config` y `config/swaylock/config` son **generados**: se versionan, pero no se editan a mano.
- Valores actuales: acento `#3399cc`, secundario `#cba6f7` (degradado secundario → acento en el borde de ventanas), fondo `#0a1e3c`, superficie `#133e7c`; estados urgente `#f38ba8`, éxito `#a6e3a1`, tenue `#6c7086`.
- Esquinas de 10 px, borde de 2 px, transparencias 0.70 (paneles), 0.85 (terminal) y 0.95 (menús); tema oscuro en todo.

## Secretos

- Todo valor sensible va en `.env` (ignorado en `.gitignore`) con formato `export NOMBRE="valor"`, y se documenta con un placeholder en `.env.example`.
- Consumo: `source ~/dotfiles/.env && … "$NOMBRE"`.
- Nunca versionar contraseñas, tokens ni IDs de dispositivos nuevos (hoy `valent-clipboard.sh` incumple esto con el ID del celular hardcodeado).

## Git y Commits

- Rama única: `main`. No hay ramas de desarrollo ni PRs.
- Conventional Commits en español, en minúscula: `feat:`, `fix:`, `docs:`. Los commits hechos desde la web de GitHub no siguen la convención (`Update README.md`).
- Un commit suele agrupar los cambios de una funcionalidad a través de varias capas (Nix + Hyprland + init.sh).

## Manejo de errores

- No hay manejo de errores formal: los scripts no usan `set -e`/`set -u`. `init.sh` continúa aunque falle un paso.
- Salida que no interesa se silencia con `> /dev/null 2>&1` (ej. `valent-clipboard.sh`), lo que oculta fallos: al tocar esos scripts, considerar registrar el error con `notify-send` o `logger`.
