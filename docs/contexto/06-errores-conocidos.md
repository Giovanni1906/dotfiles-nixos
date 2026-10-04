# Errores Conocidos y Soluciones (Troubleshooting)

*Resultado de la auditoría del 2026-10-04 contra el sistema en ejecución (NixOS 26.05, Hyprland 0.55.2). Ordenado por impacto. Al resolver uno, moverlo a "Resueltos" con la fecha.*

## Bugs activos

- **Error**: WayVNC no arranca al iniciar sesión (no hay proceso `wayvnc`).
  - **Causa**: `config/hypr/hyprland.conf` tiene la directiva duplicada: `exec-once = exec-once = wayvnc 0.0.0.0`. Hyprland intenta ejecutar el comando literal `exec-once = wayvnc …`.
  - **Solución definitiva**: dejar `exec-once = wayvnc 0.0.0.0` (y revisar antes el problema de seguridad de WayVNC, más abajo).

- **Error**: No hay agente polkit gráfico; las apps que piden contraseña de administrador (Thunar al montar, virt-manager, etc.) fallan o no muestran diálogo.
  - **Causa**: `exec-once = ${pkgs.polkit_gnome}/libexec/…` usa interpolación de Nix dentro de `hyprland.conf`, que es un archivo plano y no pasa por Nix. Además `polkit_gnome` no está en `systemPackages`.
  - **Solución**: añadir `polkit_gnome` a `environment.systemPackages` y usar `exec-once = /run/current-system/sw/libexec/polkit-gnome-authentication-agent-1`, o declarar un servicio de usuario en `configuration.nix` (`systemd.user.services.polkit-gnome-authentication-agent-1`).

- **Error**: `nm-applet` se lanza dos veces (líneas 39 y 41 de `hyprland.conf`).
  - **Causa**: quedó la línea original y la variante con `GTK_THEME="Adwaita-dark"`.
  - **Solución**: borrar `exec-once = nm-applet --indicator` y conservar solo la versión con `GTK_THEME`.

- **Error**: La fuente de Kitty no es la configurada.
  - **Causa**: `kitty.conf` pide `FiraCode Nerd Font`, pero solo está instalada `nerd-fonts.jetbrains-mono` (`fc-list | grep -i firacode` devuelve 0).
  - **Solución**: cambiar a `font_family JetBrainsMono Nerd Font` o añadir `nerd-fonts.fira-code` a `fonts.packages`.

- **Error**: El tema de Rofi desaparece tras actualizar Rofi + GC.
  - **Causa**: `config/rofi/config.rasi` apunta a una ruta con hash `/nix/store/f6jj0h6…-rofi-2.0.0/share/rofi/themes/material.rasi`. Ya ocurrió una vez (hay otra ruta de store comentada).
  - **Solución definitiva**: usar la copia local que ya existe: `@theme "themes/material.rasi"`.

- **Error**: Iconos genéricos o faltantes en apps GTK.
  - **Causa**: GTK (`gtk-3.0`, `gtk-4.0`, `gtkrc-2.0`) usa `breeze-dark`, pero `kdePackages.breeze-icons` está comentado; Hyprland además fija `icon-theme 'Adwaita-dark'`, que no es un tema de iconos. Lo instalado es `papirus-icon-theme` y `adwaita-icon-theme`.
  - **Solución**: unificar en un solo tema instalado (p. ej. `Papirus-Dark`) en los tres archivos GTK y en el `dconf write … icon-theme`.

- **Error**: `XCURSOR_PATH` en `~/.bash_profile` no incluye realmente `~/.icons` ni `~/.local/share/icons`.
  - **Causa**: `init.sh` escribe `export XCURSOR_PATH="…:~/.icons:~/.local/share/icons"`; dentro de comillas dobles `~` no se expande.
  - **Solución**: usar `$HOME/.icons:$HOME/.local/share/icons` en `init.sh` y corregir la línea ya escrita en `~/.bash_profile`.

- **Error**: Alias `k` falla con "command not found".
  - **Causa**: `kubectl` no está en `systemPackages`.
  - **Solución**: instalar `kubectl` o eliminar el alias.

## Riesgos de seguridad

- **WayVNC expuesto sin autenticación**: escucha en `0.0.0.0` con el puerto 5900 abierto en el firewall y sin `~/.config/wayvnc/config`. Cualquiera en la misma red puede ver y controlar el escritorio.
  - **Solución**: escuchar solo en la interfaz de Tailscale (`wayvnc 100.x.y.z`, o `networking.firewall.interfaces.tailscale0.allowedTCPPorts = [ 5900 ]` en lugar del puerto global) y/o configurar `enable_auth`, usuario/contraseña y TLS en la configuración de WayVNC.
