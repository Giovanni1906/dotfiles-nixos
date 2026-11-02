#!/usr/bin/env python3
# Utilidad gráfica para:
# 1. Redimensionar y optimizar imágenes (lote o individuales, resolución fija y peso ~20 KB).
# 2. Listar nombres de archivos (DNI/nombres sin extensión, con extensión, copiar al portapapeles o exportar).
# 3. Renombrar archivos en lote con vista previa en vivo (sufijo como _FTR, prefijo, reemplazar texto, etc.).
# Se abre o cierra con SUPER + I (utils/optimizar-imagenes.sh) y toma la paleta de tema/tema.conf.

import csv
import math
import os
import shutil
import subprocess
import threading
from pathlib import Path
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango

GLib.set_prgname("optimizar-imagenes")
GLib.set_application_name("Optimizador y Gestor de Archivos")

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

EXTENSIONES_IMAGEN = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".avif", ".heic", ".gif"
}

PRESETS_RESOLUCION = [
    ("800x600", "800", "600"),
    ("640x480", "640", "480"),
    ("400x400", "400", "400"),
    ("1280x720", "1280", "720"),
    ("1920x1080", "1920", "1080"),
    ("Original", "", ""),
]

MODOS_AJUSTE = [
    ("exacto", "Llenar exacto (recorte al centro)"),
    ("proporcional", "Ajustar dentro (sin recortar)"),
    ("estirar", "Estirar (dimensiones exactas)"),
]

FORMATOS_SALIDA = [
    ("jpg", "JPG (Recomendado para ~20 KB)"),
    ("webp", "WebP (Alta eficiencia moderna)"),
    ("png", "PNG (Sin pérdida)"),
    ("mismo", "Conservar formato original"),
]

FILTROS_ARCHIVOS = [
    ("imagenes", "Imágenes (*.jpg, *.png, *.webp...)"),
    ("jpg", "Solo JPG (*.jpg, *.jpeg)"),
    ("pdf", "Solo PDF (*.pdf)"),
    ("todos", "Todos los archivos (*.*)"),
]


def obtener_bin_xsel():
    ruta = shutil.which("xsel")
    if ruta and os.access(ruta, os.X_OK):
        return ruta
    candidatos = list(Path("/nix/store").glob("*-xsel-*/bin/xsel"))
    if candidatos:
        return str(candidatos[0])
    return None


