# Errores Conocidos y Soluciones (Troubleshooting)

*Resultado de la auditoría del 2026-10-04 contra el sistema en ejecución (NixOS 26.05, Hyprland 0.55.2). Ordenado por impacto. Al resolver uno, moverlo a "Resueltos" con la fecha.*

## Bugs activos

- **Error**: No hay agente polkit gráfico; las apps que piden contraseña de administrador (Thunar al montar, virt-manager, etc.) fallan o no muestran diálogo.
  - **Causa**: `exec-once = ${pkgs.polkit_gnome}/libexec/…` usa interpolación de Nix dentro de `hyprland.conf`, que es un archivo plano y no pasa por Nix. Además `polkit_gnome` no está en `systemPackages`.
  - **Solución**: añadir `polkit_gnome` a `environment.systemPackages` y usar `exec-once = /run/current-system/sw/libexec/polkit-gnome-authentication-agent-1`, o declarar un servicio de usuario en `configuration.nix` (`systemd.user.services.polkit-gnome-authentication-agent-1`).
## Riesgos de seguridad

- **WayVNC sin contraseña dentro de la tailnet**: cualquier dispositivo de la cuenta de Tailscale puede ver y controlar el escritorio (decisión del usuario, ver ADR-010). Si se comparte la tailnet, configurar `enable_auth` en `~/.config/wayvnc/config`.
- **Contraseña de sesión en texto plano** (`.env` → `PASS_SWAYLOCK`): cualquier celular emparejado con Valent puede desbloquear la PC. Mitigación: limitar el desbloqueo remoto a dispositivos de confianza o retirar ese comando.
- **Todo el portapapeles se envía al celular** (`valent-clipboard.sh` vía `wl-paste --watch`), incluidas contraseñas copiadas desde Bitwarden. Mitigación: filtrar por tipo MIME/origen o activar el envío solo manualmente.
- `utils/reset-trial-navicat.sh` es un script de terceros que reinicia el periodo de prueba de Navicat: puede incumplir la licencia y modifica `dconf` y `preferences.json` (hace backup antes).

## Fragilidades (funcionan hoy, pero se pueden romper)

