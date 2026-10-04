# Convenciones del Proyecto

*Reglas extraídas de cómo está escrito el repositorio hoy. Si una convención se rompe en algún archivo, se indica.*

## Idioma

- Comentarios, mensajes de commit, README y notificaciones al usuario: **español**.
- Identificadores técnicos (nombres de módulos Waybar, clases CSS, opciones Nix): en inglés, tal como los exige cada herramienta.
- Variables de color propias en español: `texto_principal`, `fondo_modulos`, `fondo_hover`, `MORADO`, `FONDO_SELECT`.

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
- `style.css`: colores solo vía `@define-color`; estilos por ID (`#custom-pomo`, `#clock`) y estados por clase (`.work`, `.break`, `.idle`).

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

- Color de texto/acento: `#3399cc`; fondo de módulos `rgba(19, 62, 124, 0.7)`.
- Bordes Catppuccin Mocha: activo `#cba6f7 → #89b4fa` (Hyprland), `#cba6f7` (Kitty); inactivo `#595959`.
- Estados: urgente `#f38ba8`, break `#a6e3a1`, idle `#6c7086`.
- Esquinas redondeadas 8–10 px, transparencias 0.7–0.9, tema oscuro en todo.

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
