# Registro de Decisiones Arquitectónicas (ADRs)

*Decisiones reconstruidas a partir del código actual y del historial de Git (27 commits, 2026-06-22 → 2026-10-04). Las fechas son las del commit que introdujo el cambio. Las decisiones nuevas se añaden al final con el siguiente número.*

## ADR-001: NixOS declarativo para el sistema, symlinks para el usuario
- **Fecha**: 2026-06-22
- **Contexto**: Se necesita reproducir el mismo escritorio en varias PCs sin reconfigurar a mano.
- **Decisión**: Paquetes y servicios en `configuration.nix`; configuración de aplicaciones en `config/` enlazada a `~/.config` mediante `init.sh` (`ln -sfn`). No se usa Home Manager ni GNU Stow.
- **Consecuencias**:
  - Positivas: editar un archivo del repo aplica el cambio al instante (recargar la app); curva de aprendizaje baja.
  - Negativas: la capa de usuario no es declarativa (no hay rollback); `init.sh` hace `rm -rf` de carpetas existentes; rutas como `/home/nova` quedan hardcodeadas.

## ADR-002: Una carpeta de configuración NixOS por equipo (reemplazada por ADR-019)
- **Fecha**: 2026-06-22 (`nixos/` → `nixos-laptop-hp/`); `nixos-pc-asus/` el 2026-09-03; `nixos-laptop-hp/` eliminado el 2026-09-26.
- **Contexto**: `hardware-configuration.nix` contiene UUIDs de disco; usarlo en otra máquina deja el sistema sin arrancar.
- **Decisión**: Cada equipo tiene su `nixos-<equipo>/`. En el equipo actual, `/etc/nixos/*.nix` son **symlinks** a `nixos-pc-asus/`. El README recomienda **copiar** (no enlazar) en máquinas nuevas.
- **Consecuencias**:
  - Positivas: el repo versiona la configuración real del sistema.
  - Negativas: el contenido de `configuration.nix` se duplica entre equipos (no hay módulo común); la recomendación del README y la práctica actual no coinciden.

## ADR-003: Hyprland + greetd/tuigreet en lugar de KDE Plasma + SDDM (tuigreet reemplazado en ADR-017)
- **Fecha**: 2026-06-22 (Plasma/SDDM quedan comentados en `configuration.nix`)
- **Contexto**: Se busca un escritorio ligero, por teclado y muy personalizable sobre Wayland.
- **Decisión**: `programs.hyprland.enable`, login en TTY con `tuigreet` que ejecuta `start-hyprland`. Las piezas del escritorio se ensamblan a mano (Waybar, Rofi, Mako, swaybg, swaylock, nm-applet).
- **Consecuencias**:
  - Positivas: control total, consumo bajo, atajos coherentes.
  - Negativas: cada función de escritorio (polkit, temas, portapapeles, notificaciones) hay que configurarla explícitamente; cambios de sintaxis entre versiones de Hyprland (p. ej. `windowrule … match:class`) obligan a migrar.

## ADR-004: Cursor Catppuccin servido desde el perfil del sistema (un color por tema en ADR-026)
- **Fecha**: 2026-06-28; ajustes 2026-07-06 y 2026-09-03
- **Contexto**: El cursor aparecía distinto o invisible según la app (GTK, Xwayland, Hyprland).
- **Decisión**: Instalar `catppuccin-cursors.mochaSky` vía Nix y, en paralelo: variables `XCURSOR_*`/`HYPRCURSOR_*` en Nix y Hyprland, symlinks a `/run/current-system/sw/share/icons` en `~/.icons` y `~/.local/share/icons`, `index.theme` heredando el tema, `dconf`/`hyprctl setcursor` al iniciar y `no_hardware_cursors = true` + `inactive_timeout = 0`.
- **Consecuencias**:
  - Positivas: cursor consistente.
  - Negativas: la misma configuración está en 5–6 sitios; difícil saber cuál es la que realmente funciona.