- **ID de dispositivo Valent hardcodeado** en `valent-clipboard.sh` (`9f91b45437b94e139957b9d336079ea0`): si se vuelve a emparejar el celular o se cambia de teléfono, el puente deja de funcionar en silencio (la salida va a `/dev/null`). Mover el ID a `.env`.
- **Escapado incompleto en `valent-clipboard.sh`**: solo escapa `"`; textos con `\` o saltos de línea pueden romper el GVariant que recibe `gdbus`.
- **Ruta hardcodeada a `/home/nova`** en `config/gtkrc-2.0` (la escribe nwg-look): falla con otro usuario.
- **Thorium fijado a la versión M128 AVX2** en `init.sh`: sin actualizaciones; falla en CPUs sin AVX2. Para actualizarlo, cambiar la URL y borrar `~/.local/bin/appimages/Thorium.AppImage`.
- **`hardware-configuration.nix` sin respaldo en git**: si se pierde, `init.sh sistema` lo regenera con `nixos-generate-config`, que puede omitir módulos como `uas`/`sd_mod` (irrelevante si el disco raíz es interno) y copia todo lo montado en ese momento (`init.sh` filtra Docker, overlay, fuse, `/run` y `/tmp`; revisar si hay otros montajes temporales).
- **Entrada antigua de systemd-boot en el firmware** (`Linux Boot Manager`, `\EFI\systemd\systemd-bootx64.efi`): queda como respaldo detrás de GRUB en el orden de arranque; sus entradas apuntan a generaciones viejas.
- **`hypridle` avisa "No rules configured"** al iniciar: no hay temporizadores de inactividad (solo bloquea al suspender). Es inofensivo.
- **Rutas absolutas a `/home/nova/dotfiles`** en el `configuration.nix` que genera `init.sh`, en los alias y en Hyprland: el repo debe clonarse ahí.
- **Comentarios de Kitty dicen "SUPER"** pero los atajos usan `ctrl`.
- **La clase `long` del Pomodoro no tiene estilo** en `style.css` (solo `work`, `break`, `idle`).
- **Waybar solo muestra los workspaces 1–10** (`espacios.sh`, ADR-027): un workspace 11 o con nombre existe en Hyprland pero no tiene número en la barra. Si los números dejan de actualizarse, comprobar que corre `espacios.sh escuchar` (Waybar lo reinicia a los 5 s si se cae).
- **Configuraciones no versionadas** (WayVNC, Valent): se pierden al reinstalar.
- **Archivos del tema desfasados**: si se edita un tema sin ejecutar `tema-aplicar`, los `tema.*` siguen con los valores anteriores (GRUB y el login sí se actualizan con `nix-switch`, porque Nix lee el tema directamente). El selector (`SUPER + F2`) aplica solo al cerrar el editor.
- **Bloques comentados abundantes** en los módulos de `nixos/` y `config.rasi` (~160 líneas de opciones por defecto comentadas): dificultan leer qué está activo. Candidatos a eliminar según el paso 2 de la filosofía (Eliminar).

## Resueltos

- **2026-10-05** — Los módulos declaraban el usuario `nova` fijo: en la PC de admisión (usuario `admision`) NixOS habría creado `nova` y borrado `admision`. Ahora cada equipo elige su usuario con `dotfiles.usuario` (ADR-025). `thorium.desktop` usa `$HOME` en lugar de `/home/nova`.
- **2026-10-05** — Alias `k` fallaba con "command not found": `desarrollo.nix` instala `kubectl`, `kind` y `skaffold`.
- **2026-10-04** — WayVNC no arrancaba al iniciar sesión (`exec-once = exec-once = wayvnc 0.0.0.0` en `hyprland.conf`) y, lanzado a mano, quedaba expuesto sin contraseña en toda la red local. Ahora `utils/wayvnc-tailscale.sh` espera la IP de Tailscale y escucha solo en ella, y el firewall abre el 5900 solo en `tailscale0`.
- **2026-10-04** — Las carpetas siempre eran azules: el tema genera `dotfiles-iconos` (Papirus con las carpetas de `COLOR_CARPETAS`, ver ADR-024).

- **2026-10-04** — Thunar no cambiaba de color con el tema (`Adwaita-dark` tiene los colores compilados): ahora el tema GTK es `dotfiles-tema` (adw-gtk3 con la paleta del tema, ver ADR-023). Quitada también la segunda línea de `nm-applet` con `GTK_THEME` fijo.

- **2026-10-04** — El login tardaba ~15 s en aparecer después de GRUB: greetd es `Type=idle` en NixOS y esperaba a `NetworkManager-wait-online` (~6 s), y el montaje del NVMe raíz esperaba el sondeo uno a uno de los 6 puertos SATA vacíos (~2,8 s, bandera de arranque escalonado). Ahora greetd es `Type=simple` (`tema.nix`) y pc-asus arranca con `libahci.ignore_sss=1`.
- **2026-10-04** — La generación 7 entraba en modo de emergencia al arrancar: `init.sh sistema` regeneró `hardware-configuration.nix` con contenedores de Docker corriendo y `nixos-generate-config` copió sus montajes `overlay` (`/var/lib/docker/rootfs/overlayfs/…`), que fallan al arrancar. `init.sh` ahora quita los montajes temporales (Docker, overlay, fuse, `/run`, `/tmp`) al regenerar o al encontrarlos en el archivo existente, y antes de activar revisa el `fstab` construido.
- **2026-10-04** — Suspender no bloqueaba si `hypridle` no corría (la sesión empezó antes de instalarlo): Hyprland lo arranca con `exec` en cada recarga si falta, el menú de apagado bloquea con hyprlock en ese caso, y `inhibit_sleep = 3` retiene la suspensión hasta que la pantalla está bloqueada.
- **2026-10-04** — `nix-clean` no borraba generaciones del sistema: `sudo nix-env --delete-generations old` sin `-p` actúa sobre el perfil de root, así que el menú de GRUB acumulaba todas las generaciones. Ahora usa `sudo nix-collect-garbage -d`.
- **2026-10-04** — Tras `nix-switch`, cerrar sesión mostraba el login anterior: NixOS no reinicia greetd en un switch. No es un fallo, pero `init.sh` ahora avisa que hay que reiniciar cuando cambia la pantalla de inicio de sesión.
- **2026-10-04** — Otras PCs se bloqueaban al arrancar con esta configuración: `/etc/nixos` enlazaba el `hardware-configuration.nix` de la ASUS (UUID de discos ajenos). El hardware ya no está en el repo; cada máquina conserva el suyo y `init.sh` escribe un `configuration.nix` que lo importa junto al equipo.
- **2026-10-04** — Cada cambio de tema lanzaba un `swaybg` nuevo sin cerrar el anterior (llegó a haber 11) y Waybar no recargaba el CSS: `pkill -x swaybg`/`waybar` nunca coincidía porque en NixOS los procesos se llaman `.swaybg-wrapped`/`.waybar-wrapped`. Ahora se buscan por línea de comandos (`pkill -f '^swaybg( |$)'`).
- **2026-10-04** — Hyprland mostraba errores al cambiar de tema porque leía `config/hypr/tema.conf` a medio escribir: `aplicar-tema.sh` escribe en un temporal y lo mueve.
- **2026-10-04** — `init.sh` reescrito (ADR-021): ya no hace `rm -rf` sin respaldo, no anida enlaces (`~/.config/fastfetch/fastfetch`, `~/.local/share/icons/icons`, que además elimina), no escribe `XCURSOR_PATH` con `~` literal en `~/.bash_profile` (lo limpia; NixOS ya define las variables del cursor), se detiene ante errores, no vuelve a descargar Thorium y gestiona `/etc/nixos`.
- **2026-10-04** — El README no coincidía con la realidad (copiar `configuration.nix`, URL de ejemplo): ahora describe `init.sh` y la URL real.
- **2026-10-04** — Scripts sin shebang (`pomo.sh`, `valent-clipboard.sh`, `reset-trial-navicat.sh`): todos empiezan con `#!/usr/bin/env bash`.
- **2026-10-04** — Alias `*-config` con `sudo micro` sobre archivos del repo (dejaban archivos de root): usan `micro` sin `sudo`.
- **2026-10-04** — Fondos con paréntesis en el nombre (`guts(1).jpg`, `demon-slayer(1).jpeg`): renombrados para poder usarlos en los temas.
- **2026-10-04** — Los archivos generados por el tema ensuciaban `git status` en cada cambio y chocaban entre máquinas: salen de git (ADR-020).
- **2026-10-04** — La fuente de Kitty no era la configurada (`FiraCode Nerd Font` no estaba instalada): Kitty toma la fuente del tema (`JetBrainsMono Nerd Font`) desde `config/kitty/tema.conf`.
- **2026-10-04** — El tema de Rofi apuntaba a una ruta con hash de `/nix/store` que desaparecía tras actualizar + GC: ahora usa el tema local `config/rofi/themes/nova.rasi` y `@theme "/dev/null"` para descartar el de por defecto.
- **2026-10-04** — Iconos genéricos en apps GTK (`breeze-dark` no instalado y `icon-theme 'Adwaita-dark'` en Hyprland): GTK, dconf, Rofi y Mako usan `ICONOS` del tema (`Papirus-Dark`).
- **2026-10-04** — Mako no estaba versionado: `config/mako/config` se genera desde el tema e `init.sh` lo enlaza.
- **2026-10-04** — Suspender solo bloqueaba desde el menú de apagado (`swaylock -f && sleep 1`): ahora `hypridle` abre `hyprlock` antes de cualquier suspensión.

- **2026-09-03** — Cursor invisible en inactividad: `cursor { inactive_timeout = 0; no_hardware_cursors = true }` + `WLR_NO_HARDWARE_CURSORS=1` en `hyprland.conf`.
- **2026-09-26** — Capturas de pantalla se guardaban sueltas en `~/Imágenes`: ahora van a `~/Imágenes/CapturasPantalla/`, carpeta que crea `init.sh`.
- **2026-08-04** — Rofi no tomaba la configuración del repo: se versionó `config/rofi/` y se añadió el enlace `~/.config/rofi` en `init.sh`.
