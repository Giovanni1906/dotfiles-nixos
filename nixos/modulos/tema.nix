# =============================================================================
# TEMA DEL SISTEMA: GRUB, pantalla de inicio de sesión y cursor
# =============================================================================
# Lee tema/tema.conf (el mismo archivo que usa utils/aplicar-tema.sh para el
# escritorio), así GRUB, el login y la sesión comparten colores, fuente y fondo.
# Se importa desde nixos/equipos/<equipo> y se aplica con nix-switch.

{ config, pkgs, lib, ... }:

let
  raiz = ../..;
  # tema/tema.conf es el enlace local al tema elegido (SUPER + F2); sin elegir, el tema nova
  archivoTema =
    if builtins.pathExists (raiz + "/tema/tema.conf")
    then raiz + "/tema/tema.conf"
    else raiz + "/tema/temas/nova.conf";
  tema = builtins.fromTOML (builtins.readFile archivoTema);

  # "0.70" -> "b3" (canal alfa en hexadecimal para colores #RRGGBBAA)
  alfa = opacidad:
    lib.toLower (lib.fixedWidthString 2 "0"
      (lib.toHexString (builtins.floor ((builtins.fromJSON opacidad) * 255 + 0.5))));

  # Copia solo la imagen al store (con nombre seguro aunque el archivo tenga espacios o paréntesis)
  extension = lib.last (lib.splitString "." tema.FONDO_PANTALLA);
  fondoPantalla = builtins.path {
    path = raiz + "/${tema.FONDO_PANTALLA}";
    name = "fondo-pantalla.${extension}";
  };

  # Fontconfig con las fuentes del sistema, para encontrar el archivo de tema.FUENTE
  fuentesSistema = pkgs.makeFontsConf { fontDirectories = config.fonts.packages; };

  hyprland = config.programs.hyprland.package;

  # ---------------------------------------------------------------------------
  # GRUB
  # ---------------------------------------------------------------------------
  temaGrub = pkgs.runCommand "tema-grub" {
    nativeBuildInputs = [ pkgs.imagemagick pkgs.grub2 pkgs.fontconfig ];
  } ''
    # C.UTF-8 para que printf "\uXXXX" produzca el glifo y no el texto literal
    export HOME=$TMPDIR FONTCONFIG_FILE=${fuentesSistema} LC_ALL=C.UTF-8
    mkdir -p $out/icons
    cd $TMPDIR

    regular=$(fc-match -f '%{file}' "${tema.FUENTE}:style=Regular")
    negrita=$(fc-match -f '%{file}' "${tema.FUENTE}:style=Bold")

    # Fondo: mismo wallpaper del escritorio, recortado a 1920x1080, con un velo de FONDO
    magick ${fondoPantalla} -resize 1920x1080^ -gravity center -extent 1920x1080 \
      -blur 0x3 -fill '${tema.FONDO}' -colorize 35% PNG24:$out/fondo.png

    # Fuentes de GRUB (.pf2): latín, flechas y cajas de dibujo
    rangos=0x20-0x7E,0xA0-0x17F,0x2013-0x2026,0x2190-0x2193,0x2500-0x257F
    for t in 16 20; do
      grub-mkfont -n Nova -s $t -r $rangos -o $out/nova-regular-$t.pf2 "$regular"
    done
    for t in 20 40; do
      grub-mkfont -n Nova -s $t -r $rangos -o $out/nova-negrita-$t.pf2 "$negrita"
    done

    # Caja redondeada en 9 piezas (nw n ne w c e sw s se) para que GRUB la estire
    caja() { # nombre relleno borde grosor radio
      local s=$(( $5 * 3 )) m=$(( $4 / 2 ))
      magick -size ''${s}x''${s} xc:none -fill "$2" -stroke "$3" -strokewidth $4 \
        -draw "roundrectangle $m,$m $(( s - 1 - m )),$(( s - 1 - m )) $5,$5" PNG32:caja.png
      magick caja.png -crop $5x$5 +repage PNG32:pieza-%d.png
      local i=0
      for p in nw n ne w c e sw s se; do mv pieza-$i.png $out/$1_$p.png; i=$(( i + 1 )); done
    }
    caja menu      '${tema.FONDO}${alfa tema.OPACIDAD_PANEL}'      '${tema.SUPERFICIE}' 2 ${tema.RADIO}
    caja select    '${tema.SUPERFICIE}${alfa tema.OPACIDAD_PANEL}' '${tema.ACENTO}'     2 ${tema.RADIO}
    caja terminal_box '${tema.FONDO}f2'                            '${tema.ACENTO}'     2 ${tema.RADIO}

    # Barra de cuenta atrás: GRUB le impone 28 px de alto, así que las piezas superior
    # e inferior son transparentes (12 px cada una) y solo se ve una línea de 4 px
    magick -size 1x12 xc:none PNG32:$out/barra_n.png
    cp $out/barra_n.png $out/barra_s.png
    magick -size 1x1 xc:'${tema.SUPERFICIE}' PNG32:$out/barra_c.png
    magick -size 1x1 xc:'${tema.ACENTO}' PNG32:$out/barra_hl_c.png

    # Iconos (glifos de la Nerd Font en el color de acento) según la clase de cada entrada
    icono() { # archivo glifo tamaño
      magick -background none -fill '${tema.ACENTO}' -font "$regular" -pointsize 160 \
        label:"$(printf "\\u$2")" -trim +repage -resize $3x$3 -gravity center -extent $3x$3 PNG32:$1
    }
    icono $out/logo.png f313 88
    icono $out/icons/nixos.png f313 28
    icono $out/icons/submenu.png f1da 28
    icono $out/icons/efi.png f013 28
    icono $out/icons/restart.png f021 28
    icono $out/icons/shutdown.png f011 28

    cat > $out/theme.txt <<'EOF'
    title-text: ""
    desktop-image: "fondo.png"
    desktop-image-scale-method: "crop"
    desktop-color: "${tema.FONDO}"
    terminal-font: "Nova Regular 16"
    terminal-box: "terminal_box_*.png"
    terminal-left: "10%"
    terminal-top: "10%"
    terminal-width: "80%"
    terminal-height: "80%"
    terminal-border: "0"

    + image {
      left = 50%-44
      top = 13%
      width = 88
      height = 88
      file = "logo.png"
    }

    + label {
      left = 0
      top = 13%+104
      width = 100%
      height = 50
      align = "center"
      text = "NixOS"
      font = "Nova Bold 40"
      color = "${tema.ACENTO}"
    }

    + label {
      left = 0
      top = 13%+160
      width = 100%
      height = 26
      align = "center"
      text = "Elige cómo arrancar"
      font = "Nova Regular 16"
      color = "${tema.TEXTO_TENUE}"
    }

    + boot_menu {
      left = 50%-380
      top = 13%+220
      width = 760
      height = 372
      menu_pixmap_style = "menu_*.png"
      selected_item_pixmap_style = "select_*.png"
      item_font = "Nova Regular 20"
      selected_item_font = "Nova Bold 20"
      item_color = "${tema.TEXTO}"
      selected_item_color = "${tema.TEXTO}"
      icon_width = 28
      icon_height = 28
      item_icon_space = 18
      item_height = 46
      item_padding = 16
      item_spacing = 12
      scrollbar = false
    }

    + progress_bar {
      id = "__timeout__"
      left = 50%-380
      top = 13%+612
      width = 760
      height = 28
      bar_style = "barra_*.png"
      highlight_style = "barra_hl_*.png"
    }

    + label {
      id = "__timeout__"
      left = 0
      top = 13%+644
      width = 100%
      height = 24
      align = "center"
      text = "Arranque automático en %d s"
      font = "Nova Regular 16"
      color = "${tema.TEXTO_TENUE}"
    }

    + label {
      left = 0
      top = 100%-56
      width = 100%
      height = 24
      align = "center"
      text = "↑ ↓  elegir   ·   Enter  arrancar   ·   E  editar   ·   C  consola"
      font = "Nova Regular 16"
      color = "${tema.TEXTO_TENUE}"
    }
    EOF
  '';

  # ---------------------------------------------------------------------------
  # PANTALLA DE INICIO DE SESIÓN: greetd + nwg-hello dentro de un Hyprland mínimo
  # ---------------------------------------------------------------------------
  # Textos en español (los de es_ES de nwg-hello dicen "Acceso", "Apagado"...)
  idiomaGreeter = pkgs.writeText "nwg-hello-es_MX" (builtins.toJSON {
    failed-starting-session = "No se pudo iniciar la sesión";
    login = "Entrar";
    login-failed = "Contraseña incorrecta";
    password = "Contraseña";
    password-empty = "Escribe tu contraseña";
    power-off = "Apagar";
    session = "Sesión";
    show-password = "Mostrar contraseña";
    sleep = "Suspender";
    reboot = "Reiniciar";
    user = "Usuario";
    welcome = "¡Hola de nuevo!";
  });

  nwgHello = pkgs.nwg-hello.overrideAttrs (old: {
    postInstall = (old.postInstall or "") + ''
      install -D -m 644 ${idiomaGreeter} "$out/etc/nwg-hello/es_MX"
    '';
  });

  # Plantilla original con un nombre CSS para la etiqueta de errores (upstream no le pone)
  plantillaGreeter = pkgs.runCommand "nwg-hello-tema.glade" { } ''
    substitute ${nwgHello}/${pkgs.python3.sitePackages}/nwg_hello/template.glade $out \
      --replace-fail '<object class="GtkLabel" id="lbl-message">' \
        '<object class="GtkLabel" id="lbl-message"><property name="name">message-label</property>'
  '';

  # Solo la sesión normal de Hyprland (la de uwsm no se usa en este equipo)
  sesiones = pkgs.runCommand "sesiones-greeter" { } ''
    mkdir -p $out
    cp ${hyprland}/share/wayland-sessions/hyprland.desktop $out/
  '';

  configGreeter = pkgs.writeText "nwg-hello.json" (builtins.toJSON {
    session_dirs = [ "${sesiones}" ];
    custom_sessions = [ ];
    monitor_nums = [ ];
    form_on_monitors = [ ];
    delay_secs = 0;
    cmd-sleep = "/run/current-system/sw/bin/systemctl suspend";
    cmd-reboot = "/run/current-system/sw/bin/systemctl reboot";
    cmd-poweroff = "/run/current-system/sw/bin/systemctl poweroff";
    gtk-theme = "Adwaita";
    gtk-icon-theme = tema.ICONOS;
    gtk-cursor-theme = tema.CURSOR;
    prefer-dark-theme = true;
    template-name = "tema.glade";
    time-format = "%H:%M";
    date-format = "%A, %d de %B";
    layer = "overlay";
    keyboard-mode = "exclusive";
    lang = "es_MX";
    avatar-show = false;
    env-vars = [ ];
  });

  estiloGreeter = pkgs.writeText "nwg-hello.css" ''
    @define-color acento ${tema.ACENTO};
    @define-color fondo ${tema.FONDO};
    @define-color superficie ${tema.SUPERFICIE};
    @define-color texto ${tema.TEXTO};
    @define-color texto_tenue ${tema.TEXTO_TENUE};
    @define-color urgente ${tema.URGENTE};

    * {
      font-family: "${tema.FUENTE}", sans-serif;
      font-size: ${toString (lib.toInt tema.FUENTE_TAMANO + 3)}pt;
      color: @texto;
      text-shadow: none;
      box-shadow: none;
    }

    /* Ventana transparente: detrás está el fondo (swaybg) desenfocado por Hyprland */
    window {
      background: transparent;
    }

    /* Panel lateral con el mismo estilo que los módulos de Waybar */
    #form-wrapper {
      margin: 40px;
      background-color: alpha(@fondo, ${tema.OPACIDAD_PANEL});
      border: ${tema.BORDE}px solid alpha(@acento, 0.6);
      border-radius: ${tema.RADIO}px;
    }

    #welcome-label {
      font-size: 22pt;
      color: @texto;
    }

    #clock-label {
      font-size: 64pt;
      font-weight: bold;
      color: @acento;
    }

    #date-label {
      font-size: 15pt;
      color: @texto_tenue;
    }

    #form-label {
      color: @texto_tenue;
    }

    entry,
    combobox button {
      background: alpha(@superficie, ${tema.OPACIDAD_PANEL}) none;
      color: @texto;
      border: 1px solid transparent;
      border-radius: ${tema.RADIO}px;
      padding: 10px 14px;
      caret-color: @acento;
    }

    entry:focus,
    combobox button:hover {
      border-color: @acento;
    }

    button {
      background: alpha(@superficie, ${tema.OPACIDAD_PANEL}) none;
      border: 1px solid transparent;
      border-radius: ${tema.RADIO}px;
      padding: 10px 16px;
    }

    button:hover {
      background-color: alpha(@superficie, 0.4);
      border-color: @acento;
    }

    #login-button {
      background: @acento none;
      font-weight: bold;
    }

    #login-button label {
      color: @fondo;
    }

    #login-button:hover {
      background: alpha(@acento, 0.85) none;
    }

    #power-button {
      background: none;
      border: 1px solid transparent;
    }

    #power-button:hover {
      background-color: alpha(@superficie, 0.5);
      border-color: @acento;
    }

    checkbutton check {
      background: alpha(@superficie, ${tema.OPACIDAD_PANEL}) none;
      border: 1px solid @texto_tenue;
      border-radius: 4px;
    }

    checkbutton check:checked {
      background-color: @acento;
      border-color: @acento;
    }

    /* Mensajes de error (contraseña incorrecta, etc.) */
    #message-label {
      color: @urgente;
    }

    menu,
    .menu {
      background-color: @fondo;
      border: 1px solid @acento;
      border-radius: ${tema.RADIO}px;
      padding: 4px;
    }

    menuitem {
      padding: 8px 12px;
      border-radius: ${tema.RADIO}px;
    }

    menuitem:hover {
      background-color: @superficie;
    }
  '';

  hyprlandGreeter = pkgs.writeText "hyprland-greeter.conf" ''
    # Hyprland mínimo que solo muestra nwg-hello. Generado por nixos/modulos/tema.nix.
    monitor = , preferred, auto, 1

    env = XCURSOR_THEME,${tema.CURSOR}
    env = XCURSOR_SIZE,${tema.CURSOR_TAMANO}
    env = HYPRCURSOR_THEME,${tema.CURSOR}
    env = HYPRCURSOR_SIZE,${tema.CURSOR_TAMANO}
    env = XCURSOR_PATH,/run/current-system/sw/share/icons
    env = XDG_DATA_DIRS,/run/current-system/sw/share

    input {
        kb_layout = ${config.services.xserver.xkb.layout}
    }

    cursor {
        no_hardware_cursors = true
        inactive_timeout = 0
    }

    general {
        border_size = 0
        gaps_out = 0
    }

    decoration {
        blur {
            enabled = true
            size = 8
            passes = 3
        }
    }

    misc {
        disable_hyprland_logo = true
        disable_splash_rendering = true
        force_default_wallpaper = 0
    }

    ecosystem {
        no_update_news = true
        no_donation_nag = true
    }

    # Desenfoca el fondo solo detrás del panel (lo transparente de la ventana se ignora)
    layerrule = blur on, ignore_alpha 0.2, match:namespace nwg-hello

    exec-once = ${pkgs.swaybg}/bin/swaybg -i ${fondoPantalla} -m fill
    exec-once = ${nwgHello}/bin/nwg-hello -c ${configGreeter} -s ${estiloGreeter}; ${hyprland}/bin/hyprctl dispatch exit
  '';