## ADR-005: Tema oscuro unificado Adwaita-dark + paleta azul/Catppuccin (paleta centralizada en ADR-015)
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
- **Decisión**: `services.tailscale.enable` y `sudo tailscale up` al final de `init.sh`. WayVNC (cliente AVNC en el celular) solo por Tailscale y sin contraseña: `utils/wayvnc-tailscale.sh` (al iniciar sesión y alias `remote-conexion`) espera la IP de Tailscale y escucha solo en ella; el firewall abre el 5900 solo en `tailscale0`. (Antes: `0.0.0.0` con el puerto abierto en todas las redes, sin contraseña.)
- **Consecuencias**: control remoto desde cualquier lugar con Tailscale activo en el celular, cifrado por la VPN; desde el wifi sin Tailscale no conecta. Cualquier dispositivo de la tailnet puede controlar el escritorio (ver `06-errores-conocidos.md`).

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

## ADR-014: pwvucontrol en lugar de pulsemixer como gestor de volumen
- **Fecha**: 2026-10-04
- **Contexto**: `pulsemixer` (TUI en Kitty, clase `pomo-mixer`) no encajaba con el flujo visual del escritorio.
- **Decisión**: `pwvucontrol` (GTK4, nativo de PipeWire) se abre/cierra con clic en el módulo `pulseaudio` de Waybar; Hyprland lo hace flotante (760×450) debajo de la barra, a la derecha, con opacidad 0.9/0.8.
- **Consecuencias**: interfaz gráfica que sigue el modo oscuro (libadwaita + `prefer-dark`) y gestiona dispositivos y apps por separado; la posición está fijada en píxeles para un monitor de 1920 px de ancho.

## ADR-015: Tema único en `tema/tema.conf` con generador (presets y archivos sin versionar en ADR-020)
- **Fecha**: 2026-10-04
- **Contexto**: Los colores, la fuente y los radios estaban repetidos en Hyprland, Waybar, Kitty, Rofi, `powermenu.sh` y `atajos.sh`, con valores que ya no coincidían (Kitty usaba una fuente no instalada, GTK un tema de iconos inexistente). Cambiar el aspecto obligaba a tocar 6+ archivos.
- **Decisión**: `tema/tema.conf` con líneas `NOMBRE="valor"`, formato válido a la vez para bash (`source`) y TOML (`builtins.fromTOML`). `utils/aplicar-tema.sh` genera un archivo `tema.*` por app en el formato que cada una entiende y recarga lo que está corriendo; las configs lo incluyen y solo conservan el diseño. Rofi pasa a un único tema propio (`themes/nova.rasi`) que usan el lanzador, el menú de apagado y la lista de atajos. Mako se versiona como archivo generado.
- **Consecuencias**:
  - Positivas: cambiar un color o la fuente es editar una línea y ejecutar `tema-aplicar`; GRUB y el login usan los mismos valores.
  - Negativas: los archivos generados se versionan y pueden quedar desfasados si se edita `tema.conf` sin ejecutar el generador; el formato compartido no admite `$` ni comillas simples.

## ADR-016: GRUB con tema propio en lugar de systemd-boot
- **Fecha**: 2026-10-04
- **Contexto**: systemd-boot no admite temas; el arranque mostraba un menú de texto y mensajes del kernel que no encajaban con el escritorio.
- **Decisión**: `boot.loader.grub` EFI (`device = "nodev"`). `tema/tema.nix` construye el tema en Nix: fondo de pantalla desenfocado y teñido con `FONDO`, fuentes `.pf2` generadas desde la fuente del tema, cajas redondeadas e iconos Nerd Font en `ACENTO`, textos en español y entradas extra (firmware UEFI, reiniciar, apagar). Arranque silencioso con `quiet`, `udev.log_level=3` y `initrd.verbose = false`.
- **Consecuencias**:
  - Positivas: el menú de arranque sigue la paleta y se regenera solo con `nix-switch` al cambiar el tema.
  - Negativas: la entrada de systemd-boot queda en la partición EFI como respaldo; el diseño está pensado para 1920×1080 (`gfxmodeEfi`).

