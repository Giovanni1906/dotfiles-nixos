"""Reproductor de audio integrado con comparador A/B en vivo y visualizador de onda en Cairo."""

import array
import math
from pathlib import Path
import shutil
import subprocess
import threading
import time

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from .tema import formatear_tiempo, hex_a_rgb_float, obtener_metadatos_audio


def extraer_onda_audio(archivo: Path, num_barras: int = 110) -> list[float]:
    """Extrae la envolvente de amplitud normalizada de un archivo de audio usando ffmpeg."""
    if not archivo or not archivo.is_file():
        return [0.08] * num_barras
    try:
        res = subprocess.run(
            [
                "ffmpeg",
                "-v", "error",
                "-i", str(archivo),
                "-vn",
                "-ac", "1",
                "-ar", "1200",
                "-f", "s16le",
                "-",
            ],
            capture_output=True,
            timeout=20.0,
        )
        if res.returncode != 0 or not res.stdout:
            return [0.15] * num_barras

        muestras = array.array("h")
        n_bytes = len(res.stdout) - (len(res.stdout) % 2)
        muestras.frombytes(res.stdout[:n_bytes])
        total = len(muestras)
        if total == 0:
            return [0.10] * num_barras

        paso = max(1, total // num_barras)
        barras: list[float] = []
        for i in range(num_barras):
            inicio = i * paso
            fin = min(total, (i + 1) * paso)
            if inicio >= total:
                barras.append(0.05)
                continue
            bloque = muestras[inicio:fin]
            # Promedio cuadrático aproximado + pico para reflejar tanto voz como ruido de fondo
            pico = max((abs(x) for x in bloque), default=0) / 32768.0
            barras.append(pico)

        max_val = max(barras, default=0.01) or 0.01
        return [max(0.05, min(1.0, v / max_val)) for v in barras]
    except Exception:
        return [0.15] * num_barras


def abrir_en_reproductor_externo(archivo: Path) -> bool:
    """Abre el archivo de audio en Amberol, MPV o el reproductor predeterminado del sistema."""
    if not archivo or not archivo.is_file():
        return False
    for candidato in (
        "amberol",
        str(Path.home() / ".nix-profile/bin/amberol"),
        "mpv",
        str(Path.home() / ".nix-profile/bin/mpv"),
        "xdg-open",
    ):
        ruta_bin = shutil.which(candidato) or (candidato if Path(candidato).is_file() else None)
        if ruta_bin:
            try:
                subprocess.Popen(
                    [ruta_bin, str(archivo)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                continue
    return False


class LienzoOnda(Gtk.DrawingArea):
    """Widget Cairo interactivo que dibuja la forma de onda y permite saltar con clic/arrastre."""

    def __init__(self, tema: dict, al_saltar_callback):
        super().__init__()
        self.tema = tema
        self.al_saltar = al_saltar_callback
        self.barras: list[float] = [0.08] * 110
        self.progreso: float = 0.0  # 0.0 a 1.0
        self.modo_limpio: bool = False
        self.cargando: bool = False

        self.set_size_request(-1, 96)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )
        self._arrastrando = False

        self.connect("draw", self._al_dibujar)
        self.connect("button-press-event", self._al_presionar)
        self.connect("button-release-event", self._al_soltar)
        self.connect("motion-notify-event", self._al_mover)

    def actualizar_datos(self, barras: list[float], modo_limpio: bool, cargando: bool = False):
        self.barras = barras if barras else [0.08] * 110
        self.modo_limpio = modo_limpio
        self.cargando = cargando
        self.queue_draw()

    def fijar_progreso(self, fraccion: float):
        self.progreso = max(0.0, min(1.0, fraccion))
        self.queue_draw()

    def _emitir_salto_desde_x(self, x: float):
        ancho = self.get_allocated_width()
        if ancho > 16 and self.al_saltar:
            frac = max(0.0, min(1.0, (x - 8) / (ancho - 16)))
            self.progreso = frac
            self.queue_draw()
            self.al_saltar(frac)

    def _al_presionar(self, _widget, event):
        if event.button == 1:
            self._arrastrando = True
            self._emitir_salto_desde_x(event.x)
        return True

    def _al_mover(self, _widget, event):
        if self._arrastrando:
            self._emitir_salto_desde_x(event.x)
        return True

    def _al_soltar(self, _widget, event):
        if event.button == 1 and self._arrastrando:
            self._arrastrando = False
            self._emitir_salto_desde_x(event.x)
        return True

    def _al_dibujar(self, widget, cr: cairo.Context):
        ancho = widget.get_allocated_width()
        alto = widget.get_allocated_height()

        r_sup, g_sup, b_sup = hex_a_rgb_float(self.tema["SUPERFICIE"])
        r_fnd, g_fnd, b_fnd = hex_a_rgb_float(self.tema["FONDO"])
        r_act, g_act, b_act = hex_a_rgb_float(
            self.tema["EXITO"] if self.modo_limpio else self.tema["ACENTO"]
        )
        r_sec, g_sec, b_sec = hex_a_rgb_float(self.tema["SECUNDARIO"])
        r_txt, g_txt, b_txt = hex_a_rgb_float(self.tema["TEXTO"])

        # Fondo redondeado del visor
        radio = 8.0
        cr.new_sub_path()
        cr.arc(ancho - radio, radio, radio, -math.pi / 2, 0)
        cr.arc(ancho - radio, alto - radio, radio, 0, math.pi / 2)
        cr.arc(radio, alto - radio, radio, math.pi / 2, math.pi)
        cr.arc(radio, radio, radio, math.pi, 3 * math.pi / 2)
        cr.close_path()

        cr.set_source_rgba(r_fnd * 0.75 + r_sup * 0.25, g_fnd * 0.75 + g_sup * 0.25, b_fnd * 0.75 + b_sup * 0.25, 0.92)
        cr.fill_preserve()
        cr.set_source_rgba(r_act, g_act, b_act, 0.40)
        cr.set_line_width(1.2)
        cr.stroke()

        # Línea central sutil
        centro_y = alto / 2.0
        cr.set_source_rgba(r_txt, g_txt, b_txt, 0.10)
        cr.set_line_width(1.0)
        cr.move_to(10, centro_y)
        cr.line_to(ancho - 10, centro_y)
        cr.stroke()

        # Dibujar barras de la forma de onda
        n = len(self.barras)
        if n > 0:
            margen_x = 12.0
            ancho_util = max(10.0, ancho - 2 * margen_x)
            paso_x = ancho_util / n
            ancho_barra = max(2.0, paso_x * 0.62)
            max_altura = (alto - 22.0) / 2.0

            for i, valor in enumerate(self.barras):
                pos_rel = (i + 0.5) / n
                x = margen_x + i * paso_x + (paso_x - ancho_barra) / 2.0
                h_mitad = max(2.5, valor * max_altura)

                if pos_rel <= self.progreso:
                    cr.set_source_rgba(r_act, g_act, b_act, 0.95)
                else:
                    cr.set_source_rgba(r_sec, g_sec, b_sec, 0.30)

                cr.rectangle(x, centro_y - h_mitad, ancho_barra, h_mitad * 2.0)
                cr.fill()

            # Cursor de reproducción (Playhead)
            cursor_x = margen_x + self.progreso * ancho_util
            cr.set_source_rgba(r_txt, g_txt, b_txt, 0.92)
            cr.set_line_width(1.8)
            cr.move_to(cursor_x, 6)
            cr.line_to(cursor_x, alto - 6)
            cr.stroke()

            cr.arc(cursor_x, 8, 4.0, 0, 2 * math.pi)
            cr.set_source_rgba(r_act, g_act, b_act, 1.0)
            cr.fill()

        return False


class PanelReproductorAB(Gtk.Box):
    """Panel completo de reproducción y comparación en tiempo real entre Original (A) y Limpio (B)."""

    def __init__(self, tema: dict):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.tema = tema

        self.archivo_original: Path | None = None
        self.archivo_limpio: Path | None = None
        self.onda_original: list[float] = [0.08] * 110
        self.onda_limpio: list[float] = [0.08] * 110

        self.pista_activa: str = "original"  # "original" | "limpio"
        self.duracion: float = 0.0
        self.posicion_seg: float = 0.0
        self.reproduciendo: bool = False
        self.volumen: int = 90

        self._proc_ffplay: subprocess.Popen | None = None
        self._t0_monotonic: float = 0.0
        self._offset_inicio: float = 0.0
        self._timer_id: int | None = None

        self._construir_ui()

    def _construir_ui(self):
        # 1. Selector de Pista A/B (Comparación en vivo)
        fila_ab = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fila_ab.set_homogeneous(True)
        self.pack_start(fila_ab, False, False, 0)

        self.btn_pista_orig = Gtk.Button(label="🎤  A · Audio Original (Con ruido)")
        self.btn_pista_orig.get_style_context().add_class("chip-activo")
        self.btn_pista_orig.connect("clicked", lambda *_: self.cambiar_pista("original"))
        fila_ab.pack_start(self.btn_pista_orig, True, True, 0)

        self.btn_pista_limpio = Gtk.Button(label="✨  B · Voz Limpia (Procesado)")
        self.btn_pista_limpio.set_sensitive(False)
        self.btn_pista_limpio.connect("clicked", lambda *_: self.cambiar_pista("limpio"))
        fila_ab.pack_start(self.btn_pista_limpio, True, True, 0)

        # 2. Visualizador de Forma de Onda interactivo
        self.lienzo_onda = LienzoOnda(self.tema, self._al_saltar_en_onda)
        self.pack_start(self.lienzo_onda, False, False, 0)

        # 3. Etiquetas de estado de pista y tiempo
        fila_info_tiempo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pack_start(fila_info_tiempo, False, False, 0)

        self.lbl_pista_actual = Gtk.Label(label="Selecciona o procesa un audio para escucharlo")
        self.lbl_pista_actual.set_halign(Gtk.Align.START)
        self.lbl_pista_actual.get_style_context().add_class("info-archivo")
        fila_info_tiempo.pack_start(self.lbl_pista_actual, True, True, 0)

        self.lbl_tiempo = Gtk.Label(label="00:00 / 00:00")
        self.lbl_tiempo.set_halign(Gtk.Align.END)
        self.lbl_tiempo.get_style_context().add_class("etiqueta-seccion")
        fila_info_tiempo.pack_start(self.lbl_tiempo, False, False, 0)

        # 4. Controles de transporte y volumen
        fila_controles = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pack_start(fila_controles, False, False, 0)

        btn_atras = Gtk.Button(label="⏪ -5s")
        btn_atras.set_tooltip_text("Retroceder 5 segundos")
        btn_atras.connect("clicked", lambda *_: self.saltar_relativo(-5.0))
        fila_controles.pack_start(btn_atras, False, False, 0)

        self.btn_play = Gtk.Button(label="󰐊  Reproducir")
        self.btn_play.get_style_context().add_class("accion-principal")
        self.btn_play.connect("clicked", lambda *_: self.alternar_play_pausa())
        fila_controles.pack_start(self.btn_play, False, False, 0)

        btn_stop = Gtk.Button(label="󰓛")
        btn_stop.set_tooltip_text("Detener y volver al inicio")
        btn_stop.connect("clicked", lambda *_: self.detener(reiniciar=True))
        fila_controles.pack_start(btn_stop, False, False, 0)

        btn_adelante = Gtk.Button(label="+5s ⏩")
        btn_adelante.set_tooltip_text("Avanzar 5 segundos")
        btn_adelante.connect("clicked", lambda *_: self.saltar_relativo(5.0))
        fila_controles.pack_start(btn_adelante, False, False, 0)

        btn_ab_rapido = Gtk.Button(label="⇄  Alternar A/B")
        btn_ab_rapido.set_tooltip_text("Conmutar al instante entre Original y Limpio en el mismo segundo")
        btn_ab_rapido.connect("clicked", lambda *_: self.alternar_ab())
        fila_controles.pack_start(btn_ab_rapido, False, False, 0)

        # Control de volumen a la derecha
        caja_vol = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        fila_controles.pack_end(caja_vol, False, False, 0)

        lbl_vol = Gtk.Label(label="󰕾")
        caja_vol.pack_start(lbl_vol, False, False, 0)

        self.escala_vol = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        self.escala_vol.set_draw_value(False)
        self.escala_vol.set_value(90)
        self.escala_vol.set_size_request(90, -1)
        self.escala_vol.connect("value-changed", self._al_cambiar_volumen)
        caja_vol.pack_start(self.escala_vol, False, False, 0)

    def cargar_audios(self, original: Path | None, limpio: Path | None = None, seleccionar_limpio: bool = False):
        """Carga las pistas de audio y calcula sus formas de onda en segundo plano."""
        self.detener(reiniciar=True)
        self.archivo_original = original if (original and original.is_file()) else None
        self.archivo_limpio = limpio if (limpio and limpio.is_file()) else None

        self.btn_pista_orig.set_sensitive(self.archivo_original is not None)
        self.btn_pista_limpio.set_sensitive(self.archivo_limpio is not None)

        if seleccionar_limpio and self.archivo_limpio:
            self.pista_activa = "limpio"
        else:
            self.pista_activa = "original"

        self._actualizar_botones_pista()

        arch_ref = self._obtener_archivo_activo()
        if arch_ref:
            meta = obtener_metadatos_audio(arch_ref)
            self.duracion = meta["duracion"]
        else:
            self.duracion = 0.0

        self.posicion_seg = 0.0
        self._actualizar_etiquetas_tiempo()

        def _calcular_ondas():
            onda_o = extraer_onda_audio(self.archivo_original) if self.archivo_original else [0.08] * 110
            onda_l = extraer_onda_audio(self.archivo_limpio) if self.archivo_limpio else [0.08] * 110

            def _aplicar():
                self.onda_original = onda_o
                self.onda_limpio = onda_l
                self._refrescar_lienzo()
                return False

            GLib.idle_add(_aplicar)

        threading.Thread(target=_calcular_ondas, daemon=True).start()

    def _obtener_archivo_activo(self) -> Path | None:
        if self.pista_activa == "limpio" and self.archivo_limpio:
            return self.archivo_limpio
        return self.archivo_original

    def _actualizar_botones_pista(self):
        ctx_o = self.btn_pista_orig.get_style_context()
        ctx_l = self.btn_pista_limpio.get_style_context()
        ctx_o.remove_class("chip-activo")
        ctx_l.remove_class("chip-exito")

        if self.pista_activa == "limpio" and self.archivo_limpio:
            ctx_l.add_class("chip-exito")
            self.lbl_pista_actual.set_text(
                f"✨ Escuchando: VOZ LIMPIA ({self.archivo_limpio.name})"
            )
        elif self.archivo_original:
            ctx_o.add_class("chip-activo")
            self.lbl_pista_actual.set_text(
                f"🎤 Escuchando: AUDIO ORIGINAL ({self.archivo_original.name})"
            )
        else:
            self.lbl_pista_actual.set_text("Ningún archivo cargado")

        self._refrescar_lienzo()

    def _refrescar_lienzo(self):
        es_limpio = self.pista_activa == "limpio" and self.archivo_limpio is not None
        barras = self.onda_limpio if es_limpio else self.onda_original
        self.lienzo_onda.actualizar_datos(barras, modo_limpio=es_limpio)

    def cambiar_pista(self, nueva_pista: str):
        if nueva_pista == "limpio" and not self.archivo_limpio:
            return
        if nueva_pista == "original" and not self.archivo_original:
            return
        if self.pista_activa == nueva_pista:
            return

        estaba_reproduciendo = self.reproduciendo
        pos_actual = self.posicion_seg
        self.detener(reiniciar=False)
        self.pista_activa = nueva_pista
        self.posicion_seg = pos_actual
        self._actualizar_botones_pista()

        if estaba_reproduciendo:
            self.iniciar_reproduccion(desde_seg=pos_actual)

    def alternar_ab(self):
        if self.pista_activa == "original" and self.archivo_limpio:
            self.cambiar_pista("limpio")
        elif self.pista_activa == "limpio" and self.archivo_original:
            self.cambiar_pista("original")

    def alternar_play_pausa(self):
        if self.reproduciendo:
            self.detener(reiniciar=False)
        else:
            if self.duracion > 0 and self.posicion_seg >= self.duracion - 0.25:
                self.posicion_seg = 0.0
            self.iniciar_reproduccion(desde_seg=self.posicion_seg)

    def iniciar_reproduccion(self, desde_seg: float = 0.0):
        archivo = self._obtener_archivo_activo()
        if not archivo or not archivo.is_file():
            return

        self._matar_ffplay()
        if self.duracion <= 0:
            self.duracion = obtener_metadatos_audio(archivo)["duracion"]

        self.posicion_seg = max(0.0, min(desde_seg, max(0.0, self.duracion - 0.1)))
        self._offset_inicio = self.posicion_seg
        self._t0_monotonic = time.monotonic()

        cmd = [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-vn",
            "-loglevel", "quiet",
            "-ss", f"{self.posicion_seg:.2f}",
            "-volume", str(int(self.volumen)),
            str(archivo),
        ]
        try:
            self._proc_ffplay = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.reproduciendo = True
            self.btn_play.set_label("󰏤  Pausar")
            if self._timer_id is None:
                self._timer_id = GLib.timeout_add(50, self._tick_reloj)
        except Exception:
            self.reproduciendo = False

    def _tick_reloj(self) -> bool:
        if not self.reproduciendo or self._proc_ffplay is None:
            self._timer_id = None
            return False

        if self._proc_ffplay.poll() is not None:
            # Terminó la pista
            self.reproduciendo = False
            self.posicion_seg = 0.0
            self.btn_play.set_label("󰐊  Reproducir")
            self.lienzo_onda.fijar_progreso(0.0)
            self._actualizar_etiquetas_tiempo()
            self._timer_id = None
            return False

        transcurrido = time.monotonic() - self._t0_monotonic
        self.posicion_seg = min(self.duracion, self._offset_inicio + transcurrido)
        frac = (self.posicion_seg / self.duracion) if self.duracion > 0 else 0.0
        self.lienzo_onda.fijar_progreso(frac)
        self._actualizar_etiquetas_tiempo()
        return True

    def detener(self, reiniciar: bool = False):
        if self.reproduciendo and self._proc_ffplay is not None:
            transcurrido = time.monotonic() - self._t0_monotonic
            self.posicion_seg = min(self.duracion, self._offset_inicio + transcurrido)
        self.reproduciendo = False
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        self._matar_ffplay()
        self.btn_play.set_label("󰐊  Reproducir")

        if reiniciar:
            self.posicion_seg = 0.0
            self.lienzo_onda.fijar_progreso(0.0)
        self._actualizar_etiquetas_tiempo()

    def saltar_relativo(self, delta_seg: float):
        if self.duracion <= 0:
            return
        nueva_pos = max(0.0, min(self.duracion - 0.1, self.posicion_seg + delta_seg))
        estaba_reproduciendo = self.reproduciendo
        self.detener(reiniciar=False)
        self.posicion_seg = nueva_pos
        self.lienzo_onda.fijar_progreso(nueva_pos / self.duracion)
        self._actualizar_etiquetas_tiempo()
        if estaba_reproduciendo:
            self.iniciar_reproduccion(desde_seg=nueva_pos)

    def _al_saltar_en_onda(self, fraccion: float):
        if self.duracion <= 0:
            return
        nueva_pos = fraccion * self.duracion
        estaba_reproduciendo = self.reproduciendo
        self.detener(reiniciar=False)
        self.posicion_seg = nueva_pos
        self._actualizar_etiquetas_tiempo()
        if estaba_reproduciendo:
            self.iniciar_reproduccion(desde_seg=nueva_pos)

    def _al_cambiar_volumen(self, escala):
        nuevo_vol = int(escala.get_value())
        if nuevo_vol == self.volumen:
            return
        self.volumen = nuevo_vol
        if self.reproduciendo:
            pos = self.posicion_seg
            self.iniciar_reproduccion(desde_seg=pos)

    def _actualizar_etiquetas_tiempo(self):
        self.lbl_tiempo.set_text(
            f"{formatear_tiempo(self.posicion_seg)} / {formatear_tiempo(self.duracion)}"
        )

    def _matar_ffplay(self):
        if self._proc_ffplay is not None:
            try:
                self._proc_ffplay.terminate()
                self._proc_ffplay.wait(timeout=0.3)
            except Exception:
                try:
                    self._proc_ffplay.kill()
                except Exception:
                    pass
            self._proc_ffplay = None

    def abrir_activo_en_externo(self):
        arch = self._obtener_archivo_activo()
        if arch:
            self.detener(reiniciar=False)
            abrir_en_reproductor_externo(arch)
