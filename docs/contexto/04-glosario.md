# Glosario y Lenguaje Ubicuo

*Términos que aparecen en el código, commits y documentación de este repositorio.*

## Conceptos del proyecto

- **Dotfiles**: este repositorio. Configuración personal versionada que se despliega en `~/.config`, `~/.local/share` y `/etc/nixos`.
- **Equipo**: una máquina física con su propia carpeta `nixos-<equipo>/` (hoy `nixos-pc-asus`; antes `nixos-laptop-hp`).
- **Capa de sistema**: lo que gestiona NixOS con root (`configuration.nix`). Se aplica con `nix-switch`.
- **Capa de usuario**: configuraciones en `config/` enlazadas por `init.sh`. Se aplica al instante al guardar (y recargar la app).
- **Enlazar / symlink**: `ln -sfn ~/dotfiles/<origen> <destino>`. Es la forma en que el repo "se instala".
- **Inicializar / `init.sh`**: script que prepara la capa de usuario en una máquina nueva: carpetas, `.env`, symlinks, permisos, cursor, Flatpak, AppImage y Tailscale.
- **Secretos / `.env`**: archivo local con valores sensibles (`PASS_SWAYLOCK`). Nunca se versiona.
- **Arranque automático**: comandos `exec-once` de Hyprland que se ejecutan al iniciar sesión.

## Escritorio

- **Hyprland**: compositor Wayland en mosaico (tiling). Configurado en `config/hypr/hyprland.conf`.
- **`$mainMod` / SUPER**: tecla Windows; modificador de todos los atajos de Hyprland.
- **Workspace / pantalla**: escritorio virtual 1–10 (`SUPER + 0-9`). En los comentarios se le llama "pantalla".
- **Dwindle**: layout de Hyprland que divide el espacio en espiral binaria.
- **Ventana flotante**: ventana fuera del mosaico (`SUPER + V`, o por regla `windowrule`).
- **Waybar**: barra superior. **Módulo** = cada bloque de la barra (`clock`, `cpu`, `custom/pomo`…).
- **Módulo custom**: bloque de Waybar alimentado por un script que imprime JSON `{text, tooltip, class}`.
- **Rofi**: lanzador de aplicaciones (`SUPER + R`, modo `drun`) y menús de selección (modo `dmenu`).
- **Lista de atajos**: menú Rofi que abre `SUPER + F1` o el botón del teclado en Waybar (`utils/atajos.sh`) con el contenido de `utils/atajos.txt`, la única fuente de atajos del proyecto.
- **Menú de apagado / powermenu**: `config/waybar/scripts/powermenu.sh`; opciones Apagar, Reiniciar, Suspender, Cerrar Sesión. Se abre con `SUPER + X` o el botón ⏻.
- **Pomodoro / pomo**: temporizador en Waybar (`pomo.sh`). Clic izquierdo inicia, clic derecho detiene.
  - **Ronda**: bloque de trabajo de 25 min (`WORK`). Hay 4 por ciclo.
  - **Descanso corto** (`BREAK`): 5 min tras las rondas 1–3.
  - **Descanso largo** (`LONG`): 15 min tras la ronda 4; reinicia el contador.
  - **Idle**: sin temporizador activo.
- **Gestor de volumen / `pwvucontrol`**: ventana flotante (clase `com.saivert.pwvucontrol`) que se abre o cierra al hacer clic en el volumen de Waybar; también se cierra con `Escape` si tiene el foco (`bindn` en `hyprland.conf`). Sustituyó a `pulsemixer` en Kitty (clase `pomo-mixer`, que no tenía relación con el Pomodoro).
- **Tema / `tema.conf`**: archivo `tema/tema.conf` con la paleta, la fuente, el radio, el fondo, el cursor y los iconos de todo el proyecto. **Aplicar el tema** (`tema-aplicar`) regenera los archivos `tema.*` de `config/` y recarga el escritorio.
- **Acento / secundario / fondo / superficie**: nombres de los colores del tema: acento (azul principal), secundario (morado del degradado), fondo (azul marino oscuro), superficie (azul de los paneles).
- **GRUB**: menú de arranque; su tema (fondo, fuentes, iconos) lo genera `tema/tema.nix`.
- **greetd / nwg-hello**: gestor de inicio de sesión. greetd abre un Hyprland mínimo en el que `nwg-hello` muestra la pantalla de login (reloj, sesión, usuario, contraseña y botones de apagado). Sustituyó a `tuigreet` (login en modo texto).
- **Mako**: demonio de notificaciones (`notify-send`).
- **swaylock**: bloqueo de pantalla (con efectos de blur y reloj); sus opciones están en `config/swaylock/config`.
- **swaybg**: pone el fondo de pantalla (hoy `public/background/gojo2.png`).
- **nwg-look**: herramienta gráfica que generó `gtk-3.0/`, `gtk-4.0/`, `gtkrc-2.0` e `index.theme`.

## Integraciones

- **Valent**: implementación GTK del protocolo KDE Connect. Conecta el celular para notificaciones, portapapeles y **comandos remotos** (bloquear, desbloquear, apagar, suspender).
- **Dispositivo Valent**: celular emparejado, identificado por un ID (`9f91b454…` hardcodeado en `valent-clipboard.sh`).
- **Puente de portapapeles**: `wl-paste -t text --watch utils/valent-clipboard.sh`; envía cada texto copiado al celular por D-Bus (`share.text`).
- **Desbloqueo remoto**: comando de Valent que escribe `PASS_SWAYLOCK` con `wtype` sobre swaylock.
- **Tailscale / tailnet**: VPN mesh para alcanzar el PC desde fuera de la LAN.
- **WayVNC**: servidor VNC para Wayland; "compartir pantalla" o "conexión remota" en los comentarios (puerto 5900). Alias `remote-conexion`.
- **AppImage**: binario portable; en NixOS se ejecuta con `appimage-run`. Se guardan en `~/.local/bin/appimages/`.
- **Flatpak / Flathub**: sistema de paquetes sandbox; de ahí viene Zen Browser (`app.zen_browser.zen`).

## NixOS

- **`configuration.nix`**: archivo declarativo del sistema.
- **`hardware-configuration.nix`**: generado por `nixos-generate-config`; contiene UUIDs de discos. Es específico de cada equipo.
- **Rebuild / switch**: `sudo nixos-rebuild switch` (alias `nix-switch`); construye y activa la nueva generación.
- **Generación**: versión del sistema tras cada rebuild; permite volver atrás desde el menú de arranque (submenú de GRUB).
- **Store (`/nix/store`)**: donde viven los paquetes; las rutas incluyen un hash y cambian con cada versión.
- **GC (recolector de basura)**: borra generaciones y paquetes no usados (automático semanal, o `nix-clean`).
- **`/run/current-system/sw`**: perfil del sistema activo; ruta estable a binarios, iconos y sonidos instalados.
- **unfree**: software privativo (VS Code, Navicat, Cursor…); habilitado con `allowUnfree = true`.