## ADR-017: nwg-hello en lugar de tuigreet
- **Fecha**: 2026-10-04
- **Contexto**: `tuigreet` es de texto y no podía seguir los colores ni el fondo del escritorio.
- **Decisión**: greetd ejecuta un Hyprland mínimo (`start-hyprland -- --config` generado en `tema/tema.nix`) que pone el fondo de pantalla con `swaybg` y abre `nwg-hello` con desenfoque (`layerrule … match:namespace nwg-hello`). El CSS, la plantilla (con `message-label` para los errores) y los textos en español (`es_MX`) se generan desde el tema; al cerrar el greeter, `hyprctl dispatch exit` termina su Hyprland.
- **Consecuencias**:
  - Positivas: login gráfico con la misma paleta, fuente, cursor y fondo que la sesión.
  - Negativas: arranca un compositor más antes de la sesión (≈1 s); el paquete `nwg-hello` se sobrescribe (`overrideAttrs`) para añadir el idioma.

## ADR-018: hyprlock + hypridle en lugar de swaylock
- **Fecha**: 2026-10-04
- **Contexto**: El bloqueo al suspender era `swaylock-effects` (un anillo sobre una captura desenfocada) lanzado a mano desde el menú de apagado con `swaylock -f && sleep 1 && systemctl suspend`; no seguía el diseño del login y otras suspensiones (desde el login o `systemctl suspend`) no bloqueaban.
- **Decisión**: `programs.hyprlock` (paquete + PAM) con `config/hypr/hyprlock.conf`, que repite el panel del login (reloj, fecha, avatar, campo de contraseña) sobre el fondo desenfocado y toma colores, fuente y radio de `config/hypr/tema.conf`. `hypridle` (arrancado con `exec-once`) bloquea en `before_sleep_cmd` y enciende la pantalla al volver; no tiene temporizadores de inactividad. El menú de apagado y Valent suspenden con `systemctl suspend` y bloquean con `loginctl lock-session`.
- **Consecuencias**:
  - Positivas: bloqueo y login se ven iguales; cualquier suspensión bloquea antes de dormir, sin `sleep` de espera.
  - Negativas: si `hypridle` no está corriendo, suspender no bloquea; las posiciones del panel están en píxeles para 1920×1080.

## ADR-019: Módulos por función + equipos, con el hardware fuera del repo
- **Fecha**: 2026-10-04
- **Contexto**: Cada máquina nueva se montaba copiando `nixos-pc-asus/` (con su `hardware-configuration.nix`) y editando la copia. Las copias divergían, un cambio común había que repetirlo en cada carpeta, y `/etc/nixos` enlazado al hardware de la ASUS hacía que otras PCs no arrancaran.
- **Decisión**: La configuración de sistema se parte en `nixos/modulos/` (base, escritorio, tema, desarrollo, remoto, juegos). Cada máquina tiene `nixos/equipos/<equipo>/default.nix`, que solo elige módulos y define lo propio (hostname, arranque, `stateVersion`). `/etc/nixos/configuration.nix` es un archivo local que escribe `init.sh` e importa `./hardware-configuration.nix` (el de la máquina, nunca versionado) y el equipo. Los equipos nuevos salen de `nixos/equipos/plantilla` con `./init.sh nuevo-equipo <nombre>`. La opción `dotfiles.equipo` permite que el alias `nix-config` abra el archivo del equipo actual.
- **Consecuencias**:
  - Positivas: un cambio común se escribe una vez y llega a todas las máquinas con `git pull`; quitar Steam de la laptop es comentar `juegos.nix` en su equipo; una configuración ya no puede arrancar con los discos de otra PC.
  - Negativas: `hardware-configuration.nix` no tiene respaldo en git (se regenera con `nixos-generate-config`); las rutas absolutas `/home/nova/dotfiles` obligan a clonar en esa ubicación.