in
{
  # --- GRUB ---
  boot.loader.grub = {
    theme = temaGrub;
    splashImage = null;
    gfxmodeEfi = "1920x1080,auto";
    extraEntries = ''
      menuentry "Configuración del firmware (UEFI)" --class efi {
        fwsetup
      }
      menuentry "Reiniciar" --class restart {
        reboot
      }
      menuentry "Apagar" --class shutdown {
        halt
      }
    '';
  };

  # Arranque sin texto entre GRUB y el login
  boot.kernelParams = [ "quiet" "udev.log_level=3" ];
  boot.consoleLogLevel = 3;
  boot.initrd.verbose = false;

  # --- PANTALLA DE INICIO DE SESIÓN ---
  services.greetd = {
    enable = true;
    settings.default_session = {
      command = "${pkgs.dbus}/bin/dbus-run-session ${hyprland}/bin/start-hyprland -- --config ${hyprlandGreeter}";
      user = "greeter";
    };
  };
  # "idle" (el de NixOS) retrasa el login hasta que terminan los demás servicios (hasta 5 s,
  # por NetworkManager-wait-online); con el arranque silencioso no hay texto que se mezcle.
  systemd.services.greetd.serviceConfig.Type = lib.mkForce "simple";

  # nwg-hello solo busca plantillas propias en /etc/nwg-hello/
  environment.etc."nwg-hello/tema.glade".source = plantillaGreeter;

  # Hyprland necesita un HOME escribible; nwg-hello recuerda el último usuario y sesión
  users.users.greeter = {
    home = "/var/lib/greeter";
    createHome = true;
  };
  systemd.tmpfiles.rules = [
    "d /var/cache/nwg-hello 0755 greeter greeter - -"
    "f /var/cache/nwg-hello/cache.json 0644 greeter greeter - {}"
  ];

  # --- CURSOR (mismo tema en toda la sesión) ---
  environment.variables = {
    XCURSOR_THEME = tema.CURSOR;
    XCURSOR_SIZE = tema.CURSOR_TAMANO;
    HYPRCURSOR_THEME = tema.CURSOR;
    HYPRCURSOR_SIZE = tema.CURSOR_TAMANO;
  };
}
