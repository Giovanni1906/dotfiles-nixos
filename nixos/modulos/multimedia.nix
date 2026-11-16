# =============================================================================
# MULTIMEDIA: Creación, edición y procesamiento de contenido
# =============================================================================
# Módulo opcional. Agrupa todas las herramientas creativas y de producción:
#   - Descarga de videos/música (yt-dlp)       → SUPER + D
#   - Conversión de formatos (ffmpeg-full)
#   - Gestión y recorte de imágenes            → SUPER + I
#   - Voz Limpia IA + Comparador A/B (GTK3)    → SUPER + A
#     DeepFilterNet 3 (48 kHz) + RNNoise + Puerta anti-murmullos + Master -16 LUFS

{ config, lib, pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    yt-dlp         # Descargar videos/música de YouTube y más de 1000 sitios
    ffmpeg-full    # Conversión multimedia + filtros de audio (arnndn, afftdn, loudnorm) y video
    sox            # Utilidades de audio por línea de comandos (stats, trim, convert)
    uv             # Gestor de entornos Python para NixOS

    # App GTK3: Descargador y conversor multimedia (yt-dlp + ffmpeg) — SUPER + D
    (let
      multimediaPython = python3.withPackages (ps: [ ps.pygobject3 ]);
    in writeShellScriptBin "multimedia" ''
      export GDK_BACKEND=wayland
      export GI_TYPELIB_PATH="${lib.makeSearchPath "lib/girepository-1.0" [
        glib.out
        pango.out
        gtk3
        gdk-pixbuf
        atk
        harfbuzz
        gobject-introspection
      ]}"
      export XDG_DATA_DIRS="${gsettings-desktop-schemas}/share/gsettings-schemas/${gsettings-desktop-schemas.name}:${gtk3}/share/gsettings-schemas/${gtk3.name}''${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
      exec ${multimediaPython}/bin/python3 "$HOME/dotfiles/utils/multimedia.py"
    '')

    # App GTK3: Optimizar, redimensionar, recortar y gestionar imágenes — SUPER + I
    (let
      optimizarImagenesPython = python3.withPackages (ps: [ ps.pygobject3 ]);
    in writeShellScriptBin "optimizar-imagenes" ''
      export GDK_BACKEND=wayland
      export GI_TYPELIB_PATH="${lib.makeSearchPath "lib/girepository-1.0" [
        glib.out
        pango.out
        gtk3
        gdk-pixbuf
        atk
        harfbuzz
        gobject-introspection
      ]}"
      export XDG_DATA_DIRS="${gsettings-desktop-schemas}/share/gsettings-schemas/${gsettings-desktop-schemas.name}:${gtk3}/share/gsettings-schemas/${gtk3.name}''${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
      exec ${optimizarImagenesPython}/bin/python3 "$HOME/dotfiles/utils/optimizar-imagenes.py"
    '')

    # App GTK3: Limpieza neuronal de voz, aislamiento vocal y comparador A/B — SUPER + A
    (let
      vozLimpiaPython = python3.withPackages (ps: [ ps.pygobject3 ps.pycairo ]);
    in writeShellScriptBin "voz-limpia-bin" ''
      export GDK_BACKEND=wayland
      export GI_TYPELIB_PATH="${lib.makeSearchPath "lib/girepository-1.0" [
        glib.out
        pango.out
        gtk3
        gdk-pixbuf
        atk
        harfbuzz
        gobject-introspection
      ]}"
      export XDG_DATA_DIRS="${gsettings-desktop-schemas}/share/gsettings-schemas/${gsettings-desktop-schemas.name}:${gtk3}/share/gsettings-schemas/${gtk3.name}''${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
      exec ${vozLimpiaPython}/bin/python3 "$HOME/dotfiles/utils/voz-limpia.py" "$@"
    '')
  ];

  environment.shellAliases = {
    voz-limpia = "~/dotfiles/utils/voz-limpia.sh";
  };
}