## ADR-020: Temas predefinidos con selector y archivos generados sin versionar
- **Fecha**: 2026-10-04
- **Contexto**: Con un solo `tema/tema.conf` versionado, cambiar de aspecto era editar valores a mano, y cada `tema-aplicar` ensuciaba git con los archivos generados (que además chocaban entre máquinas con temas distintos).
- **Decisión**: Los temas viven en `tema/temas/<nombre>.conf` (con `NOMBRE` y `DESCRIPCION`). `tema/tema.conf` pasa a ser un symlink local al elegido; `nixos/modulos/tema.nix` cae a `nova.conf` si no existe. `utils/elegir-tema.sh` (`SUPER + F2`, sin botón en Waybar) muestra en Rofi una vista previa de cada tema (fondo + franjas de color generadas con ImageMagick y cacheadas) y aplica el elegido con `aplicar-tema.sh <nombre>`. Los archivos generados (`config/*/tema.*`, `config/mako/config`) salen de git.
- **Consecuencias**:
  - Positivas: cambiar de tema es un atajo; cada máquina puede tener el suyo; `git status` queda limpio.
  - Negativas: tras clonar hay que ejecutar `init.sh usuario` (o `tema-aplicar`) antes de que Hyprland, Waybar y Kitty encuentren sus `tema.*`; GRUB y el login no cambian hasta `nix-switch`.

## ADR-021: `init.sh` por pasos, idempotente y con respaldos
- **Fecha**: 2026-10-04
- **Contexto**: El `init.sh` anterior hacía `rm -rf` de las carpetas de `~/.config`, no se detenía ante errores, anidaba carpetas al repetirse (fastfetch, `icons/icons`), escribía rutas con `~` literal en `.bash_profile`, descargaba Thorium en cada ejecución y no tocaba la configuración del sistema.
- **Decisión**: Script con `set -euo pipefail` y subcomandos: `usuario` (enlaces, archivos locales, tema), `sistema [equipo]` (escribe `/etc/nixos/configuration.nix`, migra symlinks antiguos, conserva o regenera el hardware y ejecuta `nixos-rebuild switch`), `apps`, `red`, `actualizar` (`git pull --rebase --autostash` + usuario + sistema), `nuevo-equipo` y `todo` (por defecto). Lo que reemplaza lo respalda; `--simular` muestra los comandos con `sudo` sin ejecutarlos; los avisos se resumen al final.
- **Consecuencias**:
  - Positivas: instalar y actualizar es el mismo script; se puede repetir sin efectos acumulados; el alias `dotfiles-actualizar` sincroniza una máquina en un paso.
  - Negativas: depende de que el repo esté en `~/dotfiles`; `nixos-rebuild switch` en `actualizar` tarda aunque no haya cambios de sistema.

## ADR-022: Tareas en un tablero kanban de Notion
- **Fecha**: 2026-10-04
- **Contexto**: Los cambios grandes (reorganización, arranque, sesión) tienen varios pasos, algunos solo los puede hacer el usuario (sudo, reiniciar), y no quedaba registro de qué estaba hecho y qué faltaba revisar.
- **Decisión**: Cada tarea es una tarjeta en el tablero de Notion "nixos" con diagnóstico, pasos y verificación. El agente las pasa por Not started → In progress → In revision; el usuario las revisa y las pasa a Done. La regla `.cursor/rules/kanban-notion.mdc` lo hace obligatorio.
- **Consecuencias**:
  - Positivas: el estado del proyecto se ve de un vistazo y lo pendiente del usuario queda escrito en cada tarjeta.
  - Negativas: depende del conector de Notion en Cursor; el historial técnico sigue en git y los dos pueden desincronizarse.

## ADR-023: GTK con adw-gtk3 y la paleta del tema
- **Fecha**: 2026-10-04
- **Contexto**: Thunar (y el resto de apps GTK) no cambiaba de color con el tema: `Adwaita-dark` trae los colores compilados y no se pueden redefinir. Se evaluó cambiar a Dolphin (esquema de color de KDE generado), pero suma dependencias de KDE/Qt y una configuración de Qt aparte, sin ganar nada en miniaturas ni en "Abrir con".
- **Decisión**: Mantener Thunar y usar `adw-gtk3-dark`, que define sus colores como variables. `utils/aplicar-tema.sh` genera el tema GTK `~/.local/share/themes/dotfiles-tema` (importa `adw-gtk3-dark` y redefine la paleta) y `config/gtk-4.0/gtk.css` para las apps de libadwaita. Al aplicar un tema cambia el nombre del tema GTK en dconf y vuelve, para que las ventanas abiertas lo relean. GTK2 sigue con `Adwaita-dark`.
- **Consecuencias**:
  - Positivas: Thunar y las apps GTK3 cambian de color al momento con `SUPER + F2`; las GTK4/libadwaita (pwvucontrol) al reabrirlas.
  - Negativas: el tema GTK vive fuera del repo y depende de que exista `adw-gtk3` (si falta, cae a Adwaita oscuro sin colores y avisa); nwg-look puede sobrescribir `gtk-theme-name`.

