# Registro de Decisiones Arquitectónicas (ADRs)

*Decisiones reconstruidas a partir del código actual y del historial de Git (27 commits, 2026-06-22 → 2026-10-04). Las fechas son las del commit que introdujo el cambio. Las decisiones nuevas se añaden al final con el siguiente número.*

## ADR-001: NixOS declarativo para el sistema, symlinks para el usuario
- **Fecha**: 2026-06-22
- **Contexto**: Se necesita reproducir el mismo escritorio en varias PCs sin reconfigurar a mano.
- **Decisión**: Paquetes y servicios en `configuration.nix`; configuración de aplicaciones en `config/` enlazada a `~/.config` mediante `init.sh` (`ln -sfn`). No se usa Home Manager ni GNU Stow.
- **Consecuencias**:
  - Positivas: editar un archivo del repo aplica el cambio al instante (recargar la app); curva de aprendizaje baja.
  - Negativas: la capa de usuario no es declarativa (no hay rollback); `init.sh` hace `rm -rf` de carpetas existentes; rutas como `/home/nova` quedan hardcodeadas.

## ADR-002: Una carpeta de configuración NixOS por equipo
- **Fecha**: 2026-06-22 (`nixos/` → `nixos-laptop-hp/`); `nixos-pc-asus/` el 2026-09-03; `nixos-laptop-hp/` eliminado el 2026-09-26.
- **Contexto**: `hardware-configuration.nix` contiene UUIDs de disco; usarlo en otra máquina deja el sistema sin arrancar.
- **Decisión**: Cada equipo tiene su `nixos-<equipo>/`. En el equipo actual, `/etc/nixos/*.nix` son **symlinks** a `nixos-pc-asus/`. El README recomienda **copiar** (no enlazar) en máquinas nuevas.
- **Consecuencias**:
  - Positivas: el repo versiona la configuración real del sistema.
  - Negativas: el contenido de `configuration.nix` se duplica entre equipos (no hay módulo común); la recomendación del README y la práctica actual no coinciden.

## ADR-003: Hyprland + greetd/tuigreet en lugar de KDE Plasma + SDDM
- **Fecha**: 2026-06-22 (Plasma/SDDM quedan comentados en `configuration.nix`)
- **Contexto**: Se busca un escritorio ligero, por teclado y muy personalizable sobre Wayland.
- **Decisión**: `programs.hyprland.enable`, login en TTY con `tuigreet` que ejecuta `start-hyprland`. Las piezas del escritorio se ensamblan a mano (Waybar, Rofi, Mako, swaybg, swaylock, nm-applet).
- **Consecuencias**:
  - Positivas: control total, consumo bajo, atajos coherentes.
  - Negativas: cada función de escritorio (polkit, temas, portapapeles, notificaciones) hay que configurarla explícitamente; cambios de sintaxis entre versiones de Hyprland (p. ej. `windowrule … match:class`) obligan a migrar.

## ADR-004: Cursor Catppuccin servido desde el perfil del sistema
- **Fecha**: 2026-06-28; ajustes 2026-07-06 y 2026-09-03
- **Contexto**: El cursor aparecía distinto o invisible según la app (GTK, Xwayland, Hyprland).
- **Decisión**: Instalar `catppuccin-cursors.mochaSky` vía Nix y, en paralelo: variables `XCURSOR_*`/`HYPRCURSOR_*` en Nix y Hyprland, symlinks a `/run/current-system/sw/share/icons` en `~/.icons` y `~/.local/share/icons`, `index.theme` heredando el tema, `dconf`/`hyprctl setcursor` al iniciar y `no_hardware_cursors = true` + `inactive_timeout = 0`.
- **Consecuencias**:
  - Positivas: cursor consistente.
  - Negativas: la misma configuración está en 5–6 sitios; difícil saber cuál es la que realmente funciona.

## ADR-005: Tema oscuro unificado Adwaita-dark + paleta azul/Catppuccin
- **Fecha**: 2026-07-06
- **Decisión**: GTK 2/3/4 con `Adwaita-dark` (generados con `nwg-look`), `color-scheme prefer-dark` vía dconf al inicio, Waybar/Rofi/Kitty con acento `#3399cc` y bordes Catppuccin.
- **Consecuencias**: apariencia coherente; las apps Qt no están tematizadas (el bloque `qt` está comentado) y el tema de iconos `breeze-dark` referenciado en GTK no está instalado.

## ADR-006: Aplicaciones fuera de nixpkgs vía Flatpak y AppImage
- **Fecha**: 2026-07-27; Thorium reactivado 2026-09-30
- **Contexto**: Zen Browser y Thorium no están (o no actualizados) en nixpkgs.
- **Decisión**: `services.flatpak.enable` + Flathub para Zen (`$browser = app.zen_browser.zen`); Thorium como AppImage descargado por `init.sh` a `~/.local/bin/appimages/` y ejecutado con `appimage-run`.
- **Consecuencias**: navegadores actuales sin empaquetar; versiones fuera del control de Nix (Thorium fijado a `M128.0.6613.189` AVX2, sin actualización automática).