def copiar_al_portapapeles_universal(texto: str):
    if not texto:
        return False

    datos = texto.encode("utf-8")
    exito = False

    # 1. Wayland nativo (wl-copy) desacoplado en sesión independiente (persiste tras cerrar la ventana)
    if shutil.which("wl-copy"):
        try:
            p_wl = subprocess.Popen(
                ["wl-copy"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            p_wl.communicate(input=datos, timeout=2)

            p_wl_p = subprocess.Popen(
                ["wl-copy", "--primary"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            p_wl_p.communicate(input=datos, timeout=2)
            exito = True
        except Exception:
            pass

    # 2. X11 / XWayland (xsel) desacoplado en sesión independiente (para ONLYOFFICE, Navicat, etc.)
    bin_xsel = obtener_bin_xsel()
    display = os.environ.get("DISPLAY", ":0")
    if bin_xsel and display:
        try:
            # CLIPBOARD (Ctrl+V)
            p_xsel = subprocess.Popen(
                [bin_xsel, "--display", display, "-b", "-i"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            p_xsel.communicate(input=datos, timeout=2)

            # PRIMARY (clic central / Shift+Insert)
            p_xsel_p = subprocess.Popen(
                [bin_xsel, "--display", display, "-p", "-i"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            p_xsel_p.communicate(input=datos, timeout=2)
            exito = True
        except Exception:
            pass

    # No usamos Gtk.Clipboard para no sobrescribir a los daemons independientes
    # ni perder la selección cuando la ventana GTK se cierra.
    return exito


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
        try:
            for linea in TEMA.read_text(encoding="utf-8").splitlines():
                linea = sin_comentario(linea).strip()
                if "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip().strip('"')
        except Exception:
            pass
    return valores


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    if len(h) != 6:
        h = "3399cc"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def formatear_tamano(num_bytes):
    for unidad in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unidad}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def notificar(titulo, cuerpo="", critico=False):
    if not shutil.which("notify-send"):
        return
    cmd = ["notify-send", "-a", "Optimizador de Imágenes"]
    if critico:
        cmd += ["-u", "critical"]
    cmd += [titulo, cuerpo]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


class OptimizadorApp:
    def __init__(self):
        self.tema = leer_tema()

        # Carpeta compartida entre módulos para máxima comodidad
        self.carpeta_compartida = Path("/home/nova/Documentos/Backups/cepuii2027/cortada")
        if not self.carpeta_compartida.is_dir():
            self.carpeta_compartida = HOME

        # Estado Módulo 1 (Optimizar)
        self.modo_entrada_opt = "carpeta"
        self.carpeta_origen_opt = self.carpeta_compartida
        self.archivos_origen_opt = []
        self.carpeta_salida_opt = None
        self.en_proceso_opt = False
        self.cancelar_solicitado_opt = False
        self.ultima_carpeta_salida_opt = self.carpeta_compartida

        # Estado Módulo 2 (Listar)
        self.carpeta_listar = self.carpeta_compartida
        self.lista_nombres_actual = []

        # Estado Módulo 3 (Renombrar)
        self.carpeta_renombrar = self.carpeta_compartida
        self.archivos_renombrar = []
        self.debounce_timer_renombrar = None
        self.en_proceso_renombrar = False

        # Estado Módulo 4 (Extraer / Copiar por Lista)
        self.carpeta_origen_extraer = self.carpeta_compartida
        self.carpeta_destino_extraer = None
        self.archivos_encontrados_extraer = []  # list of (Path, str)
        self.elementos_faltantes_extraer = []   # list of str
        self.en_proceso_extraer = False
        self.ultima_carpeta_salida_extraer = None
        self.debounce_timer_extraer = None

        self._construir_ventana()

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
            padding: 14px 18px;
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
            margin-top: 4px;
        }}
        .info-secundaria {{
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
            padding: 5px 8px;
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
        button.tab-nav {{
            padding: 8px 12px;
            font-weight: 700;
            border-radius: 8px;
        }}
        button.tab-nav.tab-activa, button.chip-activo {{
            background-color: {acento_suave};
            border: 1px solid {t["ACENTO"]};
        }}
        button.tab-nav.tab-activa label, button.chip-activo label {{
            color: {t["ACENTO"]};
            font-weight: 700;
        }}
        button.preset-btn {{
            padding: 4px 10px;
            font-size: 11px;
            border-radius: 6px;
        }}
        button.btn-principal {{
            background-color: {t["ACENTO"]};
            border: 1px solid {t["ACENTO"]};
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 700;
        }}
        button.btn-principal label {{
            color: {t["FONDO"]};
            font-weight: 800;
        }}
        button.btn-principal:hover {{
            background-color: {t["SECUNDARIO"]};
            border-color: {t["SECUNDARIO"]};
        }}
        button.btn-cancelar {{
            background-color: rgba(243, 139, 168, 0.2);
            border: 1px solid {t["URGENTE"]};
        }}
        button.btn-cancelar label {{
            color: {t["URGENTE"]};
        }}
        progressbar trough {{
            background-color: {superficie};
            border-radius: 6px;
            min-height: 8px;
            border: none;
        }}
        progressbar progress {{
            background-color: {t["ACENTO"]};
            border-radius: 6px;
            min-height: 8px;
        }}
        combobox button.combo {{
            background-color: {superficie};
            border: 1px solid {borde_suave};
            border-radius: 8px;
            padding: 4px 8px;
            color: {t["TEXTO"]};
        }}
        .caja-drop {{
            background-color: rgba(19, 62, 124, 0.35);
            border: 1px dashed {borde_suave};
            border-radius: 8px;
            padding: 8px 12px;
        }}
        textview text {{
            background-color: {superficie};
            color: {t["TEXTO"]};
            font-size: 11px;
        }}
        treeview {{
            background-color: {superficie};
            color: {t["TEXTO"]};
            font-size: 11px;
            border-radius: 6px;
        }}
        treeview:selected {{
            background-color: {acento_suave};
            color: {t["ACENTO"]};
        }}
        """
        proveedor = Gtk.CssProvider()
        proveedor.load_from_data(css.encode("utf-8"))
        pantalla = Gdk.Screen.get_default()
        if pantalla:
            Gtk.StyleContext.add_provider_for_screen(
                pantalla, proveedor, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _construir_ventana(self):
        self._aplicar_css()

        self.win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.win.set_title("Optimizador y Gestor de Archivos")
        self.win.set_wmclass("optimizar-imagenes", "optimizar-imagenes")
        self.win.set_role("optimizar-imagenes")
        self.win.set_default_size(800, 760)
        self.win.set_position(Gtk.WindowPosition.CENTER)
        self.win.connect("destroy", Gtk.main_quit)
        self.win.connect("key-press-event", self._al_presionar_tecla)

        contenedor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        contenedor.get_style_context().add_class("contenedor-principal")
        self.win.add(contenedor)

        # Encabezado principal
        fila_cabecera = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        contenedor.pack_start(fila_cabecera, False, False, 0)

        lbl_icono = Gtk.Label(label="󰄟")
        lbl_icono.get_style_context().add_class("titulo-app")
        fila_cabecera.pack_start(lbl_icono, False, False, 0)

        caja_titulos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        fila_cabecera.pack_start(caja_titulos, True, True, 0)

        lbl_tit = Gtk.Label(label="GESTOR Y OPTIMIZADOR DE IMÁGENES")
        lbl_tit.set_halign(Gtk.Align.START)
        lbl_tit.get_style_context().add_class("titulo-app")
        caja_titulos.pack_start(lbl_tit, False, False, 0)

        lbl_sub = Gtk.Label(label="Reducir peso (20 KB) · Listar nombres · Renombrar en lote (_FTR) · Copiar por lista")
        lbl_sub.set_halign(Gtk.Align.START)
        lbl_sub.get_style_context().add_class("subtitulo-app")
        caja_titulos.pack_start(lbl_sub, False, False, 0)

        # Barra de Navegación de Pestañas
        barra_tabs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        barra_tabs.set_homogeneous(True)
        contenedor.pack_start(barra_tabs, False, False, 4)

        self.btn_tab_opt = Gtk.Button(label="⚡  Optimizar")
        self.btn_tab_opt.get_style_context().add_class("tab-nav")
        self.btn_tab_opt.connect("clicked", lambda *_: self._cambiar_pestana("optimizar"))
        barra_tabs.pack_start(self.btn_tab_opt, True, True, 0)

        self.btn_tab_listar = Gtk.Button(label="📋  Listar")
        self.btn_tab_listar.get_style_context().add_class("tab-nav")
        self.btn_tab_listar.connect("clicked", lambda *_: self._cambiar_pestana("listar"))
        barra_tabs.pack_start(self.btn_tab_listar, True, True, 0)

        self.btn_tab_renombrar = Gtk.Button(label="🏷️  Renombrar")
        self.btn_tab_renombrar.get_style_context().add_class("tab-nav")
        self.btn_tab_renombrar.connect("clicked", lambda *_: self._cambiar_pestana("renombrar"))
        barra_tabs.pack_start(self.btn_tab_renombrar, True, True, 0)

        self.btn_tab_extraer = Gtk.Button(label="📦  Copiar por Lista")
        self.btn_tab_extraer.get_style_context().add_class("tab-nav")
        self.btn_tab_extraer.connect("clicked", lambda *_: self._cambiar_pestana("extraer"))
        barra_tabs.pack_start(self.btn_tab_extraer, True, True, 0)

        contenedor.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # STACK DE CONTENIDO
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(150)
        contenedor.pack_start(self.stack, True, True, 0)

        self.stack.add_named(self._construir_tab_optimizar(), "optimizar")
        self.stack.add_named(self._construir_tab_listar(), "listar")
        self.stack.add_named(self._construir_tab_renombrar(), "renombrar")
        self.stack.add_named(self._construir_tab_extraer(), "extraer")

        # Activar la primera pestaña por defecto
        self._cambiar_pestana("optimizar")

        self.win.show_all()

    def _cambiar_pestana(self, nombre):
        self.stack.set_visible_child_name(nombre)
        self.btn_tab_opt.get_style_context().remove_class("tab-activa")
        self.btn_tab_listar.get_style_context().remove_class("tab-activa")
        self.btn_tab_renombrar.get_style_context().remove_class("tab-activa")
        self.btn_tab_extraer.get_style_context().remove_class("tab-activa")

        if nombre == "optimizar":
            self.btn_tab_opt.get_style_context().add_class("tab-activa")
        elif nombre == "listar":
            self.btn_tab_listar.get_style_context().add_class("tab-activa")
            self._actualizar_carpeta_listar(self.carpeta_compartida)
        elif nombre == "renombrar":
            self.btn_tab_renombrar.get_style_context().add_class("tab-activa")
            self._actualizar_carpeta_renombrar(self.carpeta_compartida)
        elif nombre == "extraer":
            self.btn_tab_extraer.get_style_context().add_class("tab-activa")
            self._actualizar_carpeta_extraer(self.carpeta_compartida)

    def _etiqueta_seccion(self, texto):
        lbl = Gtk.Label(label=texto)
        lbl.set_halign(Gtk.Align.START)
        lbl.get_style_context().add_class("etiqueta-seccion")
        return lbl

    def _al_presionar_tecla(self, win, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.en_proceso_opt:
                self._cancelar_proceso_opt(None)
            else:
                self.win.destroy()
            return True
        return False

    # =========================================================================
    # PESTAÑA 1: OPTIMIZAR / REDUCIR IMÁGENES
    # =========================================================================
    def _construir_tab_optimizar(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scroll.add(caja)

        # 1. Origen
        caja.pack_start(self._etiqueta_seccion("1. ORIGEN DE IMÁGENES"), False, False, 0)

        fila_modo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fila_modo.set_homogeneous(True)
        caja.pack_start(fila_modo, False, False, 0)

        self.btn_modo_carpeta = Gtk.Button(label="󰉋  Carpeta completa (Lote)")
        self.btn_modo_carpeta.get_style_context().add_class("tab-btn")
        self.btn_modo_carpeta.connect("clicked", lambda b: self._cambiar_modo_entrada_opt("carpeta"))
        fila_modo.pack_start(self.btn_modo_carpeta, True, True, 0)

        self.btn_modo_archivos = Gtk.Button(label="󰈟  Imágenes sueltas")
        self.btn_modo_archivos.get_style_context().add_class("tab-btn")
        self.btn_modo_archivos.connect("clicked", lambda b: self._cambiar_modo_entrada_opt("archivos"))
        fila_modo.pack_start(self.btn_modo_archivos, True, True, 0)

        # Drop Zone
        self.caja_drop_opt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.caja_drop_opt.get_style_context().add_class("caja-drop")
        caja.pack_start(self.caja_drop_opt, False, False, 0)

        self.caja_drop_opt.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.caja_drop_opt.drag_dest_add_uri_targets()
        self.caja_drop_opt.connect("drag-data-received", self._al_soltar_archivos_opt)

        fila_sel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.caja_drop_opt.pack_start(fila_sel, False, False, 0)

        self.entrada_ruta_opt = Gtk.Entry()
        self.entrada_ruta_opt.set_editable(False)
        self.entrada_ruta_opt.set_text(str(self.carpeta_compartida))
        fila_sel.pack_start(self.entrada_ruta_opt, True, True, 0)

        self.btn_elegir_opt = Gtk.Button(label="Examinar...")
        self.btn_elegir_opt.connect("clicked", self._al_elegir_origen_opt)
        fila_sel.pack_start(self.btn_elegir_opt, False, False, 0)

        self.lbl_info_origen_opt = Gtk.Label(label="...")
        self.lbl_info_origen_opt.set_halign(Gtk.Align.START)
        self.lbl_info_origen_opt.get_style_context().add_class("info-secundaria")
        self.caja_drop_opt.pack_start(self.lbl_info_origen_opt, False, False, 0)

        self.chk_subcarpetas_opt = Gtk.CheckButton(label="Incluir imágenes dentro de subcarpetas")
        self.caja_drop_opt.pack_start(self.chk_subcarpetas_opt, False, False, 0)

        # 2. Reducción de resolución / peso
        caja.pack_start(self._etiqueta_seccion("2. REDUCCIÓN DE TAMAÑO / PESO"), False, False, 0)

        fila_tipo_red = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fila_tipo_red.set_homogeneous(True)
        caja.pack_start(fila_tipo_red, False, False, 0)

        self.btn_tipo_peso = Gtk.Button(label="🎯  Peso objetivo (ej. 20 KB o 50 KB)")
        self.btn_tipo_peso.get_style_context().add_class("tab-btn")
        self.btn_tipo_peso.get_style_context().add_class("tab-activa")
        self.btn_tipo_peso.connect("clicked", lambda *_: self._cambiar_tipo_reduccion("peso"))
        fila_tipo_red.pack_start(self.btn_tipo_peso, True, True, 0)

        self.btn_tipo_pct = Gtk.Button(label="󰏖  Por Porcentaje (%)")
        self.btn_tipo_pct.get_style_context().add_class("tab-btn")
        self.btn_tipo_pct.connect("clicked", lambda *_: self._cambiar_tipo_reduccion("pct"))
        fila_tipo_red.pack_start(self.btn_tipo_pct, True, True, 0)

        self.btn_tipo_dims = Gtk.Button(label="󰆾  Por Dimensiones fijas (px)")
        self.btn_tipo_dims.get_style_context().add_class("tab-btn")
        self.btn_tipo_dims.connect("clicked", lambda *_: self._cambiar_tipo_reduccion("dims"))
        fila_tipo_red.pack_start(self.btn_tipo_dims, True, True, 0)

        # Contenedor modo 1: Peso objetivo (ej. 20 KB / 50 KB)
        self.caja_modo_peso = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        caja.pack_start(self.caja_modo_peso, False, False, 0)

        fila_presets_peso = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.caja_modo_peso.pack_start(fila_presets_peso, False, False, 0)

        self.preset_peso_btns = []
        for valor in ["20 KB", "30 KB", "50 KB", "100 KB", "150 KB"]:
            btn_p = Gtk.Button(label=valor)
            btn_p.get_style_context().add_class("preset-btn")
            btn_p.connect("clicked", self._al_elegir_preset_peso, valor.replace(" KB", ""), btn_p)
            fila_presets_peso.pack_start(btn_p, False, False, 0)
            self.preset_peso_btns.append(btn_p)

        fila_input_peso = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.caja_modo_peso.pack_start(fila_input_peso, False, False, 0)

        fila_input_peso.pack_start(Gtk.Label(label="Peso máximo objetivo:"), False, False, 0)
        self.entrada_peso = Gtk.Entry()
        self.entrada_peso.set_width_chars(6)
        self.entrada_peso.set_text("20")
        fila_input_peso.pack_start(self.entrada_peso, False, False, 0)
        fila_input_peso.pack_start(Gtk.Label(label="KB  (ej: 20 o 50)"), False, False, 0)

        lbl_guia_peso = Gtk.Label(
            label="• Calcula la resolución óptima proporcional para que cada imagen pese ~20 KB o 50 KB.\n"
                  "• 100% proporcional: no corta cabezas, no estira caras, y mantiene tonos de piel reales sin verdes."
        )
        lbl_guia_peso.set_halign(Gtk.Align.START)
        lbl_guia_peso.get_style_context().add_class("info-secundaria")
        self.caja_modo_peso.pack_start(lbl_guia_peso, False, False, 0)

        # Contenedor modo 2: Porcentaje
        self.caja_modo_pct = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        caja.pack_start(self.caja_modo_pct, False, False, 0)
        self.caja_modo_pct.hide()

        fila_presets_pct = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.caja_modo_pct.pack_start(fila_presets_pct, False, False, 0)

        self.preset_pct_btns = []
        for valor in ["50%", "40%", "30%", "25%", "20%", "75%"]:
            btn_p = Gtk.Button(label=valor)
            btn_p.get_style_context().add_class("preset-btn")
            btn_p.connect("clicked", self._al_elegir_preset_pct, valor.replace("%", ""), btn_p)
            fila_presets_pct.pack_start(btn_p, False, False, 0)
            self.preset_pct_btns.append(btn_p)

        fila_input_pct = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.caja_modo_pct.pack_start(fila_input_pct, False, False, 0)

        fila_input_pct.pack_start(Gtk.Label(label="Porcentaje de reducción:"), False, False, 0)
        self.entrada_pct = Gtk.Entry()
        self.entrada_pct.set_width_chars(5)
        self.entrada_pct.set_text("30")
        fila_input_pct.pack_start(self.entrada_pct, False, False, 0)
        fila_input_pct.pack_start(Gtk.Label(label="%  (ej: mogrify -resize 30%)"), False, False, 0)

        lbl_guia_pct = Gtk.Label(label="• Reduce el ancho y alto en proporción exacta al porcentaje indicado.")
        lbl_guia_pct.set_halign(Gtk.Align.START)
        lbl_guia_pct.get_style_context().add_class("info-secundaria")
        self.caja_modo_pct.pack_start(lbl_guia_pct, False, False, 0)

        # Contenedor modo 3: Dimensiones
        self.caja_modo_dims = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        caja.pack_start(self.caja_modo_dims, False, False, 0)
        self.caja_modo_dims.hide()

        fila_dims = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.caja_modo_dims.pack_start(fila_dims, False, False, 0)

        fila_dims.pack_start(Gtk.Label(label="Ancho max:"), False, False, 0)
        self.entrada_w = Gtk.Entry()
        self.entrada_w.set_width_chars(6)
        self.entrada_w.set_text("450")
        fila_dims.pack_start(self.entrada_w, False, False, 0)
        fila_dims.pack_start(Gtk.Label(label="px"), False, False, 0)

        fila_dims.pack_start(Gtk.Label(label="  Alto max:"), False, False, 0)
        self.entrada_h = Gtk.Entry()
        self.entrada_h.set_width_chars(6)
        self.entrada_h.set_text("600")
        fila_dims.pack_start(self.entrada_h, False, False, 0)
        fila_dims.pack_start(Gtk.Label(label="px"), False, False, 0)

        fila_dims.pack_start(Gtk.Label(label="  Modo:"), False, False, 0)
        self.combo_ajuste = Gtk.ComboBoxText()
        self.combo_ajuste.append("proporcional", "Proporcional (sin deformar ni cortar caras)")
        self.combo_ajuste.append("exacto", "Llenar exacto (recorte al centro)")
        self.combo_ajuste.set_active(0)
        fila_dims.pack_start(self.combo_ajuste, True, True, 0)

        # 3. Calidad y Color
        caja.pack_start(self._etiqueta_seccion("3. CALIDAD VISUAL Y COLOR (FIDELIDAD DE ROSTROS)"), False, False, 0)

        fila_calidad = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caja.pack_start(fila_calidad, False, False, 0)

        fila_calidad.pack_start(Gtk.Label(label="Calidad visual:"), False, False, 0)
        self.combo_calidad = Gtk.ComboBoxText()
        self.combo_calidad.append("75", "75% · Equilibrada (rostros limpios, ligera ~20-35 KB)")
        self.combo_calidad.append("80", "80% · Alta calidad (rostros nítidos)")
        self.combo_calidad.append("70", "70% · Muy ligera (menor peso)")
        self.combo_calidad.append("85", "85% · Máxima fidelidad")
        self.combo_calidad.set_active(0)
        fila_calidad.pack_start(self.combo_calidad, True, True, 0)

        fila_calidad.pack_start(Gtk.Label(label="Formato:"), False, False, 0)
        self.combo_formato = Gtk.ComboBoxText()
        for clave, txt in FORMATOS_SALIDA:
            self.combo_formato.append(clave, txt)
        self.combo_formato.set_active(0)
        fila_calidad.pack_start(self.combo_formato, False, False, 0)

        fila_checks_opt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        caja.pack_start(fila_checks_opt, False, False, 0)

        self.chk_srgb = Gtk.CheckButton(label="Garantizar color real (-colorspace sRGB · evita caras verdes)")
        self.chk_srgb.set_active(True)
        fila_checks_opt.pack_start(self.chk_srgb, False, False, 0)

        self.chk_strip = Gtk.CheckButton(label="Quitar metadatos EXIF (-strip)")
        self.chk_strip.set_active(True)
        fila_checks_opt.pack_start(self.chk_strip, False, False, 0)

        # Estado inicial del modo (Peso objetivo activado por defecto con 20 KB)
        self.modo_red_actual = "peso"
        if self.preset_peso_btns:
            self.preset_peso_btns[0].get_style_context().add_class("chip-activo")  # 20 KB activo
        if self.preset_pct_btns:
            self.preset_pct_btns[2].get_style_context().add_class("chip-activo")  # 30% activo

        # 4. Destino
        caja.pack_start(self._etiqueta_seccion("4. CARPETA DE DESTINO"), False, False, 0)

        fila_dest = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        caja.pack_start(fila_dest, False, False, 0)

        self.radio_subcarpeta = Gtk.RadioButton.new_with_label(None, "Guardar en subcarpeta 'optimizadas/'")
        fila_dest.pack_start(self.radio_subcarpeta, False, False, 0)

        self.radio_personalizada = Gtk.RadioButton.new_with_label_from_widget(
            self.radio_subcarpeta, "Elegir otra..."
        )
        self.radio_personalizada.connect(
            "toggled", lambda r: self.btn_dest_custom.set_sensitive(r.get_active())
        )
        fila_dest.pack_start(self.radio_personalizada, False, False, 0)

        self.btn_dest_custom = Gtk.Button(label="Examinar...")
        self.btn_dest_custom.set_sensitive(False)
        self.btn_dest_custom.connect("clicked", self._al_elegir_dest_custom_opt)
        fila_dest.pack_start(self.btn_dest_custom, False, False, 0)

        self.lbl_dest_custom = Gtk.Label(label="")
        self.lbl_dest_custom.get_style_context().add_class("info-secundaria")
        fila_dest.pack_start(self.lbl_dest_custom, True, True, 0)

        # 5. Progreso y Log
        caja.pack_start(self._etiqueta_seccion("5. PROCESAMIENTO"), False, False, 0)

        self.barra_progreso_opt = Gtk.ProgressBar()
        self.barra_progreso_opt.set_fraction(0.0)
        self.barra_progreso_opt.set_text("Listo")
        self.barra_progreso_opt.set_show_text(True)
        caja.pack_start(self.barra_progreso_opt, False, False, 0)

        self.lbl_estado_opt = Gtk.Label(label="Listo para procesar imágenes")
        self.lbl_estado_opt.set_halign(Gtk.Align.START)
        self.lbl_estado_opt.get_style_context().add_class("estado-texto")
        caja.pack_start(self.lbl_estado_opt, False, False, 0)

        scroll_log = Gtk.ScrolledWindow()
        scroll_log.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_log.set_min_content_height(90)
        caja.pack_start(scroll_log, True, True, 0)

        self.txt_log_opt = Gtk.TextView()
        self.txt_log_opt.set_editable(False)
        self.txt_log_opt.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroll_log.add(self.txt_log_opt)
        self.buffer_log_opt = self.txt_log_opt.get_buffer()

        # Botones acción
        fila_acciones = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        caja.pack_start(fila_acciones, False, False, 4)

        self.btn_iniciar_opt = Gtk.Button(label="⚡  OPTIMIZAR IMÁGENES")
        self.btn_iniciar_opt.get_style_context().add_class("btn-principal")
        self.btn_iniciar_opt.connect("clicked", self._iniciar_proceso_opt)
        fila_acciones.pack_start(self.btn_iniciar_opt, True, True, 0)

        self.btn_cancelar_opt = Gtk.Button(label="󰜺 Cancelar")
        self.btn_cancelar_opt.get_style_context().add_class("btn-cancelar")
        self.btn_cancelar_opt.set_sensitive(False)
        self.btn_cancelar_opt.connect("clicked", self._cancelar_proceso_opt)
        fila_acciones.pack_start(self.btn_cancelar_opt, False, False, 0)

        self.btn_abrir_carpeta_opt = Gtk.Button(label="📁 Abrir salida")
        self.btn_abrir_carpeta_opt.set_sensitive(False)
        self.btn_abrir_carpeta_opt.connect("clicked", self._abrir_carpeta_salida_opt)
        fila_acciones.pack_start(self.btn_abrir_carpeta_opt, False, False, 0)

        self._cambiar_modo_entrada_opt("carpeta")
        self._escanear_carpeta_opt()
        return scroll

    def _cambiar_tipo_reduccion(self, tipo):
        self.modo_red_actual = tipo
        self.btn_tipo_peso.get_style_context().remove_class("tab-activa")
        self.btn_tipo_pct.get_style_context().remove_class("tab-activa")
        self.btn_tipo_dims.get_style_context().remove_class("tab-activa")
        self.caja_modo_peso.hide()
        self.caja_modo_pct.hide()
        self.caja_modo_dims.hide()

        if tipo == "peso":
            self.btn_tipo_peso.get_style_context().add_class("tab-activa")
            self.caja_modo_peso.show()
        elif tipo == "pct":
            self.btn_tipo_pct.get_style_context().add_class("tab-activa")
            self.caja_modo_pct.show()
        else:
            self.btn_tipo_dims.get_style_context().add_class("tab-activa")
            self.caja_modo_dims.show()

    def _al_elegir_preset_peso(self, btn, valor, btn_obj):
        for b in self.preset_peso_btns:
            b.get_style_context().remove_class("chip-activo")
        btn_obj.get_style_context().add_class("chip-activo")
        self.entrada_peso.set_text(valor)

    def _al_elegir_preset_pct(self, btn, valor, btn_obj):
        for b in self.preset_pct_btns:
            b.get_style_context().remove_class("chip-activo")
        btn_obj.get_style_context().add_class("chip-activo")
        self.entrada_pct.set_text(valor)

    def _cambiar_modo_entrada_opt(self, modo):
        self.modo_entrada_opt = modo
        if modo == "carpeta":
            self.btn_modo_carpeta.get_style_context().add_class("tab-activa")
            self.btn_modo_archivos.get_style_context().remove_class("tab-activa")
            self.chk_subcarpetas_opt.show()
            self._escanear_carpeta_opt()
        else:
            self.btn_modo_archivos.get_style_context().add_class("tab-activa")
            self.btn_modo_carpeta.get_style_context().remove_class("tab-activa")
            self.chk_subcarpetas_opt.hide()
            self._actualizar_resumen_origen_opt()

    def _al_elegir_preset_opt(self, btn, w, h, btn_obj):
        for b in getattr(self, "preset_btns", []):
            b.get_style_context().remove_class("chip-activo")
        btn_obj.get_style_context().add_class("chip-activo")
        self.entrada_w.set_text(w)
        self.entrada_h.set_text(h)

    def _al_elegir_dest_custom_opt(self, btn):
        dialogo = Gtk.FileChooserDialog(
            title="Seleccionar carpeta de destino",
            parent=self.win,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialogo.add_button("Seleccionar", Gtk.ResponseType.OK)
        if dialogo.run() == Gtk.ResponseType.OK:
            self.carpeta_salida_opt = Path(dialogo.get_filename())
            self.lbl_dest_custom.set_text(self.carpeta_salida_opt.name)
        dialogo.destroy()

    def _al_elegir_origen_opt(self, btn):
        if self.modo_entrada_opt == "carpeta":
            dialogo = Gtk.FileChooserDialog(
                title="Seleccionar carpeta con imágenes",
                parent=self.win,
                action=Gtk.FileChooserAction.SELECT_FOLDER,
            )
            dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
            dialogo.add_button("Seleccionar", Gtk.ResponseType.OK)
            dialogo.set_current_folder(str(self.carpeta_compartida))

            if dialogo.run() == Gtk.ResponseType.OK:
                self.carpeta_compartida = Path(dialogo.get_filename())
                self.carpeta_origen_opt = self.carpeta_compartida
                self.entrada_ruta_opt.set_text(str(self.carpeta_compartida))
                self._escanear_carpeta_opt()
            dialogo.destroy()
        else:
            dialogo = Gtk.FileChooserDialog(
                title="Seleccionar imágenes",
                parent=self.win,
                action=Gtk.FileChooserAction.OPEN,
            )
            dialogo.set_select_multiple(True)
            dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
            dialogo.add_button("Seleccionar", Gtk.ResponseType.OK)
            dialogo.set_current_folder(str(self.carpeta_compartida))

            filtro = Gtk.FileFilter()
            filtro.set_name("Imágenes")
            for ext in EXTENSIONES_IMAGEN:
                filtro.add_pattern(f"*{ext}")
                filtro.add_pattern(f"*{ext.upper()}")
            dialogo.add_filter(filtro)

            if dialogo.run() == Gtk.ResponseType.OK:
                nombres = dialogo.get_filenames()
                self.archivos_origen_opt = [Path(p) for p in nombres]
                self.entrada_ruta_opt.set_text(f"{len(self.archivos_origen_opt)} imágenes seleccionadas")
                self._actualizar_resumen_origen_opt()
            dialogo.destroy()

    def _al_soltar_archivos_opt(self, widget, context, x, y, data, info, time):
        uris = data.get_uris()
        context.finish(True, False, time)
        if not uris:
            return

        rutas = [Path(unquote(urlparse(u).path)) for u in uris if Path(unquote(urlparse(u).path)).exists()]
        if not rutas:
            return

        if len(rutas) == 1 and rutas[0].is_dir():
            self.carpeta_compartida = rutas[0]
            self.carpeta_origen_opt = self.carpeta_compartida
            self.entrada_ruta_opt.set_text(str(self.carpeta_compartida))
            self._cambiar_modo_entrada_opt("carpeta")
        else:
            archivos_validos = [r for r in rutas if r.is_file() and r.suffix.lower() in EXTENSIONES_IMAGEN]
            if archivos_validos:
                self.archivos_origen_opt = archivos_validos
                self.entrada_ruta_opt.set_text(f"{len(archivos_validos)} imágenes seleccionadas")
                self._cambiar_modo_entrada_opt("archivos")

    def _escanear_carpeta_opt(self):
        if not self.carpeta_origen_opt or not self.carpeta_origen_opt.is_dir():
            return
        sub = self.chk_subcarpetas_opt.get_active()
        patron = "**/*" if sub else "*"
        encontrados = []
        try:
            for item in self.carpeta_origen_opt.glob(patron):
                if item.is_file() and item.suffix.lower() in EXTENSIONES_IMAGEN:
                    encontrados.append(item)
        except Exception:
            pass
        self.archivos_origen_opt = encontrados
        self._actualizar_resumen_origen_opt()

    def _actualizar_resumen_origen_opt(self):
        total = len(self.archivos_origen_opt)
        if total == 0:
            self.lbl_info_origen_opt.set_text("Ninguna imagen encontrada")
            self.lbl_estado_opt.set_text("Selecciona una carpeta o archivos para comenzar")
        else:
            bytes_totales = sum(a.stat().st_size for a in self.archivos_origen_opt if a.exists())
            self.lbl_info_origen_opt.set_text(
                f"✓ {total} imágenes encontradas ({formatear_tamano(bytes_totales)} en total)"
            )
            self.lbl_estado_opt.set_text(f"Listo para procesar {total} imágenes")

    def _agregar_log_opt(self, texto):
        def _en_hilo():
            fin = self.buffer_log_opt.get_end_iter()
            self.buffer_log_opt.insert(fin, texto + "\n")
            marca = self.buffer_log_opt.create_mark(None, fin, False)
            self.txt_log_opt.scroll_to_mark(marca, 0.05, True, 0.0, 1.0)
            return False
        GLib.idle_add(_en_hilo)

    def _iniciar_proceso_opt(self, btn):
        if self.en_proceso_opt:
            return

        if self.modo_entrada_opt == "carpeta":
            self._escanear_carpeta_opt()

        if not self.archivos_origen_opt:
            self.lbl_estado_opt.set_text("Error: No hay imágenes seleccionadas")
            return

        if not shutil.which("magick") and not shutil.which("convert"):
            self.lbl_estado_opt.set_text("Error: ImageMagick no está instalado")
            return

        self.en_proceso_opt = True
        self.cancelar_solicitado_opt = False
        self.btn_iniciar_opt.set_sensitive(False)
        self.btn_cancelar_opt.set_sensitive(True)
        self.btn_abrir_carpeta_opt.set_sensitive(False)
        self.buffer_log_opt.set_text("")

        tipo_red = getattr(self, "modo_red_actual", "peso")
        peso_str = self.entrada_peso.get_text().strip()
        pct_str = self.entrada_pct.get_text().strip()
        ancho_str = self.entrada_w.get_text().strip()
        alto_str = self.entrada_h.get_text().strip()
        modo_ajuste = self.combo_ajuste.get_active_id() or "proporcional"
        calidad_num = int(self.combo_calidad.get_active_id() or "75")
        formato_salida = self.combo_formato.get_active_id() or "jpg"
        forzar_srgb = self.chk_srgb.get_active()
        strip_meta = self.chk_strip.get_active()

        if self.radio_personalizada.get_active() and self.carpeta_salida_opt:
            dir_salida_base = self.carpeta_salida_opt
        elif self.carpeta_origen_opt:
            dir_salida_base = self.carpeta_origen_opt / "optimizadas"
        else:
            dir_salida_base = self.archivos_origen_opt[0].parent / "optimizadas"

        try:
            dir_salida_base.mkdir(parents=True, exist_ok=True)
            self.ultima_carpeta_salida_opt = dir_salida_base
        except Exception as e:
            self.lbl_estado_opt.set_text(f"Error creando carpeta destino: {e}")
            self.en_proceso_opt = False
            self.btn_iniciar_opt.set_sensitive(True)
            self.btn_cancelar_opt.set_sensitive(False)
            return

        threading.Thread(
            target=self._worker_optimizacion,
            args=(
                list(self.archivos_origen_opt),
                dir_salida_base,
                tipo_red,
                peso_str,
                pct_str,
                ancho_str,
                alto_str,
                modo_ajuste,
                calidad_num,
                formato_salida,
                forzar_srgb,
                strip_meta,
            ),
            daemon=True,
        ).start()

    def _worker_optimizacion(
        self, archivos, dir_salida, tipo_red, peso_str, pct_str, ancho, alto, modo_ajuste, calidad, formato, forzar_srgb, strip_meta
    ):
        total = len(archivos)
        exitos = 0
        errores = 0
        bytes_antes = 0
        bytes_despues = 0

        self._agregar_log_opt(f"Iniciando optimización de {total} imagen(es)...")
        if tipo_red == "peso":
            self._agregar_log_opt(f"• Modo: Peso objetivo ~{peso_str or '20'} KB (Resolución adaptativa proporcional)")
        elif tipo_red == "pct":
            self._agregar_log_opt(f"• Modo: Reducción {pct_str}% (mogrify -resize {pct_str}%)")
        else:
            self._agregar_log_opt(f"• Modo: Dimensiones max {ancho or 'auto'}x{alto or 'auto'} ({modo_ajuste})")
        self._agregar_log_opt(f"• Calidad: {calidad}% · Espacio de color: {'sRGB (Fidelidad de rostros)' if forzar_srgb else 'Original'}")
        self._agregar_log_opt(f"• Carpeta destino: {dir_salida}\n" + "—" * 50)

        cmd_magick = "magick" if shutil.which("magick") else "convert"

        for idx, arch in enumerate(archivos, start=1):
            if self.cancelar_solicitado_opt:
                self._agregar_log_opt("\n⚠ Proceso cancelado.")
                break

            fraccion = idx / total
            GLib.idle_add(self.barra_progreso_opt.set_fraction, fraccion)
            GLib.idle_add(self.barra_progreso_opt.set_text, f"{idx}/{total} ({int(fraccion*100)}%)")
            GLib.idle_add(self.lbl_estado_opt.set_text, f"Procesando: {arch.name}...")

            tam_orig = arch.stat().st_size if arch.exists() else 0
            bytes_antes += tam_orig

            ext = ".jpg" if formato == "jpg" else (".webp" if formato == "webp" else (".png" if formato == "png" else arch.suffix.lower()))
            salida_arch = dir_salida / f"{arch.stem}{ext}"

            try:
                res_err = None
                if tipo_red == "peso":
                    try:
                        target_kb = float(peso_str) if peso_str else 20.0
                    except ValueError:
                        target_kb = 20.0
                    target_bytes = int(target_kb * 1024)

                    # 1. Obtener dimensiones originales con identify
                    res_id = subprocess.run(
                        [cmd_magick, "identify", "-format", "%w %h", str(arch)],
                        capture_output=True,
                        text=True,
                    )
                    if res_id.returncode == 0 and res_id.stdout.strip():
                        partes = res_id.stdout.strip().split()
                        w_orig, h_orig = int(partes[0]), int(partes[1])
                    else:
                        w_orig, h_orig = 1200, 1600

                    ratio = (w_orig / h_orig) if h_orig > 0 else 0.75
                    area_obj = target_bytes / 0.11
                    h_est = max(80, int(math.sqrt(area_obj / ratio)))
                    w_est = max(60, int(h_est * ratio))

                    base_args = [cmd_magick, str(arch)]
                    if forzar_srgb:
                        base_args += ["-colorspace", "sRGB"]
                    if strip_meta:
                        base_args += ["-strip"]
                    base_args += ["-quality", str(calidad)]

                    # Pasada 1
                    args_p1 = list(base_args)
                    args_p1 += ["-resize", f"{w_est}x{h_est}>", str(salida_arch)]
                    res = subprocess.run(args_p1, capture_output=True, text=True, timeout=30)
                    if res.returncode != 0:
                        res_err = res.stderr

                    if res.returncode == 0 and salida_arch.exists():
                        tam1 = salida_arch.stat().st_size
                        # Si excede el peso objetivo o quedó por debajo de 72%, ajuste fino
                        if tam1 > target_bytes or tam1 < target_bytes * 0.72:
                            factor = math.sqrt((target_bytes * 0.96) / max(tam1, 1))
                            factor = max(0.4, min(2.0, factor))
                            w2 = max(60, int(w_est * factor))
                            h2 = max(80, int(h_est * factor))
                            args_p2 = list(base_args)
                            args_p2 += ["-resize", f"{w2}x{h2}>", str(salida_arch)]
                            res = subprocess.run(args_p2, capture_output=True, text=True, timeout=30)
                            if res.returncode != 0:
                                res_err = res.stderr
                else:
                    args = [cmd_magick, str(arch)]
                    if tipo_red == "pct":
                        pct = int(pct_str) if pct_str.isdigit() else 30
                        args += ["-resize", f"{pct}%"]
                    else:
                        if ancho and alto:
                            if modo_ajuste == "exacto":
                                args += ["-resize", f"{ancho}x{alto}^", "-gravity", "center", "-extent", f"{ancho}x{alto}"]
                            else:
                                args += ["-resize", f"{ancho}x{alto}>"]
                        elif ancho and not alto:
                            args += ["-resize", f"{ancho}>"]
                        elif alto and not ancho:
                            args += ["-resize", f"x{alto}>"]

                    if forzar_srgb:
                        args += ["-colorspace", "sRGB"]
                    if strip_meta:
                        args += ["-strip"]
                    args += ["-quality", str(calidad)]
                    args.append(str(salida_arch))
                    res = subprocess.run(args, capture_output=True, text=True, timeout=30)
                    if res.returncode != 0:
                        res_err = res.stderr

                if salida_arch.exists() and salida_arch.stat().st_size > 0:
                    tam_fin = salida_arch.stat().st_size
                    bytes_despues += tam_fin
                    exitos += 1
                    ahorro = ((tam_orig - tam_fin) / tam_orig * 100) if tam_orig > 0 else 0.0

                    # Resolución final
                    res_dim = subprocess.run(
                        [cmd_magick, "identify", "-format", "%wx%h", str(salida_arch)],
                        capture_output=True,
                        text=True,
                    )
                    dim_txt = f" ({res_dim.stdout.strip()}px)" if res_dim.returncode == 0 else ""

                    self._agregar_log_opt(
                        f"✓ {arch.name} ➔ {salida_arch.name}: {formatear_tamano(tam_orig)} ➔ {formatear_tamano(tam_fin)}{dim_txt} ({ahorro:+.1f}%)"
                    )
                else:
                    errores += 1
                    err_msg = res_err.strip() if res_err else "Fallo en conversión"
                    self._agregar_log_opt(f"✗ {arch.name}: Error ({err_msg})")
            except Exception as e:
                errores += 1
                self._agregar_log_opt(f"✗ {arch.name}: Error ({e})")

        def _finalizar():
            self.en_proceso_opt = False
            self.btn_iniciar_opt.set_sensitive(True)
            self.btn_cancelar_opt.set_sensitive(False)
            self.btn_abrir_carpeta_opt.set_sensitive(True)

            ahorro_total = ((bytes_antes - bytes_despues) / bytes_antes * 100) if bytes_antes > 0 else 0.0
            self._agregar_log_opt(
                f"\n{'='*50}\nCompletado: {exitos} exitosas, {errores} errores.\n"
                f"Peso total: {formatear_tamano(bytes_antes)} ➔ {formatear_tamano(bytes_despues)} (Ahorro: {ahorro_total:.1f}%)\n"
                f"Carpeta: {dir_salida}"
            )
            if not self.cancelar_solicitado_opt:
                self.barra_progreso_opt.set_fraction(1.0)
                self.barra_progreso_opt.set_text(f"Completado ({exitos}/{total})")
                self.lbl_estado_opt.set_text(f"✓ {exitos} imágenes optimizadas. Ahorro: {ahorro_total:.1f}%")
                notificar("Optimización completada", f"{exitos} imágenes procesadas con éxito.")
            return False

        GLib.idle_add(_finalizar)

    def _cancelar_proceso_opt(self, btn):
        if self.en_proceso_opt:
            self.cancelar_solicitado_opt = True
            self.lbl_estado_opt.set_text("Cancelando...")

    def _abrir_carpeta_salida_opt(self, btn):
        if self.ultima_carpeta_salida_opt and self.ultima_carpeta_salida_opt.exists():
            subprocess.Popen(["xdg-open", str(self.ultima_carpeta_salida_opt)])

    # =========================================================================
    # PESTAÑA 2: LISTAR NOMBRES DE ARCHIVOS
    # =========================================================================
    def _construir_tab_listar(self):
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # 1. Carpeta y filtro
        caja.pack_start(self._etiqueta_seccion("CARPETA A INSPECCIONAR"), False, False, 0)

        caja_drop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        caja_drop.get_style_context().add_class("caja-drop")
        caja.pack_start(caja_drop, False, False, 0)

        caja_drop.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        caja_drop.drag_dest_add_uri_targets()
        caja_drop.connect("drag-data-received", self._al_soltar_carpeta_listar)

        fila_dir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        caja_drop.pack_start(fila_dir, False, False, 0)

        self.entrada_dir_listar = Gtk.Entry()
        self.entrada_dir_listar.set_editable(False)
        self.entrada_dir_listar.set_text(str(self.carpeta_compartida))
        fila_dir.pack_start(self.entrada_dir_listar, True, True, 0)

        btn_elegir = Gtk.Button(label="Examinar...")
        btn_elegir.connect("clicked", self._al_elegir_carpeta_listar)
        fila_dir.pack_start(btn_elegir, False, False, 0)

        # Opciones de listado
        fila_opciones = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caja.pack_start(fila_opciones, False, False, 0)

        fila_opciones.pack_start(Gtk.Label(label="Filtro:"), False, False, 0)
        self.combo_filtro_listar = Gtk.ComboBoxText()
        for clave, txt in FILTROS_ARCHIVOS:
            self.combo_filtro_listar.append(clave, txt)
        self.combo_filtro_listar.set_active(0)
        self.combo_filtro_listar.connect("changed", lambda *_: self._generar_listado())
        fila_opciones.pack_start(self.combo_filtro_listar, False, False, 0)

        fila_opciones.pack_start(Gtk.Label(label="  Formato:"), False, False, 0)
        self.combo_formato_listar = Gtk.ComboBoxText()
        self.combo_formato_listar.append("solo_nombre", "Solo nombre sin extensión (ej. 60178873)")
        self.combo_formato_listar.append("con_extension", "Nombre con extensión (ej. 60178873.jpg)")
        self.combo_formato_listar.append("con_tamano", "Nombre y peso (ej. 60178873.jpg · 420 KB)")
        self.combo_formato_listar.set_active(0)
        self.combo_formato_listar.connect("changed", lambda *_: self._generar_listado())
        fila_opciones.pack_start(self.combo_formato_listar, True, True, 0)

        self.chk_subcarpetas_listar = Gtk.CheckButton(label="Incluir subcarpetas")
        self.chk_subcarpetas_listar.connect("toggled", lambda *_: self._generar_listado())
        fila_opciones.pack_start(self.chk_subcarpetas_listar, False, False, 0)

        # Resumen y contador
        fila_info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caja.pack_start(fila_info, False, False, 0)

        self.lbl_conteo_listar = Gtk.Label(label="0 archivos listados")
        self.lbl_conteo_listar.set_halign(Gtk.Align.START)
        self.lbl_conteo_listar.get_style_context().add_class("estado-exito")
        fila_info.pack_start(self.lbl_conteo_listar, True, True, 0)

        btn_refrescar = Gtk.Button(label="🔄 Actualizar")
        btn_refrescar.connect("clicked", lambda *_: self._generar_listado())
        fila_info.pack_start(btn_refrescar, False, False, 0)

        # Área de texto con la lista
        scroll_txt = Gtk.ScrolledWindow()
        scroll_txt.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        caja.pack_start(scroll_txt, True, True, 0)

        self.txt_lista = Gtk.TextView()
        self.txt_lista.set_editable(False)
        self.txt_lista.set_cursor_visible(True)
        scroll_txt.add(self.txt_lista)
        self.buffer_lista = self.txt_lista.get_buffer()

        # Botones de exportación y copiado
        fila_acciones = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caja.pack_start(fila_acciones, False, False, 4)

        self.btn_copiar_lista = Gtk.Button(label="📋  COPIAR LISTA AL PORTAPAPELES")
        self.btn_copiar_lista.get_style_context().add_class("btn-principal")
        self.btn_copiar_lista.connect("clicked", self._copiar_lista_portapapeles)
        fila_acciones.pack_start(self.btn_copiar_lista, True, True, 0)

        self.btn_guardar_lista = Gtk.Button(label="💾  Guardar...")
        self.btn_guardar_lista.connect("clicked", self._guardar_lista_archivo)
        fila_acciones.pack_start(self.btn_guardar_lista, False, False, 0)

        self.btn_exportar_rapido = Gtk.Button(label="📄  Crear 'dnis.txt' aquí")
        self.btn_exportar_rapido.connect("clicked", self._exportar_dnis_directo)
        fila_acciones.pack_start(self.btn_exportar_rapido, False, False, 0)

        # Cargar el listado inicial
        self._generar_listado()

        return caja

    def _actualizar_carpeta_listar(self, ruta: Path):
        self.carpeta_listar = ruta
        self.entrada_dir_listar.set_text(str(ruta))
        self._generar_listado()

    def _al_elegir_carpeta_listar(self, btn):
        dialogo = Gtk.FileChooserDialog(
            title="Seleccionar carpeta a listar",
            parent=self.win,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialogo.add_button("Seleccionar", Gtk.ResponseType.OK)
        dialogo.set_current_folder(str(self.carpeta_listar))

        if dialogo.run() == Gtk.ResponseType.OK:
            self.carpeta_compartida = Path(dialogo.get_filename())
            self._actualizar_carpeta_listar(self.carpeta_compartida)
        dialogo.destroy()

    def _al_soltar_carpeta_listar(self, widget, context, x, y, data, info, time):
        uris = data.get_uris()
        context.finish(True, False, time)
        if not uris:
            return
        p = Path(unquote(urlparse(uris[0]).path))
        if p.exists():
            carpeta = p if p.is_dir() else p.parent
            self.carpeta_compartida = carpeta
            self._actualizar_carpeta_listar(self.carpeta_compartida)

    def _generar_listado(self):
        if not self.carpeta_listar or not self.carpeta_listar.is_dir():
            self.lbl_conteo_listar.set_text("Carpeta no válida")
            self.buffer_lista.set_text("")
            return

        filtro = self.combo_filtro_listar.get_active_id() or "imagenes"
        formato = self.combo_formato_listar.get_active_id() or "solo_nombre"
        sub = self.chk_subcarpetas_listar.get_active()

        patron = "**/*" if sub else "*"
        items = []

        try:
            for arch in sorted(self.carpeta_listar.glob(patron)):
                if not arch.is_file():
                    continue
                ext = arch.suffix.lower()

                if filtro == "imagenes" and ext not in EXTENSIONES_IMAGEN:
                    continue
                elif filtro == "jpg" and ext not in (".jpg", ".jpeg"):
                    continue
                elif filtro == "pdf" and ext != ".pdf":
                    continue

                if formato == "solo_nombre":
                    items.append(arch.stem)
                elif formato == "con_extension":
                    items.append(arch.name)
                elif formato == "con_tamano":
                    items.append(f"{arch.name}\t{formatear_tamano(arch.stat().st_size)}")
        except Exception as e:
            self.lbl_conteo_listar.set_text(f"Error listando: {e}")
            return

        self.lista_nombres_actual = items
        total = len(items)
        self.lbl_conteo_listar.set_text(f"✓ {total:,} archivos listados")
        self.buffer_lista.set_text("\n".join(items))

    def _copiar_lista_portapapeles(self, btn):
        # Obtener el texto directamente del buffer visual o de la lista
        start, end = self.buffer_lista.get_bounds()
        texto = self.buffer_lista.get_text(start, end, True).strip()
        if not texto and self.lista_nombres_actual:
            texto = "\n".join(self.lista_nombres_actual).strip()

        if not texto:
            notificar("Listado vacío", "No hay elementos para copiar.")
            return

        # Copiar simultáneamente a Wayland y a X11 (para OnlyOffice/Excel, etc.)
        copiar_al_portapapeles_universal(texto)

        total = len(texto.splitlines())
        self.lbl_conteo_listar.set_text(f"✓ ¡Copiados {total:,} nombres al portapapeles!")
        if btn:
            btn.set_label("✓  ¡COPIADO AL PORTAPAPELES!")
            GLib.timeout_add(2000, lambda: btn.set_label("📋  COPIAR LISTA AL PORTAPAPELES") and False)

        notificar("Nombres copiados", f"Se copiaron {total:,} nombres al portapapeles.")

    def _exportar_dnis_directo(self, btn):
        if not self.carpeta_listar or not self.carpeta_listar.is_dir():
            return
        start, end = self.buffer_lista.get_bounds()
        texto = self.buffer_lista.get_text(start, end, True).strip()
        if not texto:
            notificar("Listado vacío", "No hay elementos para exportar.")
            return
        destino = self.carpeta_listar / "dnis.txt"
        try:
            destino.write_text(texto + "\n", encoding="utf-8")
            total = len(texto.splitlines())
            self.lbl_conteo_listar.set_text(f"✓ Guardado en {destino.name} ({total:,} nombres)")
            notificar("Archivo creado", f"Guardado en {destino.name} ({total:,} nombres)")
        except Exception as e:
            notificar("Error al guardar", str(e), critico=True)

    def _guardar_lista_archivo(self, btn):
        if not self.lista_nombres_actual:
            return

        dialogo = Gtk.FileChooserDialog(
            title="Guardar listado de nombres",
            parent=self.win,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialogo.add_button("Guardar", Gtk.ResponseType.OK)
        dialogo.set_current_name("lista_archivos.txt")
        dialogo.set_do_overwrite_confirmation(True)

        if dialogo.run() == Gtk.ResponseType.OK:
            destino = Path(dialogo.get_filename())
            try:
                destino.write_text("\n".join(self.lista_nombres_actual), encoding="utf-8")
                notificar("Archivo guardado", f"Guardado en: {destino.name}")
            except Exception as e:
                notificar("Error al guardar", str(e), critico=True)
        dialogo.destroy()

    # =========================================================================
    # PESTAÑA 3: CAMBIAR NOMBRES EN LOTE
    # =========================================================================
    def _construir_tab_renombrar(self):
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # Carpeta
        caja.pack_start(self._etiqueta_seccion("CARPETA DE ARCHIVOS A RENOMBRAR"), False, False, 0)

        caja_drop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        caja_drop.get_style_context().add_class("caja-drop")
        caja.pack_start(caja_drop, False, False, 0)

        caja_drop.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        caja_drop.drag_dest_add_uri_targets()
        caja_drop.connect("drag-data-received", self._al_soltar_carpeta_renombrar)

        fila_dir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        caja_drop.pack_start(fila_dir, False, False, 0)

        self.entrada_dir_renombrar = Gtk.Entry()
        self.entrada_dir_renombrar.set_editable(False)
        self.entrada_dir_renombrar.set_text(str(self.carpeta_compartida))
        fila_dir.pack_start(self.entrada_dir_renombrar, True, True, 0)

        btn_elegir = Gtk.Button(label="Examinar...")
        btn_elegir.connect("clicked", self._al_elegir_carpeta_renombrar)
        fila_dir.pack_start(btn_elegir, False, False, 0)

        # Parámetros de renombramiento
        caja.pack_start(self._etiqueta_seccion("REGLAS DE RENOMBRAMIENTO"), False, False, 0)

        # Fila: Filtro y Sufijo (Caso clave del usuario: agregar _FTR)
        fila_reglas1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caja.pack_start(fila_reglas1, False, False, 0)

        fila_reglas1.pack_start(Gtk.Label(label="Filtro de archivos:"), False, False, 0)
        self.combo_filtro_renombrar = Gtk.ComboBoxText()
        for clave, txt in FILTROS_ARCHIVOS:
            self.combo_filtro_renombrar.append(clave, txt)
        self.combo_filtro_renombrar.set_active(0)
        self.combo_filtro_renombrar.connect("changed", lambda *_: self._programar_actualizacion_renombrar())
        fila_reglas1.pack_start(self.combo_filtro_renombrar, False, False, 0)

        fila_reglas1.pack_start(Gtk.Label(label="  Agregar sufijo:"), False, False, 0)
        self.entrada_sufijo = Gtk.Entry()
        self.entrada_sufijo.set_width_chars(10)
        self.entrada_sufijo.set_placeholder_text("ej. _FTR")
        self.entrada_sufijo.set_text("_FTR")  # Valor solicitado por el usuario
        self.entrada_sufijo.connect("changed", lambda *_: self._programar_actualizacion_renombrar())
        fila_reglas1.pack_start(self.entrada_sufijo, False, False, 0)

        fila_reglas1.pack_start(Gtk.Label(label="  Prefijo:"), False, False, 0)
        self.entrada_prefijo = Gtk.Entry()
        self.entrada_prefijo.set_width_chars(10)
        self.entrada_prefijo.set_placeholder_text("opcional")
        self.entrada_prefijo.connect("changed", lambda *_: self._programar_actualizacion_renombrar())
        fila_reglas1.pack_start(self.entrada_prefijo, True, True, 0)

        # Fila Buscar y Reemplazar
        fila_reglas2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caja.pack_start(fila_reglas2, False, False, 0)

        fila_reglas2.pack_start(Gtk.Label(label="Buscar texto:"), False, False, 0)
        self.entrada_buscar = Gtk.Entry()
        self.entrada_buscar.set_placeholder_text("texto a buscar")
        self.entrada_buscar.connect("changed", lambda *_: self._programar_actualizacion_renombrar())
        fila_reglas2.pack_start(self.entrada_buscar, True, True, 0)

        fila_reglas2.pack_start(Gtk.Label(label="Reemplazar con:"), False, False, 0)
        self.entrada_reemplazar = Gtk.Entry()
        self.entrada_reemplazar.set_placeholder_text("nuevo texto")
        self.entrada_reemplazar.connect("changed", lambda *_: self._programar_actualizacion_renombrar())
        fila_reglas2.pack_start(self.entrada_reemplazar, True, True, 0)

        # Fila Vista Previa
        fila_encabezado_prev = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caja.pack_start(fila_encabezado_prev, False, False, 0)

        fila_encabezado_prev.pack_start(self._etiqueta_seccion("VISTA PREVIA EN TIEMPO REAL"), True, True, 0)
        self.lbl_conteo_renombrar = Gtk.Label(label="0 archivos a renombrar")
        self.lbl_conteo_renombrar.get_style_context().add_class("info-secundaria")
        fila_encabezado_prev.pack_end(self.lbl_conteo_renombrar, False, False, 0)

        # Tabla TreeView
        scroll_tree = Gtk.ScrolledWindow()
        scroll_tree.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        caja.pack_start(scroll_tree, True, True, 0)

        # Columnas: Nombre Original, Nombre Nuevo, Estado
        self.store_renombrar = Gtk.ListStore(str, str, str)
        self.tree_renombrar = Gtk.TreeView(model=self.store_renombrar)
        self.tree_renombrar.set_headers_visible(True)

        col_orig = Gtk.TreeViewColumn("Nombre actual", Gtk.CellRendererText(), text=0)
        col_orig.set_resizable(True)
        col_orig.set_min_width(220)
        self.tree_renombrar.append_column(col_orig)

        col_nuevo = Gtk.TreeViewColumn("➔ Nuevo nombre", Gtk.CellRendererText(), text=1)
        col_nuevo.set_resizable(True)
        col_nuevo.set_min_width(260)
        self.tree_renombrar.append_column(col_nuevo)

        col_estado = Gtk.TreeViewColumn("Estado", Gtk.CellRendererText(), text=2)
        col_estado.set_resizable(True)
        self.tree_renombrar.append_column(col_estado)

        scroll_tree.add(self.tree_renombrar)

        # Barra de progreso para renombrar
        self.barra_progreso_renombrar = Gtk.ProgressBar()
        self.barra_progreso_renombrar.set_fraction(0.0)
        self.barra_progreso_renombrar.set_text("Listo para renombrar")
        self.barra_progreso_renombrar.set_show_text(True)
        caja.pack_start(self.barra_progreso_renombrar, False, False, 0)

        # Botón de ejecución
        fila_acciones = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caja.pack_start(fila_acciones, False, False, 4)

        self.btn_ejecutar_renombrar = Gtk.Button(label="✏   RENOMBRAR ARCHIVOS EN LOTE")
        self.btn_ejecutar_renombrar.get_style_context().add_class("btn-principal")
        self.btn_ejecutar_renombrar.connect("clicked", self._confirmar_y_ejecutar_renombramiento)
        fila_acciones.pack_start(self.btn_ejecutar_renombrar, True, True, 0)

        self.btn_abrir_carpeta_renombrar = Gtk.Button(label="📁 Abrir carpeta")
        self.btn_abrir_carpeta_renombrar.connect("clicked", lambda *_: subprocess.Popen(["xdg-open", str(self.carpeta_renombrar)]))
        fila_acciones.pack_start(self.btn_abrir_carpeta_renombrar, False, False, 0)

        return caja

    def _actualizar_carpeta_renombrar(self, ruta: Path):
        self.carpeta_renombrar = ruta
        self.entrada_dir_renombrar.set_text(str(ruta))
        self._cargar_archivos_renombrar()

    def _al_elegir_carpeta_renombrar(self, btn):
        dialogo = Gtk.FileChooserDialog(
            title="Seleccionar carpeta a renombrar",
            parent=self.win,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialogo.add_button("Seleccionar", Gtk.ResponseType.OK)
        dialogo.set_current_folder(str(self.carpeta_renombrar))

        if dialogo.run() == Gtk.ResponseType.OK:
            self.carpeta_compartida = Path(dialogo.get_filename())
            self._actualizar_carpeta_renombrar(self.carpeta_compartida)
        dialogo.destroy()

    def _al_soltar_carpeta_renombrar(self, widget, context, x, y, data, info, time):
        uris = data.get_uris()
        context.finish(True, False, time)
        if not uris:
            return
        p = Path(unquote(urlparse(uris[0]).path))
        if p.exists():
            carpeta = p if p.is_dir() else p.parent
            self.carpeta_compartida = carpeta
            self._actualizar_carpeta_renombrar(self.carpeta_compartida)

    def _programar_actualizacion_renombrar(self):
        if self.debounce_timer_renombrar:
            GLib.source_remove(self.debounce_timer_renombrar)
        self.debounce_timer_renombrar = GLib.timeout_add(150, self._actualizar_vista_previa_renombrar)

    def _cargar_archivos_renombrar(self):
        if not self.carpeta_renombrar or not self.carpeta_renombrar.is_dir():
            self.store_renombrar.clear()
            self.lbl_conteo_renombrar.set_text("Carpeta no válida")
            return

        filtro = self.combo_filtro_renombrar.get_active_id() or "imagenes"
        archivos = []
        try:
            for item in sorted(self.carpeta_renombrar.iterdir()):
                if not item.is_file():
                    continue
                ext = item.suffix.lower()
                if filtro == "imagenes" and ext not in EXTENSIONES_IMAGEN:
                    continue
                elif filtro == "jpg" and ext not in (".jpg", ".jpeg"):
                    continue
                elif filtro == "pdf" and ext != ".pdf":
                    continue
                archivos.append(item)
        except Exception:
            pass

        self.archivos_renombrar = archivos
        self._actualizar_vista_previa_renombrar()

    def _actualizar_vista_previa_renombrar(self):
        self.debounce_timer_renombrar = None
        self.store_renombrar.clear()

        sufijo = self.entrada_sufijo.get_text()
        prefijo = self.entrada_prefijo.get_text()
        buscar = self.entrada_buscar.get_text()
        reemplazar = self.entrada_reemplazar.get_text()

        cambios = 0
        conflictos = 0

        # Para chequeo de colisiones
        nombres_ocupados = {a.name for a in self.archivos_renombrar}

        for arch in self.archivos_renombrar:
            stem = arch.stem
            ext = arch.suffix

            if buscar:
                stem = stem.replace(buscar, reemplazar)

            nuevo_stem = f"{prefijo}{stem}{sufijo}"
            nuevo_nombre = f"{nuevo_stem}{ext}"

            if nuevo_nombre == arch.name:
                estado = "Sin cambios"
            elif nuevo_nombre in nombres_ocupados and nuevo_nombre != arch.name:
                estado = "⚠ Conflicto (ya existe)"
                conflictos += 1
                cambios += 1
            else:
                estado = "✓ Listo para renombrar"
                cambios += 1

            self.store_renombrar.append([arch.name, nuevo_nombre, estado])

        total = len(self.archivos_renombrar)
        self.lbl_conteo_renombrar.set_text(
            f"✓ {cambios:,} de {total:,} archivos cambiarán de nombre"
        )
        return False

    def _confirmar_y_ejecutar_renombramiento(self, btn):
        if self.en_proceso_renombrar:
            return

        if not self.archivos_renombrar:
            notificar("Sin archivos", "No hay archivos para renombrar en la carpeta.")
            return

        dialogo = Gtk.MessageDialog(
            transient_for=self.win,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="¿Confirmar renombramiento en lote?",
        )
        dialogo.format_secondary_text(
            f"Se aplicarán las reglas a los archivos en:\n{self.carpeta_renombrar}\n\n"
            f"Ejemplo: 60178873.jpg ➔ 60178873{self.entrada_sufijo.get_text()}.jpg\n"
            "Esta operación modificará los nombres directamente en el disco."
        )

        respuesta = dialogo.run()
        dialogo.destroy()

        if respuesta != Gtk.ResponseType.YES:
            return

        self.en_proceso_renombrar = True
        self.btn_ejecutar_renombrar.set_sensitive(False)

        threading.Thread(target=self._worker_renombrar, daemon=True).start()

    def _worker_renombrar(self):
        sufijo = self.entrada_sufijo.get_text()
        prefijo = self.entrada_prefijo.get_text()
        buscar = self.entrada_buscar.get_text()
        reemplazar = self.entrada_reemplazar.get_text()

        total = len(self.archivos_renombrar)
        renombrados = 0
        omitidos = 0
        errores = 0

        for idx, arch in enumerate(self.archivos_renombrar, start=1):
            stem = arch.stem
            ext = arch.suffix

            if buscar:
                stem = stem.replace(buscar, reemplazar)

            nuevo_stem = f"{prefijo}{stem}{sufijo}"
            nuevo_nombre = f"{nuevo_stem}{ext}"
            destino = arch.parent / nuevo_nombre

            if nuevo_nombre == arch.name:
                omitidos += 1
                continue

            try:
                if destino.exists() and destino != arch:
                    errores += 1
                    continue
                arch.rename(destino)
                renombrados += 1
            except Exception:
                errores += 1

            fraccion = idx / total
            GLib.idle_add(self.barra_progreso_renombrar.set_fraction, fraccion)
            GLib.idle_add(self.barra_progreso_renombrar.set_text, f"{idx}/{total} ({renombrados} renombrados)")

        def _finalizar():
            self.en_proceso_renombrar = False
            self.btn_ejecutar_renombrar.set_sensitive(True)
            self.barra_progreso_renombrar.set_fraction(1.0)
            self.barra_progreso_renombrar.set_text(f"Completado: {renombrados:,} archivos renombrados")
            notificar(
                "Renombramiento finalizado",
                f"Se renombraron {renombrados:,} archivos con éxito.",
            )
            # Recargar la lista de archivos
            self._cargar_archivos_renombrar()
            return False

        GLib.idle_add(_finalizar)


    # =========================================================================
    # PESTAÑA 4: EXTRAER / COPIAR POR LISTA
    # =========================================================================
    def _construir_tab_extraer(self):
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # 1. Parámetros
        caja.pack_start(self._etiqueta_seccion("1. CARPETAS Y PARÁMETROS"), False, False, 0)

        fila_origen = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        caja.pack_start(fila_origen, False, False, 0)

        fila_origen.pack_start(Gtk.Label(label="Buscar en:"), False, False, 0)
        self.entrada_dir_extraer = Gtk.Entry()
        self.entrada_dir_extraer.set_editable(False)
        self.entrada_dir_extraer.set_text(str(self.carpeta_compartida))
        fila_origen.pack_start(self.entrada_dir_extraer, True, True, 0)

        btn_examinar_origen = Gtk.Button(label="Examinar...")
        btn_examinar_origen.connect("clicked", self._al_elegir_carpeta_extraer)
        fila_origen.pack_start(btn_examinar_origen, False, False, 0)

        self.chk_subcarpetas_extraer = Gtk.CheckButton(label="Subcarpetas")
        self.chk_subcarpetas_extraer.connect("toggled", lambda *_: self._programar_analisis_extraer())
        fila_origen.pack_start(self.chk_subcarpetas_extraer, False, False, 0)

        fila_opts = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        caja.pack_start(fila_opts, False, False, 0)

        fila_opts.pack_start(Gtk.Label(label="Coincidencia:"), False, False, 0)
        self.combo_modo_extraer = Gtk.ComboBoxText()
        self.combo_modo_extraer.append("base", "Nombre base (ej. 60178873 encuentra .jpg/.png)")
        self.combo_modo_extraer.append("prefijo", "Prefijo (ej. 60178873 encuentra 60178873_FTR.jpg)")
        self.combo_modo_extraer.append("exacto", "Exacto (con extensión)")
        self.combo_modo_extraer.set_active(0)
        self.combo_modo_extraer.connect("changed", lambda *_: self._programar_analisis_extraer())
        fila_opts.pack_start(self.combo_modo_extraer, False, False, 0)

        fila_opts.pack_start(Gtk.Label(label="  Acción:"), False, False, 0)
        self.combo_accion_extraer = Gtk.ComboBoxText()
        self.combo_accion_extraer.append("copiar", "Copiar (conserva origen)")
        self.combo_accion_extraer.append("mover", "Mover (extrae del origen)")
        self.combo_accion_extraer.set_active(0)
        self.combo_accion_extraer.connect("changed", lambda *_: self._actualizar_etiqueta_boton_extraer())
        fila_opts.pack_start(self.combo_accion_extraer, False, False, 0)

        self.btn_elegir_dest_extraer = Gtk.Button(label="Destino: subcarpeta 'copiados/'")
        self.btn_elegir_dest_extraer.connect("clicked", self._al_elegir_dest_extraer)
        fila_opts.pack_start(self.btn_elegir_dest_extraer, True, True, 0)

        # 2. Panel Dividido
        caja.pack_start(self._etiqueta_seccion("2. LISTA A BUSCAR Y RESULTADOS"), False, False, 0)

        paned = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        paned.set_homogeneous(True)
        caja.pack_start(paned, True, True, 0)

        # Columna Izquierda: Entrada
        caja_izq = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        paned.pack_start(caja_izq, True, True, 0)

        fila_izq_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        caja_izq.pack_start(fila_izq_header, False, False, 0)

        lbl_izq_tit = Gtk.Label(label="LISTA (1 por línea):")
        lbl_izq_tit.get_style_context().add_class("etiqueta-seccion")
        fila_izq_header.pack_start(lbl_izq_tit, False, False, 0)

        btn_pegar_clip = Gtk.Button(label="📋 Pegar")
        btn_pegar_clip.set_tooltip_text("Pegar lista desde portapapeles (Wayland / Excel / X11)")
        btn_pegar_clip.connect("clicked", self._pegar_portapapeles_extraer)
        fila_izq_header.pack_start(btn_pegar_clip, False, False, 0)

        btn_cargar_arch = Gtk.Button(label="📁 Cargar")
        btn_cargar_arch.set_tooltip_text("Cargar lista desde archivo .txt o .csv")
        btn_cargar_arch.connect("clicked", self._cargar_archivo_extraer)
        fila_izq_header.pack_start(btn_cargar_arch, False, False, 0)

        btn_limpiar = Gtk.Button(label="🧹")
        btn_limpiar.set_tooltip_text("Limpiar lista")
        btn_limpiar.connect("clicked", lambda *_: self.buffer_lista_extraer.set_text(""))
        fila_izq_header.pack_start(btn_limpiar, False, False, 0)

        self.lbl_conteo_lista_extraer = Gtk.Label(label="0 nombres")
        self.lbl_conteo_lista_extraer.get_style_context().add_class("info-secundaria")
        fila_izq_header.pack_end(self.lbl_conteo_lista_extraer, False, False, 0)

        scroll_izq = Gtk.ScrolledWindow()
        scroll_izq.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        caja_izq.pack_start(scroll_izq, True, True, 0)

        self.txt_lista_extraer = Gtk.TextView()
        self.txt_lista_extraer.set_wrap_mode(Gtk.WrapMode.NONE)
        scroll_izq.add(self.txt_lista_extraer)
        self.buffer_lista_extraer = self.txt_lista_extraer.get_buffer()
        self.buffer_lista_extraer.connect("changed", lambda *_: self._programar_analisis_extraer())

        # Columna Derecha: Resultados
        caja_der = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        paned.pack_start(caja_der, True, True, 0)

        fila_tabs_res = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        caja_der.pack_start(fila_tabs_res, False, False, 0)

        self.btn_ver_encontrados = Gtk.Button(label="✓ Encontrados (0)")
        self.btn_ver_encontrados.get_style_context().add_class("tab-btn")
        self.btn_ver_encontrados.get_style_context().add_class("tab-activa")
        self.btn_ver_encontrados.connect("clicked", lambda *_: self._cambiar_subvista_extraer("encontrados"))
        fila_tabs_res.pack_start(self.btn_ver_encontrados, True, True, 0)

        self.btn_ver_faltantes = Gtk.Button(label="✗ Faltantes (0)")
        self.btn_ver_faltantes.get_style_context().add_class("tab-btn")
        self.btn_ver_faltantes.connect("clicked", lambda *_: self._cambiar_subvista_extraer("faltantes"))
        fila_tabs_res.pack_start(self.btn_ver_faltantes, True, True, 0)

        self.stack_res = Gtk.Stack()
        self.stack_res.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        caja_der.pack_start(self.stack_res, True, True, 0)

        # Vista Encontrados
        scroll_enc = Gtk.ScrolledWindow()
        scroll_enc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.store_encontrados = Gtk.ListStore(str, str)
        self.tree_encontrados = Gtk.TreeView(model=self.store_encontrados)

        col_arch = Gtk.TreeViewColumn("Archivo encontrado", Gtk.CellRendererText(), text=0)
        col_arch.set_resizable(True)
        col_arch.set_min_width(200)
        self.tree_encontrados.append_column(col_arch)

        col_tam = Gtk.TreeViewColumn("Tamaño", Gtk.CellRendererText(), text=1)
        self.tree_encontrados.append_column(col_tam)

        scroll_enc.add(self.tree_encontrados)
        self.stack_res.add_named(scroll_enc, "encontrados")

        # Vista Faltantes
        caja_falt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll_falt = Gtk.ScrolledWindow()
        scroll_falt.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.txt_faltantes = Gtk.TextView()
        self.txt_faltantes.set_editable(False)
        scroll_falt.add(self.txt_faltantes)
        self.buffer_faltantes = self.txt_faltantes.get_buffer()
        caja_falt.pack_start(scroll_falt, True, True, 0)

        self.btn_copiar_faltantes = Gtk.Button(label="📋 Copiar lista de faltantes")
        self.btn_copiar_faltantes.connect("clicked", self._copiar_faltantes_extraer)
        caja_falt.pack_start(self.btn_copiar_faltantes, False, False, 0)
        self.stack_res.add_named(caja_falt, "faltantes")

        # 3. Barra de progreso y Ejecución
        self.barra_progreso_extraer = Gtk.ProgressBar()
        self.barra_progreso_extraer.set_fraction(0.0)
        self.barra_progreso_extraer.set_text("Listo para buscar")
        self.barra_progreso_extraer.set_show_text(True)
        caja.pack_start(self.barra_progreso_extraer, False, False, 0)

        fila_acciones = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        caja.pack_start(fila_acciones, False, False, 4)

        self.btn_ejecutar_extraer = Gtk.Button(label="📦  COPIAR ARCHIVOS ENCONTRADOS")
        self.btn_ejecutar_extraer.get_style_context().add_class("btn-principal")
        self.btn_ejecutar_extraer.set_sensitive(False)
        self.btn_ejecutar_extraer.connect("clicked", self._confirmar_y_ejecutar_extraer)
        fila_acciones.pack_start(self.btn_ejecutar_extraer, True, True, 0)

        self.btn_abrir_dest_extraer = Gtk.Button(label="📁 Abrir destino")
        self.btn_abrir_dest_extraer.set_sensitive(False)
        self.btn_abrir_dest_extraer.connect("clicked", self._abrir_destino_extraer)
        fila_acciones.pack_start(self.btn_abrir_dest_extraer, False, False, 0)

        return caja

    def _actualizar_carpeta_extraer(self, ruta: Path):
        self.carpeta_origen_extraer = ruta
        self.entrada_dir_extraer.set_text(str(ruta))
        if not self.carpeta_destino_extraer:
            self.btn_elegir_dest_extraer.set_label(f"Destino: {ruta.name}/copiados/")
        self._programar_analisis_extraer()

    def _al_elegir_carpeta_extraer(self, btn):
        dialogo = Gtk.FileChooserDialog(
            title="Seleccionar carpeta donde buscar",
            parent=self.win,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialogo.add_button("Seleccionar", Gtk.ResponseType.OK)
        dialogo.set_current_folder(str(self.carpeta_origen_extraer))

        if dialogo.run() == Gtk.ResponseType.OK:
            self.carpeta_compartida = Path(dialogo.get_filename())
            self._actualizar_carpeta_extraer(self.carpeta_compartida)
        dialogo.destroy()

    def _al_elegir_dest_extraer(self, btn):
        dialogo = Gtk.FileChooserDialog(
            title="Seleccionar carpeta de destino",
            parent=self.win,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialogo.add_button("Seleccionar", Gtk.ResponseType.OK)
        base = self.carpeta_destino_extraer or self.carpeta_origen_extraer
        dialogo.set_current_folder(str(base))

        if dialogo.run() == Gtk.ResponseType.OK:
            self.carpeta_destino_extraer = Path(dialogo.get_filename())
            self.btn_elegir_dest_extraer.set_label(f"Destino: {self.carpeta_destino_extraer.name}/")
        dialogo.destroy()

    def _pegar_portapapeles_extraer(self, btn):
        texto = ""
        # 1. Probar Wayland
        if shutil.which("wl-copy"):
            try:
                res = subprocess.run(["wl-paste", "--no-newline"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0 and res.stdout:
                    texto = res.stdout
            except Exception:
                pass
        # 2. Probar X11
        if not texto:
            bin_xsel = obtener_bin_xsel()
            display = os.environ.get("DISPLAY", ":0")
            if bin_xsel and display:
                try:
                    res = subprocess.run([bin_xsel, "--display", display, "-b", "-o"], capture_output=True, text=True, timeout=2)
                    if res.returncode == 0 and res.stdout:
                        texto = res.stdout
                except Exception:
                    pass

        if texto:
            self.buffer_lista_extraer.set_text(texto)
            self._analizar_extraer()
            notificar("Lista pegada", "Se cargó la lista desde el portapapeles.")
        else:
            notificar("Portapapeles vacío", "No hay texto copiado.")

    def _cargar_archivo_extraer(self, btn):
        dialogo = Gtk.FileChooserDialog(
            title="Cargar archivo de lista",
            parent=self.win,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialogo.add_button("Abrir", Gtk.ResponseType.OK)
        filtro = Gtk.FileFilter()
        filtro.set_name("Archivos de texto (*.txt, *.csv)")
        filtro.add_pattern("*.txt")
        filtro.add_pattern("*.csv")
        dialogo.add_filter(filtro)

        if dialogo.run() == Gtk.ResponseType.OK:
            try:
                contenido = Path(dialogo.get_filename()).read_text(encoding="utf-8", errors="ignore")
                self.buffer_lista_extraer.set_text(contenido)
                self._analizar_extraer()
            except Exception as e:
                notificar("Error al leer archivo", str(e), critico=True)
        dialogo.destroy()

    def _programar_analisis_extraer(self):
        if self.debounce_timer_extraer:
            GLib.source_remove(self.debounce_timer_extraer)
        self.debounce_timer_extraer = GLib.timeout_add(150, self._analizar_extraer)

    def _analizar_extraer(self):
        self.debounce_timer_extraer = None
        start, end = self.buffer_lista_extraer.get_bounds()
        texto_raw = self.buffer_lista_extraer.get_text(start, end, True)

        lineas = [l.strip() for l in texto_raw.splitlines() if l.strip()]
        elementos = []
        for l in lineas:
            # Si viene copiado de Excel con múltiples columnas, tomamos la primera
            dni = l.split("\t")[0].strip().strip('\"\'')
            if dni:
                elementos.append(dni)

        total_solicitados = len(elementos)
        self.lbl_conteo_lista_extraer.set_text(f"{total_solicitados:,} nombres")

        if total_solicitados == 0 or not self.carpeta_origen_extraer or not self.carpeta_origen_extraer.is_dir():
            self.store_encontrados.clear()
            self.buffer_faltantes.set_text("")
            self.btn_ver_encontrados.set_label("✓ Encontrados (0)")
            self.btn_ver_faltantes.set_label("✗ Faltantes (0)")
            self.btn_ejecutar_extraer.set_sensitive(False)
            self.btn_ejecutar_extraer.set_label("📦  COPIAR ARCHIVOS ENCONTRADOS")
            return False

        # Indexar carpeta de origen
        modo = self.combo_modo_extraer.get_active_id() or "base"
        sub = self.chk_subcarpetas_extraer.get_active()
        patron = "**/*" if sub else "*"

        mapa_stem = {}
        mapa_name = {}
        todos_archivos = []
        try:
            for a in self.carpeta_origen_extraer.glob(patron):
                if a.is_file():
                    todos_archivos.append(a)
                    mapa_stem.setdefault(a.stem.lower(), []).append(a)
                    mapa_name.setdefault(a.name.lower(), []).append(a)
        except Exception:
            pass

        archivos_encontrados = []
        faltantes = []
        encontrados_set = set()

        for item in elementos:
            coincidencias = []
            item_limpio = item.lower()
            item_stem = Path(item).stem.lower()

            if modo == "base":
                coincidencias = mapa_stem.get(item_stem) or mapa_stem.get(item_limpio) or mapa_name.get(item_limpio) or []
            elif modo == "prefijo":
                coincidencias = [a for a in todos_archivos if a.stem.lower().startswith(item_limpio) or a.name.lower().startswith(item_limpio)]
            elif modo == "exacto":
                coincidencias = mapa_name.get(item_limpio) or []

            if coincidencias:
                for c in coincidencias:
                    if c not in encontrados_set:
                        encontrados_set.add(c)
                        archivos_encontrados.append(c)
            else:
                faltantes.append(item)

        self.archivos_encontrados_extraer = archivos_encontrados
        self.elementos_faltantes_extraer = faltantes

        # Actualizar vistas
        self.store_encontrados.clear()
        for a in archivos_encontrados:
            tam_str = formatear_tamano(a.stat().st_size) if a.exists() else "0 B"
            self.store_encontrados.append([a.name, tam_str])

        self.buffer_faltantes.set_text("\n".join(faltantes))

        n_enc = len(archivos_encontrados)
        n_fal = len(faltantes)
        self.btn_ver_encontrados.set_label(f"✓ Encontrados ({n_enc:,})")
        self.btn_ver_faltantes.set_label(f"✗ Faltantes ({n_fal:,})")

        self._actualizar_etiqueta_boton_extraer()
        self.btn_ejecutar_extraer.set_sensitive(n_enc > 0)
        return False

    def _actualizar_etiqueta_boton_extraer(self):
        accion = (self.combo_accion_extraer.get_active_id() or "copiar").upper()
        n = len(self.archivos_encontrados_extraer)
        self.btn_ejecutar_extraer.set_label(f"📦  {accion} {n:,} ARCHIVOS ENCONTRADOS")

    def _cambiar_subvista_extraer(self, subvista):
        self.stack_res.set_visible_child_name(subvista)
        if subvista == "encontrados":
            self.btn_ver_encontrados.get_style_context().add_class("tab-activa")
            self.btn_ver_faltantes.get_style_context().remove_class("tab-activa")
        else:
            self.btn_ver_faltantes.get_style_context().add_class("tab-activa")
            self.btn_ver_encontrados.get_style_context().remove_class("tab-activa")

    def _copiar_faltantes_extraer(self, btn):
        texto = "\n".join(self.elementos_faltantes_extraer)
        if not texto:
            notificar("Sin faltantes", "No hay elementos faltantes para copiar.")
            return
        copiar_al_portapapeles_universal(texto)
        total = len(self.elementos_faltantes_extraer)
        notificar("Faltantes copiados", f"Se copiaron {total:,} faltantes al portapapeles.")

    def _confirmar_y_ejecutar_extraer(self, btn):
        if self.en_proceso_extraer or not self.archivos_encontrados_extraer:
            return

        mover = (self.combo_accion_extraer.get_active_id() == "mover")
        accion_str = "mover" if mover else "copiar"

        dir_dest = self.carpeta_destino_extraer or (self.carpeta_origen_extraer / "copiados")

        dialogo = Gtk.MessageDialog(
            transient_for=self.win,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"¿Confirmar {accion_str} {len(self.archivos_encontrados_extraer):,} archivos?",
        )
        dialogo.format_secondary_text(
            f"Origen: {self.carpeta_origen_extraer}\n"
            f"Destino: {dir_dest}\n\n"
            f"{'Se moverán y quitarán del origen.' if mover else 'Se conservarán las imágenes originales intactas.'}"
        )
        resp = dialogo.run()
        dialogo.destroy()

        if resp != Gtk.ResponseType.YES:
            return

        try:
            dir_dest.mkdir(parents=True, exist_ok=True)
            self.ultima_carpeta_salida_extraer = dir_dest
        except Exception as e:
            notificar("Error destino", str(e), critico=True)
            return

        self.en_proceso_extraer = True
        self.btn_ejecutar_extraer.set_sensitive(False)
        self.btn_abrir_dest_extraer.set_sensitive(False)

        threading.Thread(
            target=self._worker_copia_extraer,
            args=(list(self.archivos_encontrados_extraer), dir_dest, mover),
            daemon=True,
        ).start()

    def _worker_copia_extraer(self, archivos, dir_destino, mover):
        total = len(archivos)
        exitos = 0
        errores = 0

        for idx, a in enumerate(archivos, start=1):
            dest = dir_destino / a.name
            try:
                if mover:
                    shutil.move(str(a), str(dest))
                else:
                    shutil.copy2(str(a), str(dest))
                exitos += 1
            except Exception:
                errores += 1

            fraccion = idx / total
            GLib.idle_add(self.barra_progreso_extraer.set_fraction, fraccion)
            GLib.idle_add(self.barra_progreso_extraer.set_text, f"{idx}/{total} ({exitos} procesados)")

        def _finalizar():
            self.en_proceso_extraer = False
            self.btn_ejecutar_extraer.set_sensitive(True)
            self.btn_abrir_dest_extraer.set_sensitive(True)
            self.barra_progreso_extraer.set_fraction(1.0)
            accion_txt = "movidos" if mover else "copiados"
            self.barra_progreso_extraer.set_text(f"✓ {exitos:,} archivos {accion_txt} a {dir_destino.name}/")
            notificar(
                f"Proceso completado",
                f"Se han {accion_txt} {exitos:,} archivos en {dir_destino.name}/",
            )
            if mover:
                self._analizar_extraer()
            return False

        GLib.idle_add(_finalizar)

    def _abrir_destino_extraer(self, btn):
        if self.ultima_carpeta_salida_extraer and self.ultima_carpeta_salida_extraer.exists():
            subprocess.Popen(["xdg-open", str(self.ultima_carpeta_salida_extraer)])


def main():
    OptimizadorApp()
    Gtk.main()


if __name__ == "__main__":
    main()