## ADR-024: Color de las carpetas en cada tema
- **Fecha**: 2026-10-04
- **Contexto**: Papirus trae las carpetas en ~25 colores y elige uno con enlaces (`folder.svg -> folder-blue.svg`) fijados al instalar. `papirus-folders` los cambia escribiendo en el tema, que en NixOS es de solo lectura; un `override` del paquete obligaría a `nix-switch` en cada cambio de tema.
- **Decisión**: Variable `COLOR_CARPETAS` en cada tema. `utils/aplicar-tema.sh` genera `~/.local/share/icons/dotfiles-iconos`, que hereda de `ICONOS` y solo contiene enlaces a las carpetas del color elegido (sigue las cadenas de alias, como `folder-downloads`); GTK usa ese tema de iconos y Rofi/Mako siguen con `ICONOS`. Se regenera solo si cambian el color o la versión de Papirus.
- **Consecuencias**:
  - Positivas: las carpetas cambian con `SUPER + F2`, en vivo en Thunar.
  - Negativas: solo funciona con temas de iconos Papirus (con otros avisa y deja las carpetas como están); el tema de iconos vive fuera del repo.

## ADR-025: Usuario por equipo y Kubernetes local en desarrollo
- **Fecha**: 2026-10-05
- **Contexto**: La PC de admisión (`pc-admision-jorge`) usa el usuario `admision` y arranca con systemd-boot; los módulos tenían `nova` fijo. Su configuración antigua incluía la capa de Kubernetes local (Kind + Skaffold) con dominios `*.admision.dev` en `/etc/hosts`.
- **Decisión**: Opción `dotfiles.usuario` en `base.nix` (por defecto `nova`); los módulos usan `users.users.${config.dotfiles.usuario}`. `pc-admision-jorge` la fija en `admision`, mantiene systemd-boot (el tema de GRUB de `tema.nix` no aplica) y define sus aliases de infraestructura (`k-prod`, `open-conexion`). Kind, Skaffold, `kubectl`, `gnumake`, los dominios locales y el aumento de inotify van en `desarrollo.nix`, para todos los equipos que lo usan.
- **Consecuencias**:
  - Positivas: los mismos módulos sirven para cualquier usuario; el entorno de Kubernetes local es igual en todas las máquinas de desarrollo.
  - Negativas: el repo sigue debiendo estar en `~/dotfiles` del usuario; los dominios de admisión apuntan a `127.0.0.1` en todas las máquinas con `desarrollo.nix`.

## ADR-026: Cursor del color de cada tema
- **Fecha**: 2026-10-09
- **Contexto**: Todos los temas usaban el cursor celeste (`catppuccin-mocha-sky-cursors`) aunque su acento fuera rojo, rosa o dorado. Además `XCURSOR_THEME` lo fija Nix en cada `nix-switch`, así que las apps abiertas tras cambiar de tema con `SUPER + F2` seguían con el cursor anterior.
- **Decisión**: `escritorio.nix` instala una variante Catppuccin Mocha por tema (Sky, Red, Pink, Blue, Yellow, Mauve) y cada tema elige la de su acento en `CURSOR`. `hyprland.conf` vuelve a definir `XCURSOR_*`/`HYPRCURSOR_*` con `$cursor` (Hyprland reaplica `env` en cada recarga). Si el cursor del tema no está instalado, `aplicar-tema.sh` avisa y mantiene el actual.
- **Consecuencias**:
  - Positivas: el cursor cambia con el tema, en vivo y en las apps nuevas, sin `nix-switch`.
  - Negativas: los colores de Catppuccin son pastel y no coinciden exactamente con el acento; un tema nuevo con otro color necesita añadir su variante en `escritorio.nix` y hacer `nix-switch`; las apps abiertas antes del cambio que no leen dconf conservan el cursor anterior.
