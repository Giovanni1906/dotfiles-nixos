#!/usr/bin/env python3
# Calendario flotante del reloj (clic derecho en Waybar).
# Es una capa del escritorio: se cierra con Escape, con un clic fuera
# o con otro clic derecho en el reloj.

from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

TEMA = Path.home() / "dotfiles/tema/tema.conf"

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
CORTOS = ["lu", "ma", "mi", "ju", "vi", "sá", "do"]

TEMA_BASE = {
    "ACENTO": "#3399cc",
    "FONDO": "#0a1e3c",
    "SUPERFICIE": "#133e7c",
    "TEXTO": "#cdd6f4",
    "TEXTO_TENUE": "#6c7086",
    "RADIO": "10",
    "BORDE": "2",
    "FUENTE": "JetBrainsMono Nerd Font",
    "OPACIDAD_MENU": "0.95",
}


def sin_comentario(linea):
    """Quita el comentario final. Los colores van entre comillas y empiezan por #."""
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
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def fecha_larga(dia):
    return f"{DIAS[dia.weekday()]} {dia.day} de {MESES[dia.month - 1]}"


def fecha_corta(dia):
    return f"{dia.day} {MESES[dia.month - 1]}"


def resumen(inicio, fin):
    """Línea de fechas y la cuenta. Los días entre ellas no incluyen los extremos."""
    if inicio is None:
        return "Elige una fecha", "Luego otra, para contar los días"
    if fin is None:
        return fecha_larga(inicio), "Elige otra fecha"
    primero, ultimo = (inicio, fin) if inicio <= fin else (fin, inicio)
    dias = (ultimo - primero).days
    if dias == 0:
        return fecha_larga(primero), "Es el mismo día"
    entre = "1 día entre ellas" if dias == 1 else f"{dias} días entre ellas"
    return f"{fecha_corta(primero)}  →  {fecha_corta(ultimo)}", f"{entre} · {dias + 1} contando ambas"