- **Contraseña de sesión en texto plano** (`.env` → `PASS_SWAYLOCK`): cualquier celular emparejado con Valent puede desbloquear la PC. Mitigación: limitar el desbloqueo remoto a dispositivos de confianza o retirar ese comando.
- **Todo el portapapeles se envía al celular** (`valent-clipboard.sh` vía `wl-paste --watch`), incluidas contraseñas copiadas desde Bitwarden. Mitigación: filtrar por tipo MIME/origen o activar el envío solo manualmente.
- **Alias `*-config` con `sudo micro`** sobre archivos del usuario: pueden quedar archivos o backups de micro con dueño root dentro del repo. Usar `micro` sin `sudo`.
- `utils/reset-trial-navicat.sh` es un script de terceros que reinicia el periodo de prueba de Navicat: puede incumplir la licencia y modifica `dconf` y `preferences.json` (hace backup antes).

## Fragilidades (funcionan hoy, pero se pueden romper)

- **Scripts sin shebang** (`init.sh`, `pomo.sh`, `powermenu.sh`, `valent-clipboard.sh`, `reset-trial-navicat.sh`) que usan bash-ismos: funcionan porque `/bin/sh` es bash en NixOS. Añadir `#!/usr/bin/env bash`.
- **ID de dispositivo Valent hardcodeado** en `valent-clipboard.sh` (`9f91b45437b94e139957b9d336079ea0`): si se vuelve a emparejar el celular o se cambia de teléfono, el puente deja de funcionar en silencio (la salida va a `/dev/null`). Mover el ID a `.env`.
- **Escapado incompleto en `valent-clipboard.sh`**: solo escapa `"`; textos con `\` o saltos de línea pueden romper el GVariant que recibe `gdbus`.
- **Rutas hardcodeadas a `/home/nova`** en `applications/thorium.desktop` y `config/gtkrc-2.0`: fallan con otro usuario.
- **Thorium fijado a la versión M128 AVX2** en `init.sh`: sin actualizaciones; falla en CPUs sin AVX2. Además `init.sh` lo vuelve a descargar en cada ejecución.
- **`init.sh` no es totalmente idempotente ni seguro**:
  - Hace `rm -rf` de `~/.config/{hypr,waybar,kitty,rofi}` y GTK sin respaldo.
  - No borra `~/.config/fastfetch` antes de enlazar: si existe como carpeta, el enlace queda anidado (`~/.config/fastfetch/fastfetch`).
  - `ln -sfn ~/dotfiles/icons ~/.local/share/icons` crea `~/.local/share/icons/icons` (porque la carpeta ya existe por el `mkdir -p` previo). Funciona por casualidad para el cursor, pero no es lo que el comentario describe.
  - No tiene `set -e`: si falla un paso sigue adelante y al final imprime "✅ instalados correctamente".
- **Desajuste entre README y realidad**:
  - El README recomienda **copiar** `configuration.nix` a `/etc/nixos`; en este equipo son **symlinks** al repo.
  - El README usa la URL placeholder `tu_usuario/tu_repositorio` y `ruta_de_tu_carpeta`; la real es `Giovanni1906/dotfiles-nixos` y `nixos-pc-asus`.
  - El README lista `kdePackages.breeze` y `breeze-icons` como requeridos, pero están comentados en `configuration.nix`.
- **Comentarios de Kitty dicen "SUPER"** pero los atajos usan `ctrl`.
- **La clase `long` del Pomodoro no tiene estilo** en `style.css` (solo `work`, `break`, `idle`).
- **Configuraciones no versionadas** (Mako, swaylock, WayVNC, Valent): se pierden al reinstalar.
- **Bloques comentados abundantes** en `configuration.nix` y `config.rasi` (~160 líneas de opciones por defecto comentadas): dificultan leer qué está activo. Candidatos a eliminar según el paso 2 de la filosofía (Eliminar).

## Resueltos

- **2026-09-03** — Cursor invisible en inactividad: `cursor { inactive_timeout = 0; no_hardware_cursors = true }` + `WLR_NO_HARDWARE_CURSORS=1` en `hyprland.conf`.
- **2026-09-26** — Capturas de pantalla se guardaban sueltas en `~/Imágenes`: ahora van a `~/Imágenes/CapturasPantalla/`, carpeta que crea `init.sh`.
- **2026-08-04** — Rofi no tomaba la configuración del repo: se versionó `config/rofi/` y se añadió el enlace `~/.config/rofi` en `init.sh`.
