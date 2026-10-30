#!/usr/bin/env python3
# Utilidad gráfica para descargar videos/música (yt-dlp) y convertir formatos (ffmpeg).
# Se abre o cierra con SUPER + D (utils/multimedia.sh) y toma la paleta de tema/tema.conf.

import os
import re
import shutil
import signal
import subprocess
import threading
from pathlib import Path
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango

GLib.set_prgname("multimedia-util")
GLib.set_application_name("Multimedia")

HOME = Path.home()
TEMA = HOME / "dotfiles/tema/tema.conf"

TEMA_BASE = {
    "ACENTO": "#3399cc",
    "SECUNDARIO": "#cba6f7",
    "FONDO": "#0a1e3c",
    "SUPERFICIE": "#133e7c",
    "TEXTO": "#cdd6f4",
    "TEXTO_TENUE": "#6c7086",
    "URGENTE": "#f38ba8",
    "EXITO": "#a6e3a1",
    "AVISO": "#f9e2af",
    "RADIO": "10",
    "BORDE": "2",
    "FUENTE": "JetBrainsMono Nerd Font",
    "OPACIDAD_MENU": "0.95",
}

FORMATOS_VIDEO_DL = [
    ("mp4", "MP4 · Compatible universal"),
    ("mkv", "MKV · Matroska"),
    ("webm", "WebM · Original sin recodificar"),
]

CALIDADES_VIDEO_DL = [
    ("best", "Mejor calidad disponible"),
    ("1080", "1080p (Full HD)"),
    ("720", "720p (HD)"),
    ("480", "480p (Ligero)"),
]

FORMATOS_AUDIO_DL = [
    ("mp3", "MP3 · Universal"),
    ("m4a", "M4A · AAC alta eficiencia"),
    ("flac", "FLAC · Sin pérdida"),
    ("wav", "WAV · Sin comprimir"),
    ("opus", "Opus · Alta calidad comprimida"),
]

CALIDADES_AUDIO_DL = [
    ("0", "Mejor calidad (320 kbps / VBR 0)"),
    ("192K", "Alta (192 kbps)"),
    ("128K", "Estándar (128 kbps)"),
]

FORMATOS_CONV_VIDEO = [
    ("mp4", "MP4 (H.264 + AAC · Universal)"),
    ("mkv", "MKV (Matroska)"),
    ("webm", "WebM (VP9 + Opus)"),
    ("mov", "MOV (QuickTime)"),
    ("avi", "AVI"),
    ("gif", "GIF animado"),
]

FORMATOS_CONV_AUDIO = [
    ("mp3", "MP3 (Universal)"),
    ("m4a", "M4A (AAC)"),
    ("wav", "WAV (Sin pérdida)"),
    ("flac", "FLAC (Sin pérdida comprimido)"),
    ("opus", "Opus"),
    ("ogg", "OGG Vorbis"),
]

MODOS_CONV = [
    ("equilibrado", "Equilibrado (rápido y buena calidad)"),
    ("alta", "Alta calidad"),
    ("ligero", "Tamaño reducido (comprimir)"),
    ("copy", "Copia directa sin recodificar (-c copy · instantáneo)"),
]


def sin_comentario(linea):
    entre_comillas = False
    for indice, caracter in enumerate(linea):
        if caracter == '"':
            entre_comillas = not entre_comillas
        elif caracter == "#" and not entre_comillas:
            return linea[:indice]
    return linea


def leer_tema():
    valores = dict(TEMA_BASE)
    if TEMA.is_file():
        for linea in TEMA.read_text(encoding="utf-8").splitlines():
            linea = sin_comentario(linea).strip()
            if "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            valores[clave.strip()] = valor.strip().strip('"')
    return valores


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    if len(h) != 6:
        h = "3399cc"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def carpeta_xdg(nombre, por_defecto):
    ruta = HOME / por_defecto
    user_dirs = HOME / ".config/user-dirs.dirs"
    if user_dirs.is_file():
        patron = f'XDG_{nombre}_DIR="'
        for linea in user_dirs.read_text(encoding="utf-8", errors="ignore").splitlines():
            linea = linea.strip()
            if linea.startswith(patron) and linea.endswith('"'):
                valor = linea[len(patron):-1].replace("$HOME", str(HOME))
                candidata = Path(valor)
                if candidata.is_dir():
                    return candidata
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def notificar(titulo, cuerpo="", critico=False):
    cmd = ["notify-send", "-a", "Multimedia"]
    if critico:
        cmd += ["-u", "critical"]
    cmd += [titulo, cuerpo]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def leer_portapapeles():
    try:
        res = subprocess.run(
            ["wl-paste", "--no-newline"],
            capture_output=True,
            text=True,
            timeout=1.0,
        )
        if res.returncode == 0 and res.stdout:
            return res.stdout.strip()
    except Exception:
        pass
    return ""


def duracion_segundos(archivo):
    try:
        res = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(archivo),
            ],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception:
        pass
    return 0.0