class Calendario:
    def __init__(self):
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

        self.Gdk = Gdk
        self.GLib = GLib
        self.Gtk = Gtk
        self.Layer = GtkLayerShell
        self.tema = leer_tema()
        self.inicio = None
        self.fin = None
        self.vista = date.today()
        self.listo = False
        self._rueda_acum = 0
        self._montar()

    def _css(self):
        t = self.tema
        fondo = rgba(t["FONDO"], t["OPACIDAD_MENU"])
        superficie = rgba(t["SUPERFICIE"], "0.55")
        rango = rgba(t["ACENTO"], "0.28")
        linea = rgba(t["ACENTO"], "0.35")
        fuente = t["FUENTE"]
        css = f"""
        window, eventbox {{ background-color: rgba(0, 0, 0, 0); }}
        * {{ font-family: "{fuente}"; }}
        .panel {{
            background-color: {fondo};
            border: {t["BORDE"]}px solid {t["ACENTO"]};
            border-radius: {t["RADIO"]}px;
            padding: 12px 12px 10px 12px;
        }}
        button {{
            background-image: none;
            background-color: transparent;
            border: none;
            box-shadow: none;
            outline: none;
            color: {t["TEXTO"]};
            border-radius: 8px;
            padding: 2px 8px;
        }}
        button:hover {{ background-color: {superficie}; background-image: none; }}
        .mes {{ font-size: 15px; font-weight: 700; color: {t["TEXTO"]}; }}
        .semana {{ color: {t["TEXTO_TENUE"]}; font-size: 11px; }}
        .dia {{ min-width: 40px; min-height: 32px; padding: 0; }}
        .dia label {{ color: {t["TEXTO"]}; }}
        .dia.otro label {{ color: {t["TEXTO_TENUE"]}; }}
        .dia.hoy {{ border: 1px solid {t["ACENTO"]}; box-shadow: none; }}
        .dia.elegido, .dia.elegido:hover {{
            background-color: {t["ACENTO"]};
            background-image: none;
            border: none;
            box-shadow: none;
        }}
        .dia.elegido label {{ color: {t["FONDO"]}; }}
        .dia.rango, .dia.rango:hover {{
            background-color: {rango};
            background-image: none;
        }}
        .fecha {{ font-weight: 700; color: {t["TEXTO"]}; }}
        .cuenta {{ color: {t["TEXTO_TENUE"]}; }}
        separator {{ background-color: {linea}; min-height: 1px; }}
        """
        proveedor = self.Gtk.CssProvider()
        proveedor.load_from_data(css.encode())
        self.Gtk.StyleContext.add_provider_for_screen(
            self.Gdk.Screen.get_default(),
            proveedor,
            self.Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _montar(self):
        Gtk = self.Gtk
        self.win = Gtk.Window()
        self.win.set_decorated(False)
        self.win.set_app_paintable(True)
        visual = self.win.get_screen().get_rgba_visual()
        if visual is not None:
            self.win.set_visual(visual)
        self._capa()
        self._css()

        fondo = Gtk.EventBox()
        fondo.connect("button-press-event", lambda *_: self.cerrar() or True)
        self.win.add(fondo)

        hueco = Gtk.Box()
        hueco.set_halign(Gtk.Align.END)
        hueco.set_valign(Gtk.Align.START)
        hueco.set_margin_top(4)
        hueco.set_margin_end(8)
        fondo.add(hueco)

        self.panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.panel.set_size_request(348, -1)
        self.panel.get_style_context().add_class("panel")
        marco = Gtk.EventBox()
        marco.add(self.panel)
        marco.connect("button-press-event", lambda *_: True)
        hueco.pack_start(marco, False, False, 0)

        cabeza = Gtk.Box(spacing=4)
        self.panel.pack_start(cabeza, False, False, 0)
        cabeza.pack_start(self._boton("‹", lambda *_: self.mover_mes(-1)), False, False, 0)
        self.mes = Gtk.Label()
        self.mes.get_style_context().add_class("mes")
        self.mes.set_hexpand(True)
        cabeza.pack_start(self.mes, True, True, 0)
        cabeza.pack_start(self._boton("›", lambda *_: self.mover_mes(1)), False, False, 0)
        cabeza.pack_start(self._boton("Hoy", lambda *_: self.elegir(date.today())), False, False, 0)

        self.rejilla = Gtk.Grid(column_homogeneous=True)
        self.panel.pack_start(self.rejilla, False, False, 0)
        self.rejilla.connect("scroll-event", self._rueda)
        self.rejilla.add_events(self.Gdk.EventMask.SCROLL_MASK | self.Gdk.EventMask.SMOOTH_SCROLL_MASK)

        self.panel.pack_start(Gtk.Separator(), False, False, 0)
        self.fecha = Gtk.Label()
        self.fecha.set_halign(Gtk.Align.START)
        self.fecha.set_line_wrap(True)
        self.fecha.set_max_width_chars(36)
        self.fecha.get_style_context().add_class("fecha")
        self.panel.pack_start(self.fecha, False, False, 0)
        self.cuenta = Gtk.Label()
        self.cuenta.set_halign(Gtk.Align.START)
        self.cuenta.set_line_wrap(True)
        self.cuenta.set_max_width_chars(36)
        self.cuenta.get_style_context().add_class("cuenta")
        self.panel.pack_start(self.cuenta, False, False, 0)

        self.win.connect("key-press-event", self._tecla)
        self.win.connect("focus-out-event", self._foco_fuera)
        self.win.connect("destroy", Gtk.main_quit)

    def _boton(self, texto, accion):
        boton = self.Gtk.Button(label=texto)
        boton.connect("clicked", accion)
        return boton

    def _capa(self):
        Layer = self.Layer
        win = self.win
        Layer.init_for_window(win)
        Layer.set_layer(win, Layer.Layer.OVERLAY)
        Layer.set_namespace(win, "calendario")
        for borde in (Layer.Edge.TOP, Layer.Edge.RIGHT, Layer.Edge.BOTTOM, Layer.Edge.LEFT):
            Layer.set_anchor(win, borde, True)
        Layer.set_exclusive_zone(win, 0)
        try:
            Layer.set_keyboard_mode(win, Layer.KeyboardMode.ON_DEMAND)
        except AttributeError:
            Layer.set_keyboard_interactivity(win, True)
        self._monitor_del_puntero()

    def _monitor_del_puntero(self):
        display = self.Gdk.Display.get_default()
        puntero = display.get_default_seat().get_pointer()
        if puntero is None:
            return
        posicion = puntero.get_position()
        if len(posicion) == 3:
            _pantalla, x, y = posicion
        else:
            x, y = posicion[0], posicion[1]
        try:
            monitor = display.get_monitor_at_point(x, y)
        except Exception:
            return
        if monitor is not None:
            self.Layer.set_monitor(self.win, monitor)

    def pintar(self):
        self.mes.set_text(f"{MESES[self.vista.month - 1]} {self.vista.year}")
        fechas, cuenta = resumen(self.inicio, self.fin)
        self.fecha.set_text(fechas)
        self.cuenta.set_text(cuenta)
        self._pintar_dias()
        self.panel.show_all()

    def _pintar_dias(self):
        Gtk = self.Gtk
        for hijo in self.rejilla.get_children():
            self.rejilla.remove(hijo)
        for columna, nombre in enumerate(CORTOS):
            etiqueta = Gtk.Label(label=nombre)
            etiqueta.get_style_context().add_class("semana")
            self.rejilla.attach(etiqueta, columna, 0, 1, 1)
        primero = date(self.vista.year, self.vista.month, 1)
        cursor = primero - timedelta(days=primero.weekday())
        hoy = date.today()
        for fila in range(6):
            for columna in range(7):
                self.rejilla.attach(self._dia(cursor, hoy), columna, fila + 1, 1, 1)
                cursor += timedelta(days=1)

    def _dia(self, dia, hoy):
        Gtk = self.Gtk
        boton = Gtk.Button(label=str(dia.day))
        estilo = boton.get_style_context()
        estilo.add_class("dia")
        if dia.month != self.vista.month:
            estilo.add_class("otro")
        if dia == hoy:
            estilo.add_class("hoy")
        if self._es_extremo(dia):
            estilo.add_class("elegido")
        elif self._en_tramo(dia):
            estilo.add_class("rango")
        boton.connect("clicked", lambda *_d, elegido=dia: self.elegir(elegido))
        return boton

    def _es_extremo(self, dia):
        return dia == self.inicio or dia == self.fin

    def _en_tramo(self, dia):
        if self.inicio is None or self.fin is None:
            return False
        primero, ultimo = (self.inicio, self.fin) if self.inicio <= self.fin else (self.fin, self.inicio)
        return primero < dia < ultimo

    def elegir(self, dia):
        if self.inicio is None or self.fin is not None:
            self.inicio, self.fin = dia, None
        else:
            self.fin = dia
        self.vista = dia
        self.pintar()

    def mover_cursor(self, delta):
        if self.inicio is None:
            self.inicio = self.vista + timedelta(days=delta)
            self.vista = self.inicio
        elif self.fin is None:
            self.fin = self.inicio + timedelta(days=delta)
            self.vista = self.fin
        else:
            self.fin = self.fin + timedelta(days=delta)
            self.vista = self.fin
        self.pintar()

    def mover_mes(self, delta):
        ano, mes = self.vista.year, self.vista.month + delta
        while mes < 1:
            mes += 12
            ano -= 1
        while mes > 12:
            mes -= 12
            ano += 1
        dia = min(self.vista.day, monthrange(ano, mes)[1])
        self.vista = date(ano, mes, dia)
        self.pintar()

    def _rueda(self, _widget, event):
        if event.direction == self.Gdk.ScrollDirection.UP:
            self.mover_mes(-1)
        elif event.direction == self.Gdk.ScrollDirection.DOWN:
            self.mover_mes(1)
        elif event.direction == self.Gdk.ScrollDirection.SMOOTH:
            _ok, _dx, dy = event.get_scroll_deltas()
            self._rueda_acum += dy
            if self._rueda_acum <= -1:
                self._rueda_acum = 0
                self.mover_mes(-1)
            elif self._rueda_acum >= 1:
                self._rueda_acum = 0
                self.mover_mes(1)
        return True

    def _tecla(self, _win, event):
        tecla = event.keyval
        K = self.Gdk
        if tecla == K.KEY_Escape:
            self.cerrar()
        elif tecla == K.KEY_Left:
            self.mover_cursor(-1)
        elif tecla == K.KEY_Right:
            self.mover_cursor(1)
        elif tecla == K.KEY_Up:
            self.mover_cursor(-7)
        elif tecla == K.KEY_Down:
            self.mover_cursor(7)
        elif tecla in (K.KEY_Home, K.KEY_t, K.KEY_T):
            self.elegir(date.today())
        elif tecla == K.KEY_Page_Up:
            self.mover_mes(-1)
        elif tecla == K.KEY_Page_Down:
            self.mover_mes(1)
        else:
            return False
        return True

    def _foco_fuera(self, *_args):
        if self.listo:
            self.GLib.timeout_add(80, self._cerrar_si_sin_foco)
        return False

    def _cerrar_si_sin_foco(self):
        if not self.win.is_active():
            self.cerrar()
        return False

    def cerrar(self):
        self.win.destroy()

    def abrir(self):
        self.pintar()
        self.win.show_all()
        self.win.present()
        self.GLib.timeout_add(200, self._marcar_listo)
        self.Gtk.main()

    def _marcar_listo(self):
        self.listo = True
        return False


if __name__ == "__main__":
    Calendario().abrir()