## ADR-007: Valent en lugar de KDE Connect
- **Fecha**: 2026-07-28 / 2026-07-29
- **Contexto**: Integración celular ↔ PC (notificaciones, portapapeles, comandos remotos) sin depender de KDE.
- **Decisión**: Paquete `valent` arrancado como servicio GApplication; `programs.kdeconnect` comentado; firewall abierto 1714–1764 TCP/UDP; portales XDG Hyprland + GTK. El portapapeles se envía al celular con `wl-paste --watch` → `utils/valent-clipboard.sh` → `gdbus`.
- **Consecuencias**: integración GTK nativa; el ID del dispositivo está hardcodeado; todo lo copiado (incluidas contraseñas) se envía al celular.

## ADR-008: Thunar como gestor de archivos (en lugar de Dolphin)
- **Fecha**: 2026-07-29
- **Decisión**: `programs.thunar` con plugins de archivo y volúmenes, `tumbler` para miniaturas, `gvfs` para montajes; Dolphin y breeze comentados.
- **Consecuencias**: menos dependencias Qt/KDE y mejor encaje con el tema GTK.

## ADR-009: Secretos en `.env` local no versionado
- **Fecha**: 2026-07-29
- **Contexto**: Desbloquear la pantalla remotamente desde Valent requiere la contraseña.
- **Decisión**: `.env` en la raíz (en `.gitignore`, `chmod 600` desde `init.sh`), plantilla en `.env.example`. Comando remoto: `source ~/dotfiles/.env && wtype "$PASS_SWAYLOCK" && wtype -k Return`.
- **Consecuencias**: el secreto no llega a Git, pero se guarda en texto plano y cualquier celular emparejado puede desbloquear la sesión.

## ADR-010: Acceso remoto con Tailscale + WayVNC
- **Fecha**: 2026-07-28 (Tailscale); 2026-10-04 (WayVNC al arranque)
- **Decisión**: `services.tailscale.enable` y `sudo tailscale up` al final de `init.sh`; WayVNC escuchando en `0.0.0.0` con el puerto 5900 abierto en el firewall; alias `remote-conexion`.
- **Consecuencias**: control remoto desde LAN o la tailnet; WayVNC no tiene autenticación configurada y escucha en todas las interfaces (ver `06-errores-conocidos.md`).

## ADR-011: Lógica de escritorio en scripts Bash conectados a Waybar/Rofi
- **Fecha**: 2026-06-24 (powermenu), Pomodoro desde el primer commit
- **Decisión**: Funciones como Pomodoro (25/5/15 min, 4 rondas) y menú de apagado (Rofi dmenu) se escriben como scripts Bash con estado en `/tmp`, en lugar de usar programas externos.
- **Consecuencias**: cero dependencias extra y fácil de modificar; sin tests y sin manejo de errores.

## ADR-012: Mantenimiento automático del store de Nix
- **Fecha**: 2026-07-06
- **Decisión**: `nix.gc` semanal (`--delete-older-than 7d`) y `auto-optimise-store`; alias `nix-clean` para limpieza manual.
- **Consecuencias**: disco controlado; rutas hardcodeadas a `/nix/store/...` (como el tema de Rofi) pueden desaparecer tras una actualización + GC.

## ADR-013: Zoom de Kitty con CTRL + rueda vía Hyprland y control remoto
- **Fecha**: 2026-10-04
- **Contexto**: Se quiere cambiar el tamaño de fuente de Kitty con `CTRL + rueda del ratón`. Kitty no permite asignar la rueda en `mouse_map` (solo botones).
- **Decisión**: Hyprland captura `CTRL + mouse_up/mouse_down` con `bindn` (no consume el evento) y ejecuta `utils/kitty-zoom.sh`, que toma el PID de la ventana enfocada y, si existe el socket `$XDG_RUNTIME_DIR/kitty-<pid>`, llama a `kitty @ set-font-size`. Kitty tiene `allow_remote_control socket-only` y `listen_on unix:${XDG_RUNTIME_DIR}/kitty`.
- **Consecuencias**:
  - Positivas: en otras apps `CTRL + rueda` sigue funcionando igual; el socket solo es accesible por el usuario y no se acepta control por secuencias de escape.
  - Negativas: cualquier proceso del usuario puede controlar Kitty por el socket; como el evento no se consume, Kitty también recibe la rueda (puede desplazar el historial o llegar a programas con ratón como `nvim`); las ventanas de Kitty abiertas antes del cambio no tienen socket hasta reiniciarlas.