def formatear_tamano(num_bytes):
    for unidad in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unidad}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def formatear_tiempo(segundos):
    if segundos <= 0:
        return "desconocida"
    m, s = divmod(int(segundos), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class MultimediaApp:
    def __init__(self):
        self.tema = leer_tema()
        self.dir_descargas = carpeta_xdg("DOWNLOAD", "Descargas")
        self.dir_musica = carpeta_xdg("MUSIC", "Música")
        self.dir_videos = carpeta_xdg("VIDEOS", "Vídeos")

        self.carpeta_dl = self.dir_descargas
        self.modo_dl = "video"  # "video" | "audio"

        self.archivo_origen = None
        self.duracion_origen = 0.0
        self.carpeta_conv = None  # None = misma carpeta del archivo
        self.tipo_conv = "video"  # "video" | "audio"

        self.proceso_activo = None
        self.cancelado = False
        self.ocupado = False
        self.ultima_carpeta_abrible = self.dir_descargas

        self._construir_ventana()
        self._auto_pegar_url()

    def _aplicar_css(self):
        t = self.tema
        fondo = rgba(t["FONDO"], "0.98")
        superficie = rgba(t["SUPERFICIE"], "0.90")
        superficie_hover = t["SUPERFICIE"]
        acento_suave = rgba(t["ACENTO"], "0.28")
        borde_suave = rgba(t["ACENTO"], "0.45")
        fuente = t["FUENTE"]

        css = f"""
        window, .contenedor-principal {{
            background-color: {fondo};
            color: {t["TEXTO"]};
        }}
        * {{
            font-family: "{fuente}";
            color: {t["TEXTO"]};
        }}
        .contenedor-principal {{
            padding: 16px 18px 16px 18px;
        }}
        .titulo-app {{
            font-size: 15px;
            font-weight: 700;
            color: {t["ACENTO"]};
        }}
        .subtitulo-app {{
            font-size: 11px;
            color: {t["TEXTO_TENUE"]};
        }}
        .etiqueta-seccion {{
            font-size: 11px;
            font-weight: 700;
            color: {t["SECUNDARIO"]};
        }}
        .info-archivo {{
            font-size: 11px;
            color: {t["TEXTO_TENUE"]};
        }}
        .estado-texto {{
            font-size: 11px;
            color: {t["TEXTO"]};
        }}
        .estado-exito {{
            font-size: 11px;
            font-weight: 700;
            color: {t["EXITO"]};
        }}
        .estado-error {{
            font-size: 11px;
            font-weight: 700;
            color: {t["URGENTE"]};
        }}
        entry {{
            background-color: {superficie};
            background-image: none;
            border: 1px solid {borde_suave};
            border-radius: 8px;
            padding: 6px 10px;
            color: {t["TEXTO"]};
            caret-color: {t["ACENTO"]};
        }}
        entry:focus {{
            border-color: {t["ACENTO"]};
        }}
        button {{
            background-image: none;
            background-color: {superficie};
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 6px 12px;
            box-shadow: none;
            outline: none;
        }}
        button:hover {{
            background-color: {superficie_hover};
            border-color: {borde_suave};
        }}
        button.tab-btn {{
            padding: 8px 14px;
            font-weight: 700;
            border-radius: 8px;
        }}
        button.tab-activa, button.chip-activo {{
            background-color: {acento_suave};
            border: 1px solid {t["ACENTO"]};
        }}
        button.tab-activa label, button.chip-activo label {{
            color: {t["ACENTO"]};
            font-weight: 700;
        }}
        button.accion-principal {{
            background-color: {t["ACENTO"]};
            border-color: {t["ACENTO"]};
            padding: 8px 18px;
            font-weight: 700;
        }}
        button.accion-principal label {{
            color: {t["FONDO"]};
            font-weight: 700;
        }}
        button.accion-principal:hover {{
            background-color: {t["SECUNDARIO"]};
            border-color: {t["SECUNDARIO"]};
        }}
        button.boton-peligro {{
            background-color: {rgba(t["URGENTE"], "0.22")};
            border: 1px solid {t["URGENTE"]};
        }}
        button.boton-peligro label {{
            color: {t["URGENTE"]};
            font-weight: 700;
        }}
        button.cerrar-btn {{
            background-color: transparent;
            padding: 4px 8px;
        }}
        button.cerrar-btn:hover {{
            background-color: {rgba(t["URGENTE"], "0.25")};
        }}
        combobox button.combo {{
            background-color: {superficie};
            border: 1px solid {borde_suave};
            border-radius: 8px;
            padding: 5px 10px;
        }}
        checkbutton label {{
            font-size: 12px;
            color: {t["TEXTO"]};
        }}
        checkbutton check {{
            background-color: {superficie};
            border: 1px solid {borde_suave};
            border-radius: 4px;
            min-width: 16px;
            min-height: 16px;
        }}
        checkbutton check:checked {{
            background-color: {t["ACENTO"]};
            border-color: {t["ACENTO"]};
            color: {t["FONDO"]};
        }}
        progressbar trough {{
            background-color: {superficie};
            border-radius: 6px;
            min-height: 10px;
        }}
        progressbar progress {{
            background-color: {t["ACENTO"]};
            border-radius: 6px;
            min-height: 10px;
        }}
        separator {{
            background-color: {borde_suave};
            min-height: 1px;
        }}
        .caja-drop {{
            background-color: {superficie};
            border: 1px dashed {borde_suave};
            border-radius: 8px;
            padding: 10px 12px;
        }}
        """
        proveedor = Gtk.CssProvider()
        proveedor.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            proveedor,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _construir_ventana(self):
        self.win = Gtk.Window(title="Multimedia")
        self.win.set_default_size(620, 520)
        self.win.set_resizable(False)
        self.win.set_decorated(False)
        visual = self.win.get_screen().get_rgba_visual()
        if visual is not None:
            self.win.set_visual(visual)

        self._aplicar_css()

        raiz = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        raiz.get_style_context().add_class("contenedor-principal")
        self.win.add(raiz)

        # --- CABECERA ---
        cabecera = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        raiz.pack_start(cabecera, False, False, 0)

        caja_titulo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_titulo = Gtk.Label(label="󰇚  Multimedia")
        lbl_titulo.set_halign(Gtk.Align.START)
        lbl_titulo.get_style_context().add_class("titulo-app")
        caja_titulo.pack_start(lbl_titulo, False, False, 0)

        lbl_sub = Gtk.Label(label="Descargar video/música (yt-dlp) y convertir formatos (ffmpeg)")
        lbl_sub.set_halign(Gtk.Align.START)
        lbl_sub.get_style_context().add_class("subtitulo-app")
        caja_titulo.pack_start(lbl_sub, False, False, 0)
        cabecera.pack_start(caja_titulo, True, True, 0)

        btn_cerrar = Gtk.Button(label="✕")
        btn_cerrar.set_tooltip_text("Cerrar (Escape)")
        btn_cerrar.get_style_context().add_class("cerrar-btn")
        btn_cerrar.connect("clicked", lambda *_: self.cerrar())
        cabecera.pack_end(btn_cerrar, False, False, 0)

        # --- PESTAÑAS ---
        barra_tabs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        barra_tabs.set_homogeneous(True)
        raiz.pack_start(barra_tabs, False, False, 0)

        self.btn_tab_dl = Gtk.Button(label="󰇚   Descargar de Internet")
        self.btn_tab_dl.get_style_context().add_class("tab-btn")
        self.btn_tab_dl.get_style_context().add_class("tab-activa")
        self.btn_tab_dl.connect("clicked", lambda *_: self._cambiar_pestana("descargar"))
        barra_tabs.pack_start(self.btn_tab_dl, True, True, 0)

        self.btn_tab_conv = Gtk.Button(label="🔁   Convertir Archivo Local")
        self.btn_tab_conv.get_style_context().add_class("tab-btn")
        self.btn_tab_conv.connect("clicked", lambda *_: self._cambiar_pestana("convertir"))
        barra_tabs.pack_start(self.btn_tab_conv, True, True, 0)

        raiz.pack_start(Gtk.Separator(), False, False, 0)

        # --- CONTENIDO DE PESTAÑAS (STACK) ---
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(160)
        raiz.pack_start(self.stack, True, True, 0)

        self.stack.add_named(self._construir_tab_descargar(), "descargar")
        self.stack.add_named(self._construir_tab_convertir(), "convertir")

        raiz.pack_start(Gtk.Separator(), False, False, 0)

        # --- BARRA DE PROGRESO Y ACCIONES ---
        zona_inferior = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        raiz.pack_start(zona_inferior, False, False, 0)

        self.barra_progreso = Gtk.ProgressBar()
        self.barra_progreso.set_fraction(0.0)
        zona_inferior.pack_start(self.barra_progreso, False, False, 0)

        fila_acciones = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        zona_inferior.pack_start(fila_acciones, False, False, 0)

        self.lbl_estado = Gtk.Label(label="Listo · Pega un enlace o elige un archivo")
        self.lbl_estado.set_halign(Gtk.Align.START)
        self.lbl_estado.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_estado.get_style_context().add_class("estado-texto")
        fila_acciones.pack_start(self.lbl_estado, True, True, 0)

        self.btn_abrir_carpeta = Gtk.Button(label="󰉋  Abrir carpeta")
        self.btn_abrir_carpeta.connect("clicked", self._abrir_carpeta_actual)
        fila_acciones.pack_start(self.btn_abrir_carpeta, False, False, 0)

        self.btn_cancelar = Gtk.Button(label="Stop  Cancelar")
        self.btn_cancelar.set_label("✕  Cancelar")
        self.btn_cancelar.get_style_context().add_class("boton-peligro")
        self.btn_cancelar.connect("clicked", self._cancelar_proceso)
        self.btn_cancelar.set_no_show_all(True)
        self.btn_cancelar.hide()
        fila_acciones.pack_start(self.btn_cancelar, False, False, 0)

        self.btn_ejecutar = Gtk.Button(label="󰇚  Descargar")
        self.btn_ejecutar.get_style_context().add_class("accion-principal")
        self.btn_ejecutar.connect("clicked", self._ejecutar_accion)
        fila_acciones.pack_start(self.btn_ejecutar, False, False, 0)

        self.win.connect("key-press-event", self._al_pulsar_tecla)
        self.win.connect("destroy", self._al_destruir)

    # =========================================================================
    # PESTAÑA 1: DESCARGAR (yt-dlp)
    # =========================================================================
    def _construir_tab_descargar(self):
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # 1. URL
        caja.pack_start(self._etiqueta_seccion("ENLACE DEL VIDEO O CANCIÓN (YOUTUBE / INTERNET)"), False, False, 0)
        fila_url = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        caja.pack_start(fila_url, False, False, 0)

        self.entrada_url = Gtk.Entry()
        self.entrada_url.set_placeholder_text("https://www.youtube.com/watch?v=...")
        self.entrada_url.connect("activate", self._ejecutar_accion)
        fila_url.pack_start(self.entrada_url, True, True, 0)

        btn_pegar = Gtk.Button(label="󰆒  Pegar")
        btn_pegar.set_tooltip_text("Pegar enlace desde el portapapeles")
        btn_pegar.connect("clicked", self._pegar_portapapeles)
        fila_url.pack_start(btn_pegar, False, False, 0)

        btn_limpiar = Gtk.Button(label="✕")
        btn_limpiar.set_tooltip_text("Limpiar enlace")
        btn_limpiar.connect("clicked", lambda *_: self.entrada_url.set_text(""))
        fila_url.pack_start(btn_limpiar, False, False, 0)

        # 2. Tipo (Video vs Solo Audio)
        caja.pack_start(self._etiqueta_seccion("QUÉ DESCARGAR"), False, False, 0)
        fila_tipo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fila_tipo.set_homogeneous(True)
        caja.pack_start(fila_tipo, False, False, 0)

        self.btn_modo_video = Gtk.Button(label="󰕧   Video completo")
        self.btn_modo_video.get_style_context().add_class("chip-activo")
        self.btn_modo_video.connect("clicked", lambda *_: self._cambiar_modo_dl("video"))
        fila_tipo.pack_start(self.btn_modo_video, True, True, 0)

        self.btn_modo_audio = Gtk.Button(label="󰎆   Solo Audio / Música")
        self.btn_modo_audio.connect("clicked", lambda *_: self._cambiar_modo_dl("audio"))
        fila_tipo.pack_start(self.btn_modo_audio, True, True, 0)

        # 3. Formato y Calidad
        fila_fmt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        fila_fmt.set_homogeneous(True)
        caja.pack_start(fila_fmt, False, False, 0)

        col_fmt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_fmt.pack_start(self._etiqueta_seccion("FORMATO"), False, False, 0)
        self.combo_formato_dl = Gtk.ComboBoxText()
        col_fmt.pack_start(self.combo_formato_dl, False, False, 0)
        fila_fmt.pack_start(col_fmt, True, True, 0)

        col_cal = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_cal.pack_start(self._etiqueta_seccion("CALIDAD"), False, False, 0)
        self.combo_calidad_dl = Gtk.ComboBoxText()
        col_cal.pack_start(self.combo_calidad_dl, False, False, 0)
        fila_fmt.pack_start(col_cal, True, True, 0)

        self._rellenar_combos_dl()

        # 4. Opciones adicionales
        fila_checks = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        caja.pack_start(fila_checks, False, False, 0)

        self.chk_no_playlist = Gtk.CheckButton(label="Solo este video (ignorar playlist)")
        self.chk_no_playlist.set_active(True)
        fila_checks.pack_start(self.chk_no_playlist, False, False, 0)

        self.chk_metadatos = Gtk.CheckButton(label="Incrustar metadatos y miniatura")
        self.chk_metadatos.set_active(True)
        fila_checks.pack_start(self.chk_metadatos, False, False, 0)

        # 5. Carpeta de destino
        caja.pack_start(self._etiqueta_seccion("CARPETA DE DESTINO"), False, False, 0)
        fila_dest = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        caja.pack_start(fila_dest, False, False, 0)

        self.lbl_carpeta_dl = Gtk.Entry()
        self.lbl_carpeta_dl.set_editable(False)
        self.lbl_carpeta_dl.set_text(str(self.carpeta_dl))
        fila_dest.pack_start(self.lbl_carpeta_dl, True, True, 0)

        for icono_texto, ruta in (
            ("Descargas", self.dir_descargas),
            ("Música", self.dir_musica),
            ("Vídeos", self.dir_videos),
        ):
            btn = Gtk.Button(label=icono_texto)
            btn.connect("clicked", lambda _b, r=ruta: self._fijar_carpeta_dl(r))
            fila_dest.pack_start(btn, False, False, 0)

        btn_elegir_dir = Gtk.Button(label="󰉋")
        btn_elegir_dir.set_tooltip_text("Elegir otra carpeta...")
        btn_elegir_dir.connect("clicked", self._elegir_carpeta_dl_dialogo)
        fila_dest.pack_start(btn_elegir_dir, False, False, 0)

        return caja

    # =========================================================================
    # PESTAÑA 2: CONVERTIR (ffmpeg)
    # =========================================================================
    def _construir_tab_convertir(self):
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # 1. Archivo de entrada
        caja.pack_start(self._etiqueta_seccion("ARCHIVO DE ORIGEN (ARRASTRA AQUÍ O SELECCIONA)"), False, False, 0)

        caja_archivo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        caja_archivo.get_style_context().add_class("caja-drop")
        caja.pack_start(caja_archivo, False, False, 0)

        # Soporte para arrastrar y soltar archivos desde Thunar
        caja_archivo.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        caja_archivo.drag_dest_add_uri_targets()
        caja_archivo.connect("drag-data-received", self._al_soltar_archivo)

        fila_arch = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        caja_archivo.pack_start(fila_arch, False, False, 0)

        self.entrada_archivo = Gtk.Entry()
        self.entrada_archivo.set_editable(False)
        self.entrada_archivo.set_placeholder_text("Ningún archivo seleccionado...")
        fila_arch.pack_start(self.entrada_archivo, True, True, 0)

        btn_elegir_arch = Gtk.Button(label="󰉋  Elegir archivo...")
        btn_elegir_arch.connect("clicked", self._elegir_archivo_origen)
        fila_arch.pack_start(btn_elegir_arch, False, False, 0)

        self.lbl_info_archivo = Gtk.Label(label="Formatos soportados: mp4, mkv, webm, mov, avi, mp3, m4a, wav, flac, ogg, opus...")
        self.lbl_info_archivo.set_halign(Gtk.Align.START)
        self.lbl_info_archivo.get_style_context().add_class("info-archivo")
        caja_archivo.pack_start(self.lbl_info_archivo, False, False, 0)

        # 2. Tipo de salida (Video vs Audio)
        caja.pack_start(self._etiqueta_seccion("CONVERTIR A"), False, False, 0)
        fila_tipo_conv = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fila_tipo_conv.set_homogeneous(True)
        caja.pack_start(fila_tipo_conv, False, False, 0)

        self.btn_conv_video = Gtk.Button(label="󰕧   Formato de Video / GIF")
        self.btn_conv_video.get_style_context().add_class("chip-activo")
        self.btn_conv_video.connect("clicked", lambda *_: self._cambiar_tipo_conv("video"))
        fila_tipo_conv.pack_start(self.btn_conv_video, True, True, 0)

        self.btn_conv_audio = Gtk.Button(label="󰎆   Formato de Audio (o extraer audio)")
        self.btn_conv_audio.connect("clicked", lambda *_: self._cambiar_tipo_conv("audio"))
        fila_tipo_conv.pack_start(self.btn_conv_audio, True, True, 0)

        # 3. Formato de salida y Modo de conversión
        fila_opts_conv = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        fila_opts_conv.set_homogeneous(True)
        caja.pack_start(fila_opts_conv, False, False, 0)

        col_fmt_c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_fmt_c.pack_start(self._etiqueta_seccion("FORMATO DE SALIDA"), False, False, 0)
        self.combo_formato_conv = Gtk.ComboBoxText()
        col_fmt_c.pack_start(self.combo_formato_conv, False, False, 0)
        fila_opts_conv.pack_start(col_fmt_c, True, True, 0)

        col_modo_c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_modo_c.pack_start(self._etiqueta_seccion("CALIDAD / VELOCIDAD"), False, False, 0)
        self.combo_modo_conv = Gtk.ComboBoxText()
        for clave, texto in MODOS_CONV:
            self.combo_modo_conv.append(clave, texto)
        self.combo_modo_conv.set_active(0)
        col_modo_c.pack_start(self.combo_modo_conv, False, False, 0)
        fila_opts_conv.pack_start(col_modo_c, True, True, 0)

        self._rellenar_combos_conv()

        # 4. Carpeta de salida
        caja.pack_start(self._etiqueta_seccion("DÓNDE GUARDAR EL ARCHIVO CONVERTIDO"), False, False, 0)
        fila_dest_c = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        caja.pack_start(fila_dest_c, False, False, 0)

        self.lbl_carpeta_conv = Gtk.Entry()
        self.lbl_carpeta_conv.set_editable(False)
        self.lbl_carpeta_conv.set_text("Misma carpeta que el archivo original")
        fila_dest_c.pack_start(self.lbl_carpeta_conv, True, True, 0)

        btn_misma = Gtk.Button(label="Original")
        btn_misma.set_tooltip_text("Guardar junto al archivo original")
        btn_misma.connect("clicked", lambda *_: self._fijar_carpeta_conv(None))
        fila_dest_c.pack_start(btn_misma, False, False, 0)

        btn_elegir_conv_dir = Gtk.Button(label="󰉋  Otra...")
        btn_elegir_conv_dir.connect("clicked", self._elegir_carpeta_conv_dialogo)
        fila_dest_c.pack_start(btn_elegir_conv_dir, False, False, 0)

        return caja

    def _etiqueta_seccion(self, texto):
        lbl = Gtk.Label(label=texto)
        lbl.set_halign(Gtk.Align.START)
        lbl.get_style_context().add_class("etiqueta-seccion")
        return lbl

    # =========================================================================
    # INTERACCIÓN Y CAMBIOS DE ESTADO DE LA INTERFAZ
    # =========================================================================
    def _cambiar_pestana(self, nombre):
        self.stack.set_visible_child_name(nombre)
        ctx_dl = self.btn_tab_dl.get_style_context()
        ctx_cv = self.btn_tab_conv.get_style_context()
        if nombre == "descargar":
            ctx_dl.add_class("tab-activa")
            ctx_cv.remove_class("tab-activa")
            self.btn_ejecutar.set_label("󰇚  Descargar")
            self.ultima_carpeta_abrible = self.carpeta_dl
        else:
            ctx_cv.add_class("tab-activa")
            ctx_dl.remove_class("tab-activa")
            self.btn_ejecutar.set_label("🔁  Convertir")
            if self.carpeta_conv:
                self.ultima_carpeta_abrible = self.carpeta_conv
            elif self.archivo_origen:
                self.ultima_carpeta_abrible = self.archivo_origen.parent

    def _cambiar_modo_dl(self, modo):
        self.modo_dl = modo
        ctx_v = self.btn_modo_video.get_style_context()
        ctx_a = self.btn_modo_audio.get_style_context()
        if modo == "video":
            ctx_v.add_class("chip-activo")
            ctx_a.remove_class("chip-activo")
            if self.carpeta_dl == self.dir_musica:
                self._fijar_carpeta_dl(self.dir_descargas)
        else:
            ctx_a.add_class("chip-activo")
            ctx_v.remove_class("chip-activo")
            if self.carpeta_dl == self.dir_videos:
                self._fijar_carpeta_dl(self.dir_musica)
        self._rellenar_combos_dl()

    def _rellenar_combos_dl(self):
        self.combo_formato_dl.remove_all()
        self.combo_calidad_dl.remove_all()
        if self.modo_dl == "video":
            for k, v in FORMATOS_VIDEO_DL:
                self.combo_formato_dl.append(k, v)
            for k, v in CALIDADES_VIDEO_DL:
                self.combo_calidad_dl.append(k, v)
        else:
            for k, v in FORMATOS_AUDIO_DL:
                self.combo_formato_dl.append(k, v)
            for k, v in CALIDADES_AUDIO_DL:
                self.combo_calidad_dl.append(k, v)
        self.combo_formato_dl.set_active(0)
        self.combo_calidad_dl.set_active(0)

    def _cambiar_tipo_conv(self, tipo):
        self.tipo_conv = tipo
        ctx_v = self.btn_conv_video.get_style_context()
        ctx_a = self.btn_conv_audio.get_style_context()
        if tipo == "video":
            ctx_v.add_class("chip-activo")
            ctx_a.remove_class("chip-activo")
        else:
            ctx_a.add_class("chip-activo")
            ctx_v.remove_class("chip-activo")
        self._rellenar_combos_conv()

    def _rellenar_combos_conv(self):
        self.combo_formato_conv.remove_all()
        lista = FORMATOS_CONV_VIDEO if self.tipo_conv == "video" else FORMATOS_CONV_AUDIO
        for k, v in lista:
            self.combo_formato_conv.append(k, v)
        self.combo_formato_conv.set_active(0)

    def _fijar_carpeta_dl(self, ruta):
        self.carpeta_dl = Path(ruta)
        self.lbl_carpeta_dl.set_text(str(self.carpeta_dl))
        self.ultima_carpeta_abrible = self.carpeta_dl

    def _fijar_carpeta_conv(self, ruta):
        self.carpeta_conv = Path(ruta) if ruta else None
        if self.carpeta_conv:
            self.lbl_carpeta_conv.set_text(str(self.carpeta_conv))
            self.ultima_carpeta_abrible = self.carpeta_conv
        else:
            self.lbl_carpeta_conv.set_text("Misma carpeta que el archivo original")
            if self.archivo_origen:
                self.ultima_carpeta_abrible = self.archivo_origen.parent

    def _auto_pegar_url(self):
        texto = leer_portapapeles()
        if texto and len(texto) < 600 and re.match(r"^https?://\S+$", texto):
            self.entrada_url.set_text(texto)
            self._mostrar_estado("Enlace detectado automáticamente del portapapeles")

    def _pegar_portapapeles(self, *_args):
        texto = leer_portapapeles()
        if texto:
            primera_linea = texto.splitlines()[0].strip()
            self.entrada_url.set_text(primera_linea)
            self._mostrar_estado("Enlace pegado desde el portapapeles")
        else:
            self._mostrar_estado("El portapapeles está vacío", error=True)

    def _elegir_carpeta_dl_dialogo(self, *_args):
        dlg = Gtk.FileChooserDialog(
            title="Elegir carpeta de descarga",
            parent=self.win,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dlg.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Seleccionar", Gtk.ResponseType.OK,
        )
        dlg.set_current_folder(str(self.carpeta_dl))
        if dlg.run() == Gtk.ResponseType.OK:
            self._fijar_carpeta_dl(Path(dlg.get_filename()))
        dlg.destroy()

    def _elegir_carpeta_conv_dialogo(self, *_args):
        dlg = Gtk.FileChooserDialog(
            title="Elegir carpeta de destino",
            parent=self.win,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dlg.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Seleccionar", Gtk.ResponseType.OK,
        )
        base = self.carpeta_conv or (self.archivo_origen.parent if self.archivo_origen else self.dir_descargas)
        dlg.set_current_folder(str(base))
        if dlg.run() == Gtk.ResponseType.OK:
            self._fijar_carpeta_conv(Path(dlg.get_filename()))
        dlg.destroy()

    def _elegir_archivo_origen(self, *_args):
        dlg = Gtk.FileChooserDialog(
            title="Seleccionar archivo multimedia",
            parent=self.win,
            action=Gtk.FileChooserAction.OPEN,
        )
        dlg.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Abrir", Gtk.ResponseType.OK,
        )
        dlg.set_current_folder(str(self.ultima_carpeta_abrible))

        filtro_media = Gtk.FileFilter()
        filtro_media.set_name("Archivos de Video y Audio")
        for patron in (
            "*.mp4", "*.mkv", "*.webm", "*.mov", "*.avi", "*.flv", "*.wmv", "*.m4v", "*.ts",
            "*.mp3", "*.m4a", "*.wav", "*.flac", "*.ogg", "*.opus", "*.aac", "*.wma", "*.gif",
        ):
            filtro_media.add_pattern(patron)
            filtro_media.add_pattern(patron.upper())
        dlg.add_filter(filtro_media)

        filtro_todos = Gtk.FileFilter()
        filtro_todos.set_name("Todos los archivos")
        filtro_todos.add_pattern("*")
        dlg.add_filter(filtro_todos)

        if dlg.run() == Gtk.ResponseType.OK:
            self._cargar_archivo_origen(Path(dlg.get_filename()))
        dlg.destroy()

    def _al_soltar_archivo(self, _widget, _context, _x, _y, data, _info, _time):
        uris = data.get_uris()
        if not uris:
            return
        parsed = urlparse(uris[0])
        if parsed.scheme == "file":
            ruta = Path(unquote(parsed.path))
            if ruta.is_file():
                self._cargar_archivo_origen(ruta)

    def _cargar_archivo_origen(self, ruta: Path):
        self.archivo_origen = ruta
        self.entrada_archivo.set_text(str(ruta))
        self.duracion_origen = duracion_segundos(ruta)
        try:
            tamano = formatear_tamano(ruta.stat().st_size)
        except Exception:
            tamano = "?"
        ext = ruta.suffix.lower() or "sin extensión"
        dur_txt = formatear_tiempo(self.duracion_origen)
        self.lbl_info_archivo.set_text(
            f"Archivo: {ruta.name}  ·  Formato actual: {ext}  ·  Duración: {dur_txt}  ·  Tamaño: {tamano}"
        )
        if not self.carpeta_conv:
            self.ultima_carpeta_abrible = ruta.parent
        self._mostrar_estado(f"Archivo listo para convertir: {ruta.name}")

    def _abrir_carpeta_actual(self, *_args):
        carpeta = self.ultima_carpeta_abrible
        if not carpeta or not Path(carpeta).exists():
            carpeta = self.dir_descargas
        try:
            subprocess.Popen(
                ["xdg-open", str(carpeta)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            self._mostrar_estado(f"No se pudo abrir la carpeta: {e}", error=True)

    def _mostrar_estado(self, texto, exito=False, error=False):
        ctx = self.lbl_estado.get_style_context()
        ctx.remove_class("estado-texto")
        ctx.remove_class("estado-exito")
        ctx.remove_class("estado-error")
        if exito:
            ctx.add_class("estado-exito")
        elif error:
            ctx.add_class("estado-error")
        else:
            ctx.add_class("estado-texto")
        self.lbl_estado.set_text(texto)

    def _fijar_ocupado(self, ocupado: bool):
        self.ocupado = ocupado
        self.btn_ejecutar.set_sensitive(not ocupado)
        self.btn_tab_dl.set_sensitive(not ocupado)
        self.btn_tab_conv.set_sensitive(not ocupado)
        if ocupado:
            self.btn_cancelar.show()
        else:
            self.btn_cancelar.hide()

    # =========================================================================
    # EJECUCIÓN DE DESCARGA (yt-dlp) Y CONVERSIÓN (ffmpeg)
    # =========================================================================
    def _ejecutar_accion(self, *_args):
        if self.ocupado:
            return
        if self.stack.get_visible_child_name() == "descargar":
            self._iniciar_descarga()
        else:
            self._iniciar_conversion()

    def _iniciar_descarga(self):
        url = self.entrada_url.get_text().strip()
        if not url:
            self._mostrar_estado("Escribe o pega un enlace primero", error=True)
            self.entrada_url.grab_focus()
            return

        if not shutil.which("yt-dlp"):
            self._mostrar_estado("No se encontró yt-dlp en el sistema", error=True)
            return

        formato = self.combo_formato_dl.get_active_id() or "mp4"
        calidad = self.combo_calidad_dl.get_active_id() or "best"
        carpeta = self.carpeta_dl
        carpeta.mkdir(parents=True, exist_ok=True)
        self.ultima_carpeta_abrible = carpeta

        cmd = [
            "yt-dlp",
            "--newline",
            "--progress",
            "-P",
            str(carpeta),
            "-o",
            "%(title)s.%(ext)s",
        ]

        if self.chk_no_playlist.get_active():
            cmd.append("--no-playlist")
        else:
            cmd.append("--yes-playlist")

        if self.chk_metadatos.get_active():
            cmd.append("--embed-metadata")
            if formato in ("mp3", "m4a", "flac", "opus", "mp4", "mkv"):
                cmd.append("--embed-thumbnail")

        if self.modo_dl == "audio":
            cmd += ["-x", "--audio-format", formato, "--audio-quality", calidad]
        else:
            if calidad == "best":
                filtro_v = "bv*+ba/b"
            else:
                filtro_v = f"bv*[height<={calidad}]+ba/b[height<={calidad}]/b"
            cmd += ["-f", filtro_v, "--merge-output-format", formato]

        cmd.append(url)

        self.cancelado = False
        self.barra_progreso.set_fraction(0.0)
        self._fijar_ocupado(True)
        self._mostrar_estado("Conectando y obteniendo información del enlace...")

        hilo = threading.Thread(target=self._hilo_ytdlp, args=(cmd,), daemon=True)
        hilo.start()

    def _hilo_ytdlp(self, cmd):
        re_progreso = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%\s+of\s+\S+\s+at\s+(\S+)\s+ETA\s+(\S+)")
        re_progreso_simple = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")
        ultima_linea_err = ""

        try:
            self.proceso_activo = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid,
            )

            for linea in self.proceso_activo.stdout:
                linea = linea.strip()
                if not linea:
                    continue
                m = re_progreso.search(linea)
                if m:
                    pct = float(m.group(1))
                    vel = m.group(2)
                    eta = m.group(3)
                    GLib.idle_add(
                        self._actualizar_progreso,
                        pct / 100.0,
                        f"Descargando: {pct:.1f}%  ·  {vel}  ·  ETA {eta}",
                    )
                    continue

                m2 = re_progreso_simple.search(linea)
                if m2:
                    pct = float(m2.group(1))
                    GLib.idle_add(
                        self._actualizar_progreso,
                        pct / 100.0,
                        f"Descargando: {pct:.1f}%",
                    )
                    continue

                if linea.startswith("[ExtractAudio]") or linea.startswith("[Merger]") or linea.startswith("[EmbedThumbnail]"):
                    GLib.idle_add(
                        self._actualizar_progreso,
                        0.98,
                        "Procesando formato final con ffmpeg...",
                    )
                elif "ERROR:" in linea:
                    ultima_linea_err = linea.split("ERROR:", 1)[-1].strip()

            rc = self.proceso_activo.wait()
        except Exception as e:
            rc = -1
            ultima_linea_err = str(e)
        finally:
            self.proceso_activo = None

        GLib.idle_add(self._fin_tarea, rc, "Descarga", ultima_linea_err)

    def _iniciar_conversion(self):
        if not self.archivo_origen or not self.archivo_origen.is_file():
            self._mostrar_estado("Selecciona primero un archivo local para convertir", error=True)
            return

        if not shutil.which("ffmpeg"):
            self._mostrar_estado("No se encontró ffmpeg en el sistema", error=True)
            return

        formato_dest = self.combo_formato_conv.get_active_id() or "mp4"
        modo = self.combo_modo_conv.get_active_id() or "equilibrado"
        carpeta_salida = self.carpeta_conv or self.archivo_origen.parent
        carpeta_salida.mkdir(parents=True, exist_ok=True)
        self.ultima_carpeta_abrible = carpeta_salida

        nombre_base = self.archivo_origen.stem
        salida = carpeta_salida / f"{nombre_base}.{formato_dest}"
        if salida.resolve() == self.archivo_origen.resolve() or salida.exists():
            contador = 1
            while True:
                sufijo = "_convertido" if contador == 1 else f"_convertido_{contador}"
                candidato = carpeta_salida / f"{nombre_base}{sufijo}.{formato_dest}"
                if not candidato.exists():
                    salida = candidato
                    break
                contador += 1

        cmd = ["ffmpeg", "-y", "-hide_banner", "-i", str(self.archivo_origen)]

        if self.tipo_conv == "audio":
            cmd.append("-vn")
            if modo == "copy":
                cmd += ["-c:a", "copy"]
            elif formato_dest == "mp3":
                bitrate = "320k" if modo == "alta" else ("128k" if modo == "ligero" else "192k")
                cmd += ["-c:a", "libmp3lame", "-b:a", bitrate]
            elif formato_dest == "m4a":
                bitrate = "256k" if modo == "alta" else ("128k" if modo == "ligero" else "192k")
                cmd += ["-c:a", "aac", "-b:a", bitrate]
            elif formato_dest == "opus":
                bitrate = "192k" if modo == "alta" else ("96k" if modo == "ligero" else "128k")
                cmd += ["-c:a", "libopus", "-b:a", bitrate]
            elif formato_dest == "ogg":
                q = "8" if modo == "alta" else ("4" if modo == "ligero" else "6")
                cmd += ["-c:a", "libvorbis", "-q:a", q]
        else:
            if formato_dest == "gif":
                fps = "15" if modo == "alta" else ("10" if modo == "ligero" else "12")
                escala = "640" if modo == "alta" else ("360" if modo == "ligero" else "480")
                cmd += ["-vf", f"fps={fps},scale={escala}:-1:flags=lanczos"]
            elif modo == "copy":
                cmd += ["-c", "copy"]
            elif formato_dest in ("mp4", "mkv", "mov"):
                crf = "18" if modo == "alta" else ("28" if modo == "ligero" else "23")
                preset = "slow" if modo == "alta" else ("veryfast" if modo == "ligero" else "faster")
                cmd += ["-c:v", "libx264", "-preset", preset, "-crf", crf, "-c:a", "aac", "-b:a", "192k"]
            elif formato_dest == "webm":
                crf = "24" if modo == "alta" else ("36" if modo == "ligero" else "31")
                cmd += ["-c:v", "libvpx-vp9", "-crf", crf, "-b:v", "0", "-c:a", "libopus"]

        cmd += ["-progress", "pipe:1", "-nostats", str(salida)]

        self.cancelado = False
        self.barra_progreso.set_fraction(0.0)
        self._fijar_ocupado(True)
        self._mostrar_estado(f"Convirtiendo a {salida.name}...")

        hilo = threading.Thread(
            target=self._hilo_ffmpeg,
            args=(cmd, salida, self.duracion_origen),
            daemon=True,
        )
        hilo.start()

    def _hilo_ffmpeg(self, cmd, salida: Path, duracion_total: float):
        ultima_linea_err = ""
        try:
            self.proceso_activo = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid,
            )

            for linea in self.proceso_activo.stdout:
                linea = linea.strip()
                if not linea:
                    continue
                if linea.startswith("out_time_us=") or linea.startswith("out_time_ms="):
                    valor = linea.split("=", 1)[1].strip()
                    if valor.isdigit() and duracion_total > 0:
                        seg_actual = int(valor) / 1_000_000.0
                        fraccion = min(max(seg_actual / duracion_total, 0.0), 0.99)
                        GLib.idle_add(
                            self._actualizar_progreso,
                            fraccion,
                            f"Convirtiendo a {salida.name}: {fraccion * 100:.1f}%",
                        )
                elif linea == "progress=end":
                    GLib.idle_add(self._actualizar_progreso, 1.0, f"Finalizado: {salida.name}")
                elif not ("=" in linea and linea.split("=", 1)[0] in (
                    "frame", "fps", "stream_0_0_q", "bitrate", "total_size",
                    "out_time", "dup_frames", "drop_frames", "speed", "progress"
                )):
                    ultima_linea_err = linea

            rc = self.proceso_activo.wait()
        except Exception as e:
            rc = -1
            ultima_linea_err = str(e)
        finally:
            self.proceso_activo = None

        if self.cancelado and salida.exists():
            try:
                salida.unlink()
            except Exception:
                pass

        GLib.idle_add(self._fin_tarea, rc, f"Conversión ({salida.name})", ultima_linea_err)

    def _actualizar_progreso(self, fraccion: float, texto: str):
        self.barra_progreso.set_fraction(min(max(fraccion, 0.0), 1.0))
        self._mostrar_estado(texto)
        return False

    def _fin_tarea(self, rc: int, etiqueta: str, detalle_error: str):
        self._fijar_ocupado(False)
        if self.cancelado:
            self.barra_progreso.set_fraction(0.0)
            self._mostrar_estado(f"{etiqueta} cancelada por el usuario")
        elif rc == 0:
            self.barra_progreso.set_fraction(1.0)
            self._mostrar_estado(f"✓ {etiqueta} completada en {self.ultima_carpeta_abrible}", exito=True)
            notificar(f"{etiqueta} completada", f"Guardado en {self.ultima_carpeta_abrible}")
        else:
            self.barra_progreso.set_fraction(0.0)
            msg = detalle_error or f"El proceso terminó con código {rc}"
            self._mostrar_estado(f"✗ Error: {msg}", error=True)
            notificar(f"Error en {etiqueta.lower()}", msg, critico=True)
        return False

    def _cancelar_proceso(self, *_args):
        self.cancelado = True
        proc = self.proceso_activo
        if proc and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass

    def _al_pulsar_tecla(self, _win, event):
        if event.keyval == Gdk.KEY_Escape:
            if not self.ocupado:
                self.cerrar()
                return True
        return False

    def _al_destruir(self, *_args):
        if self.ocupado:
            self._cancelar_proceso()
        Gtk.main_quit()

    def cerrar(self):
        self.win.destroy()

    def abrir(self):
        self.win.show_all()
        self.win.present()
        Gtk.main()


if __name__ == "__main__":
    MultimediaApp().abrir()
