"""Interfaz gráfica principal GTK3 de Voz Limpia."""

from pathlib import Path
import subprocess
import threading
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango

from .motor import (
    FORMATOS_SALIDA,
    INTENSIDADES_RUIDO,
    MODOS_RECONSTRUCCION,
    NIVELES_AISLAMIENTO,
    PERFILES,
    TONOS_VOZ,
    OpcionesProcesamiento,
    ProcesadorVoz,
    construir_filtros_post_dsp,
    estado_motores_ia,
)
from .reproductor import PanelReproductorAB
from .tema import (
    EXTENSIONES_AUDIO,
    aplicar_css_tema,
    buscar_audios_recientes,
    carpeta_xdg,
    formatear_tamano,
    formatear_tiempo,
    leer_archivo_portapapeles,
    leer_tema,
    notificar,
    obtener_metadatos_audio,
)


class VozLimpiaWindow:
    """Ventana principal de la utilidad Voz Limpia."""

    def __init__(self, archivo_inicial: Path | None = None):
        self.tema = leer_tema()
        self.procesador = ProcesadorVoz()

        self.archivo_origen: Path | None = None
        self.archivo_resultado: Path | None = None
        self.ocupado: bool = False
        self.perfil_actual: str = "estudio"
        self._actualizando_controles: bool = False
        self._sincronizando_live: bool = False
        self._en_vista_previa: bool = False
        self._ultima_pos_previa: float = 0.0
        self.ultima_carpeta: Path = carpeta_xdg("DOWNLOAD", "Descargas")

        self._construir_ventana()

        # Cargar archivo inicial si se pasó por argumento o si está en el portapapeles
        if archivo_inicial and archivo_inicial.is_file():
            self._fijar_archivo_origen(archivo_inicial.resolve())
        else:
            clip = leer_archivo_portapapeles()
            if clip:
                self._fijar_archivo_origen(clip)
            else:
                recientes = buscar_audios_recientes(limite=1)
                if recientes:
                    self._fijar_archivo_origen(recientes[0])

    def _etiqueta_seccion(self, texto: str) -> Gtk.Label:
        lbl = Gtk.Label(label=texto)
        lbl.set_halign(Gtk.Align.START)
        lbl.get_style_context().add_class("etiqueta-seccion")
        return lbl

    def _construir_ventana(self):
        self.win = Gtk.Window(title="Voz Limpia")
        self.win.set_default_size(760, 745)
        self.win.set_resizable(True)
        self.win.set_decorated(False)
        visual = self.win.get_screen().get_rgba_visual()
        if visual is not None:
            self.win.set_visual(visual)

        aplicar_css_tema(self.tema)

        raiz = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        raiz.get_style_context().add_class("contenedor-principal")
        self.win.add(raiz)

        # --- CABECERA ---
        cabecera = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        raiz.pack_start(cabecera, False, False, 0)

        caja_titulo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        fila_tit = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_titulo = Gtk.Label(label="🎙️  Voz Limpia")
        lbl_titulo.set_halign(Gtk.Align.START)
        lbl_titulo.get_style_context().add_class("titulo-app")
        fila_tit.pack_start(lbl_titulo, False, False, 0)

        est_ia = estado_motores_ia()
        txt_badge = (
            "IA DeepFilter 3 + Vocos · Tiempo Real"
            if est_ia["listo"]
            else "IA Auto-Descargable"
        )
        self.lbl_badge_ia = Gtk.Label(label=txt_badge)
        self.lbl_badge_ia.get_style_context().add_class("badge-ia")
        fila_tit.pack_start(self.lbl_badge_ia, False, False, 0)
        caja_titulo.pack_start(fila_tit, False, False, 0)

        lbl_sub = Gtk.Label(
            label="Limpieza neuronal 48 kHz sin voz robótica, vista previa de 12s y ajuste Post-IA en tiempo real"
        )
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

        self.btn_tab_proc = Gtk.Button(label="🎛️   1. Configurar y Limpiar Voz")
        self.btn_tab_proc.get_style_context().add_class("tab-btn")
        self.btn_tab_proc.get_style_context().add_class("tab-activa")
        self.btn_tab_proc.connect("clicked", lambda *_: self._cambiar_pestana("procesar"))
        barra_tabs.pack_start(self.btn_tab_proc, True, True, 0)

        self.btn_tab_rep = Gtk.Button(label="🎧   2. Reproductor y Comparador A/B")
        self.btn_tab_rep.get_style_context().add_class("tab-btn")
        self.btn_tab_rep.connect("clicked", lambda *_: self._cambiar_pestana("reproductor"))
        barra_tabs.pack_start(self.btn_tab_rep, True, True, 0)

        raiz.pack_start(Gtk.Separator(), False, False, 0)

        # --- STACK DE CONTENIDO ---
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(160)
        raiz.pack_start(self.stack, True, True, 0)

        self.stack.add_named(self._construir_tab_procesar(), "procesar")
        self.stack.add_named(self._construir_tab_reproductor(), "reproductor")

        raiz.pack_start(Gtk.Separator(), False, False, 0)

        # --- BARRA INFERIOR DE PROGRESO Y ACCIONES ---
        zona_inferior = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        raiz.pack_start(zona_inferior, False, False, 0)

        self.barra_progreso = Gtk.ProgressBar()
        self.barra_progreso.set_fraction(0.0)
        zona_inferior.pack_start(self.barra_progreso, False, False, 0)

        fila_acciones = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        zona_inferior.pack_start(fila_acciones, False, False, 0)

        self.lbl_estado = Gtk.Label(label="Listo · Selecciona un archivo de audio para comenzar")
        self.lbl_estado.set_halign(Gtk.Align.START)
        self.lbl_estado.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_estado.get_style_context().add_class("estado-texto")
        fila_acciones.pack_start(self.lbl_estado, True, True, 0)

        self.btn_escuchar_prev = Gtk.Button(label="🎧  Escuchar")
        self.btn_escuchar_prev.set_tooltip_text("Ir al reproductor para escuchar y comparar el audio")
        self.btn_escuchar_prev.connect("clicked", lambda *_: self._cambiar_pestana("reproductor"))
        fila_acciones.pack_start(self.btn_escuchar_prev, False, False, 0)

        self.btn_abrir_carpeta = Gtk.Button(label="󰉋  Carpeta")
        self.btn_abrir_carpeta.set_tooltip_text("Abrir la carpeta donde está el archivo")
        self.btn_abrir_carpeta.connect("clicked", self._abrir_carpeta_actual)
        fila_acciones.pack_start(self.btn_abrir_carpeta, False, False, 0)

        self.btn_cancelar = Gtk.Button(label="✕  Cancelar")
        self.btn_cancelar.get_style_context().add_class("boton-peligro")
        self.btn_cancelar.connect("clicked", self._cancelar_proceso)
        self.btn_cancelar.set_no_show_all(True)
        self.btn_cancelar.hide()
        fila_acciones.pack_start(self.btn_cancelar, False, False, 0)

        self.btn_probar = Gtk.Button(label="⚡  Probar 12s")
        self.btn_probar.set_tooltip_text(
            "Procesa solo 12 segundos (~1-2 s) para escuchar y ajustar el tono en tiempo real antes de exportar"
        )
        self.btn_probar.connect("clicked", self._iniciar_vista_previa)
        fila_acciones.pack_start(self.btn_probar, False, False, 0)

        self.btn_ejecutar = Gtk.Button(label="✨  Limpiar y Guardar")
        self.btn_ejecutar.get_style_context().add_class("accion-principal")
        self.btn_ejecutar.connect("clicked", self._iniciar_procesamiento)
        fila_acciones.pack_start(self.btn_ejecutar, False, False, 0)

        self.win.connect("key-press-event", self._al_pulsar_tecla)
        self.win.connect("destroy", self._al_destruir)

    # =========================================================================
    # PESTAÑA 1: CONFIGURACIÓN Y PROCESAMIENTO
    # =========================================================================
    def _construir_tab_procesar(self) -> Gtk.Widget:
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # 1. Selector de Archivo de Origen
        caja.pack_start(
            self._etiqueta_seccion("ARCHIVO DE AUDIO O VIDEO (ARRASTRA AQUÍ, EXAMINA O ELIGE RECIENTE)"),
            False, False, 0,
        )

        caja_archivo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        caja_archivo.get_style_context().add_class("caja-drop")
        caja.pack_start(caja_archivo, False, False, 0)

        caja_archivo.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        caja_archivo.drag_dest_add_uri_targets()
        caja_archivo.connect("drag-data-received", self._al_soltar_archivo)

        fila_arch = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        caja_archivo.pack_start(fila_arch, False, False, 0)

        self.entrada_archivo = Gtk.Entry()
        self.entrada_archivo.set_editable(False)
        self.entrada_archivo.set_placeholder_text("Ningún archivo seleccionado...")
        fila_arch.pack_start(self.entrada_archivo, True, True, 0)

        btn_recientes = Gtk.Button(label="󰋚  Recientes")
        btn_recientes.set_tooltip_text("Elegir entre los archivos de audio más recientes")
        btn_recientes.connect("clicked", self._mostrar_menu_recientes)
        fila_arch.pack_start(btn_recientes, False, False, 0)

        btn_pegar = Gtk.Button(label="󰆒  Pegar")
        btn_pegar.set_tooltip_text("Pegar archivo o ruta desde el portapapeles")
        btn_pegar.connect("clicked", self._pegar_portapapeles)
        fila_arch.pack_start(btn_pegar, False, False, 0)

        btn_elegir = Gtk.Button(label="󰉋  Examinar...")
        btn_elegir.connect("clicked", self._elegir_archivo_dialogo)
        fila_arch.pack_start(btn_elegir, False, False, 0)

        self.lbl_info_archivo = Gtk.Label(
            label="Formatos soportados: m4a, mp3, wav, flac, opus, ogg, aac, mp4, mkv, mov..."
        )
        self.lbl_info_archivo.set_halign(Gtk.Align.START)
        self.lbl_info_archivo.get_style_context().add_class("info-archivo")
        caja_archivo.pack_start(self.lbl_info_archivo, False, False, 0)

        # 2. Perfiles Inteligentes
        caja.pack_start(self._etiqueta_seccion("PERFIL DE LIMPIEZA"), False, False, 0)

        fila_perfiles = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fila_perfiles.set_homogeneous(True)
        caja.pack_start(fila_perfiles, False, False, 0)

        self.botones_perfil: dict[str, Gtk.Button] = {}
        for clave, etiqueta in (
            ("estudio", "🎙️ Estudio"),
            ("rescate", "🔥 Rescate IA"),
            ("aislar_voz", "👥 Anti-Voces"),
            ("rapido", "⚡ Rápido"),
            ("personalizado", "🎛️ Manual"),
        ):
            btn = Gtk.Button(label=etiqueta)
            btn.set_tooltip_text(PERFILES[clave]["descripcion"])
            btn.connect("clicked", lambda _b, k=clave: self._seleccionar_perfil(k))
            fila_perfiles.pack_start(btn, True, True, 0)
            self.botones_perfil[clave] = btn

        self.lbl_desc_perfil = Gtk.Label(label=PERFILES["estudio"]["descripcion"])
        self.lbl_desc_perfil.set_halign(Gtk.Align.START)
        self.lbl_desc_perfil.get_style_context().add_class("info-archivo")
        caja.pack_start(self.lbl_desc_perfil, False, False, 0)

        # 3. Ajustes Acústicos y de IA
        fila_combos_1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        fila_combos_1.set_homogeneous(True)
        caja.pack_start(fila_combos_1, False, False, 0)

        col_ruido = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_ruido.pack_start(self._etiqueta_seccion("REDUCCIÓN DE RUIDO Y FONDO (FASE IA)"), False, False, 0)
        self.combo_ruido = Gtk.ComboBoxText()
        for k, v in INTENSIDADES_RUIDO:
            self.combo_ruido.append(k, v)
        self.combo_ruido.set_active_id("equilibrada")
        self.combo_ruido.connect("changed", self._al_cambiar_ajuste_manual)
        col_ruido.pack_start(self.combo_ruido, False, False, 0)
        fila_combos_1.pack_start(col_ruido, True, True, 0)

        col_aislar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_aislar.pack_start(
            self._etiqueta_seccion("PUERTA / MURMULLOS (TIEMPO REAL)"),
            False, False, 0,
        )
        self.combo_aislar = Gtk.ComboBoxText()
        for k, v in NIVELES_AISLAMIENTO:
            self.combo_aislar.append(k, v)
        self.combo_aislar.set_active_id("off")
        self.combo_aislar.connect("changed", self._al_cambiar_ajuste_manual)
        col_aislar.pack_start(self.combo_aislar, False, False, 0)
        fila_combos_1.pack_start(col_aislar, True, True, 0)

        fila_combos_2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        fila_combos_2.set_homogeneous(True)
        caja.pack_start(fila_combos_2, False, False, 0)

        col_rec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_rec.pack_start(
            self._etiqueta_seccion("RECONSTRUCCIÓN DE VOZ IA (FASE IA)"),
            False, False, 0,
        )
        self.combo_reconstruir = Gtk.ComboBoxText()
        for k, v in MODOS_RECONSTRUCCION:
            self.combo_reconstruir.append(k, v)
        self.combo_reconstruir.set_active_id("off")
        self.combo_reconstruir.connect("changed", self._al_cambiar_ajuste_manual)
        col_rec.pack_start(self.combo_reconstruir, False, False, 0)
        fila_combos_2.pack_start(col_rec, True, True, 0)

        col_tono = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_tono.pack_start(self._etiqueta_seccion("TONO Y ECUALIZACIÓN (TIEMPO REAL)"), False, False, 0)
        self.combo_tono = Gtk.ComboBoxText()
        for k, v in TONOS_VOZ:
            self.combo_tono.append(k, v)
        self.combo_tono.set_active_id("claridad")
        self.combo_tono.connect("changed", self._al_cambiar_ajuste_manual)
        col_tono.pack_start(self.combo_tono, False, False, 0)
        fila_combos_2.pack_start(col_tono, True, True, 0)

        col_fmt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col_fmt.pack_start(self._etiqueta_seccion("FORMATO DEL ARCHIVO FINAL"), False, False, 0)
        self.combo_formato = Gtk.ComboBoxText()
        for k, v in FORMATOS_SALIDA:
            self.combo_formato.append(k, v)
        self.combo_formato.set_active_id("m4a")
        col_fmt.pack_start(self.combo_formato, False, False, 0)
        caja.pack_start(col_fmt, False, False, 0)

        # 4. Interruptores de módulos y modo de guardado
        caja_checks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        caja_checks.get_style_context().add_class("tarjeta-panel")
        caja.pack_start(caja_checks, False, False, 0)

        fila_chk1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        fila_chk1.set_homogeneous(True)
        caja_checks.pack_start(fila_chk1, False, False, 0)

        self.chk_deepfilter = Gtk.CheckButton(
            label="Motor IA DeepFilterNet 3 (48 kHz profundo)"
        )
        self.chk_deepfilter.set_active(True)
        self.chk_deepfilter.connect("toggled", self._al_cambiar_ajuste_manual)
        fila_chk1.pack_start(self.chk_deepfilter, True, True, 0)

        self.chk_eco = Gtk.CheckButton(
            label="Eliminar eco y resonancia de sala"
        )
        self.chk_eco.set_active(True)
        self.chk_eco.connect("toggled", self._al_cambiar_ajuste_manual)
        fila_chk1.pack_start(self.chk_eco, True, True, 0)

        fila_chk2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        fila_chk2.set_homogeneous(True)
        caja_checks.pack_start(fila_chk2, False, False, 0)

        self.chk_lufs = Gtk.CheckButton(
            label="Compresor vocal + Masterizar a -16 LUFS"
        )
        self.chk_lufs.set_active(True)
        self.chk_lufs.connect("toggled", self._al_cambiar_ajuste_manual)
        fila_chk2.pack_start(self.chk_lufs, True, True, 0)

        self.chk_reemplazar = Gtk.CheckButton(
            label="Reemplazar el archivo original al terminar"
        )
        self.chk_reemplazar.set_active(False)
        self.chk_reemplazar.set_tooltip_text(
            "Si está desmarcado, crea un archivo nuevo '<nombre>_limpio' dejando intacto tu audio original."
        )
        fila_chk2.pack_start(self.chk_reemplazar, True, True, 0)

        self._seleccionar_perfil("estudio")
        return caja

    # =========================================================================
    # PESTAÑA 2: REPRODUCTOR Y COMPARADOR A/B
    # =========================================================================
    def _construir_tab_reproductor(self) -> Gtk.Widget:
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        caja.pack_start(
            self._etiqueta_seccion("COMPARADOR EN VIVO: ESCUCHA EL ANTES (A) Y EL DESPUÉS (B)"),
            False, False, 0,
        )

        # Panel reproductor con onda interactiva
        tarjeta_rep = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tarjeta_rep.get_style_context().add_class("tarjeta-panel")
        caja.pack_start(tarjeta_rep, False, False, 0)

        self.reproductor = PanelReproductorAB(self.tema)
        tarjeta_rep.pack_start(self.reproductor, False, False, 0)

        # Panel de ajuste en tiempo real Post-IA (sin esperar re-procesamiento de IA)
        caja.pack_start(
            self._etiqueta_seccion("AJUSTE EN TIEMPO REAL (POST-IA · SIN ESPERAS)"),
            False, False, 0,
        )

        tarjeta_live = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tarjeta_live.get_style_context().add_class("tarjeta-panel")
        caja.pack_start(tarjeta_live, False, False, 0)

        fila_live_1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        fila_live_1.set_homogeneous(True)
        tarjeta_live.pack_start(fila_live_1, False, False, 0)

        col_lt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        col_lt.pack_start(self._etiqueta_seccion("TONO Y ECUALIZACIÓN"), False, False, 0)
        self.combo_live_tono = Gtk.ComboBoxText()
        for k, v in TONOS_VOZ:
            self.combo_live_tono.append(k, v)
        self.combo_live_tono.set_active_id(self.combo_tono.get_active_id() or "claridad")
        self.combo_live_tono.connect("changed", self._al_cambiar_live)
        col_lt.pack_start(self.combo_live_tono, False, False, 0)
        fila_live_1.pack_start(col_lt, True, True, 0)

        col_la = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        col_la.pack_start(self._etiqueta_seccion("PUERTA / MURMULLOS"), False, False, 0)
        self.combo_live_aislar = Gtk.ComboBoxText()
        for k, v in NIVELES_AISLAMIENTO:
            self.combo_live_aislar.append(k, v)
        self.combo_live_aislar.set_active_id(self.combo_aislar.get_active_id() or "off")
        self.combo_live_aislar.connect("changed", self._al_cambiar_live)
        col_la.pack_start(self.combo_live_aislar, False, False, 0)
        fila_live_1.pack_start(col_la, True, True, 0)

        fila_live_2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tarjeta_live.pack_start(fila_live_2, False, False, 0)

        self.chk_live_eco = Gtk.CheckButton(label="Anti-eco de sala")
        self.chk_live_eco.set_active(self.chk_eco.get_active())
        self.chk_live_eco.connect("toggled", self._al_cambiar_live)
        fila_live_2.pack_start(self.chk_live_eco, False, False, 0)

        self.chk_live_lufs = Gtk.CheckButton(label="Compresor vocal")
        self.chk_live_lufs.set_active(self.chk_lufs.get_active())
        self.chk_live_lufs.connect("toggled", self._al_cambiar_live)
        fila_live_2.pack_start(self.chk_live_lufs, False, False, 0)

        self.btn_reprobar_live = Gtk.Button(label="⚡  Re-probar 12s aquí")
        self.btn_reprobar_live.set_tooltip_text(
            "Re-genera la vista previa de 12s desde este segundo con la configuración actual de Fase IA"
        )
        self.btn_reprobar_live.connect("clicked", self._iniciar_vista_previa)
        fila_live_2.pack_end(self.btn_reprobar_live, False, False, 0)

        # Resumen comparativo y acciones sobre el resultado
        caja.pack_start(
            self._etiqueta_seccion("RESULTADO Y EXPORTACIÓN"),
            False, False, 0,
        )

        tarjeta_resumen = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tarjeta_resumen.get_style_context().add_class("tarjeta-panel")
        caja.pack_start(tarjeta_resumen, False, False, 0)

        self.lbl_resumen_ab = Gtk.Label(
            label="Aún no se ha procesado una versión limpia en esta sesión.\n"
                  "Pulsa '⚡ Probar 12s' para escuchar en ~1s o '✨ Limpiar y Guardar' para el archivo completo."
        )
        self.lbl_resumen_ab.set_halign(Gtk.Align.START)
        self.lbl_resumen_ab.set_line_wrap(True)
        self.lbl_resumen_ab.get_style_context().add_class("estado-texto")
        tarjeta_resumen.pack_start(self.lbl_resumen_ab, False, False, 0)

        fila_botones_res = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tarjeta_resumen.pack_start(fila_botones_res, False, False, 0)

        btn_ext = Gtk.Button(label="󰎆  Abrir en Amberol/MPV")
        btn_ext.set_tooltip_text("Abre la pista activa en Amberol o MPV")
        btn_ext.connect("clicked", lambda *_: self.reproductor.abrir_activo_en_externo())
        fila_botones_res.pack_start(btn_ext, False, False, 0)

        self.btn_copiar_limpio = Gtk.Button(label="󰆏  Copiar archivo")
        self.btn_copiar_limpio.set_tooltip_text(
            "Copia el archivo procesado al portapapeles para pegarlo en Thunar, WhatsApp o Telegram"
        )
        self.btn_copiar_limpio.set_sensitive(False)
        self.btn_copiar_limpio.connect("clicked", self._copiar_resultado_portapapeles)
        fila_botones_res.pack_start(self.btn_copiar_limpio, False, False, 0)

        self.btn_exportar_live = Gtk.Button(label="💾  Exportar Archivo Completo")
        self.btn_exportar_live.get_style_context().add_class("accion-principal")
        self.btn_exportar_live.set_tooltip_text(
            "Guarda el archivo final completo con estos ajustes (si ya pasó la Fase IA tarda ~1s)"
        )
        self.btn_exportar_live.connect("clicked", self._iniciar_procesamiento)
        fila_botones_res.pack_end(self.btn_exportar_live, False, False, 0)

        btn_volver = Gtk.Button(label="🎛️  Fase IA")
        btn_volver.set_tooltip_text("Volver a la pestaña de Fase IA y formato")
        btn_volver.connect("clicked", lambda *_: self._cambiar_pestana("procesar"))
        fila_botones_res.pack_end(btn_volver, False, False, 0)

        return caja

    # =========================================================================
    # LÓGICA DE INTERFAZ Y EVENTOS
    # =========================================================================
    def _cambiar_pestana(self, nombre: str):
        self.stack.set_visible_child_name(nombre)
        ctx_p = self.btn_tab_proc.get_style_context()
        ctx_r = self.btn_tab_rep.get_style_context()
        if nombre == "procesar":
            self.reproductor.detener(reiniciar=False)
            ctx_p.add_class("tab-activa")
            ctx_r.remove_class("tab-activa")
        else:
            ctx_r.add_class("tab-activa")
            ctx_p.remove_class("tab-activa")

    def _seleccionar_perfil(self, clave: str):
        if clave not in PERFILES:
            return
        self.perfil_actual = clave
        for k, btn in self.botones_perfil.items():
            ctx = btn.get_style_context()
            if k == clave:
                ctx.add_class("chip-activo")
            else:
                ctx.remove_class("chip-activo")

        datos = PERFILES[clave]
        self.lbl_desc_perfil.set_text(datos["descripcion"])

        if clave != "personalizado":
            self._actualizando_controles = True
            self.chk_deepfilter.set_active(datos["usar_deepfilter"])
            self.combo_ruido.set_active_id(datos["intensidad_ruido"])
            self.combo_aislar.set_active_id(datos["aislar_voz_principal"])
            self.chk_eco.set_active(datos["quitar_eco"])
            self.combo_reconstruir.set_active_id(datos.get("reconstruir_voz", "off"))
            self.combo_tono.set_active_id(datos["tono_voz"])
            self.chk_lufs.set_active(datos["normalizar_lufs"])
            self._actualizando_controles = False
            self._sincronizar_controles_live_desde_tab1()
            self._aplicar_dsp_en_vivo_si_disponible()

    def _al_cambiar_ajuste_manual(self, *_args):
        if self._actualizando_controles:
            return
        if self.perfil_actual != "personalizado":
            self._seleccionar_perfil("personalizado")
        self._sincronizar_controles_live_desde_tab1()
        self._aplicar_dsp_en_vivo_si_disponible()

    def _sincronizar_controles_live_desde_tab1(self):
        if not hasattr(self, "combo_live_tono") or self._sincronizando_live:
            return
        self._sincronizando_live = True
        self.combo_live_tono.set_active_id(self.combo_tono.get_active_id() or "claridad")
        self.combo_live_aislar.set_active_id(self.combo_aislar.get_active_id() or "off")
        self.chk_live_eco.set_active(self.chk_eco.get_active())
        self.chk_live_lufs.set_active(self.chk_lufs.get_active())
        self._sincronizando_live = False

    def _al_cambiar_live(self, *_args):
        if self._sincronizando_live:
            return
        self._sincronizando_live = True
        self._actualizando_controles = True
        self.combo_tono.set_active_id(self.combo_live_tono.get_active_id() or "claridad")
        self.combo_aislar.set_active_id(self.combo_live_aislar.get_active_id() or "off")
        self.chk_eco.set_active(self.chk_live_eco.get_active())
        self.chk_lufs.set_active(self.chk_live_lufs.get_active())
        self._actualizando_controles = False
        if self.perfil_actual != "personalizado":
            self._seleccionar_perfil("personalizado")
        self._sincronizando_live = False
        self._aplicar_dsp_en_vivo_si_disponible()

    def _aplicar_dsp_en_vivo_si_disponible(self):
        base_ia = self.procesador.obtener_base_ia_actual()
        if not base_ia or not hasattr(self, "reproductor"):
            return
        opciones = self._construir_opciones()
        filtro_live = construir_filtros_post_dsp(opciones, duracion=0.0, en_vivo=True)
        self.reproductor.reaplicar_filtro_live(filtro_live, activar=True)
        if not self._en_vista_previa and self.archivo_resultado:
            self._fijar_estado(
                "🎛️ Ajuste en tiempo real aplicado · Pulsa '💾 Exportar Archivo Completo' para guardarlo (~1s)"
            )

    def _fijar_archivo_origen(self, ruta: Path):
        if not ruta.is_file():
            return
        self.procesador.limpiar_cache()
        self._en_vista_previa = False
        self._ultima_pos_previa = 0.0
        self.archivo_origen = ruta
        self.archivo_resultado = None
        self.ultima_carpeta = ruta.parent
        self.entrada_archivo.set_text(str(ruta))

        meta = obtener_metadatos_audio(ruta)
        canales_txt = "Estéreo" if meta["canales"] >= 2 else "Mono"
        self.lbl_info_archivo.set_text(
            f"󰎆  {ruta.name}   ·   ⏱ {formatear_tiempo(meta['duracion'])}   ·   "
            f"{meta['codec']} {meta['sample_rate'] // 1000} kHz ({canales_txt})   ·   "
            f"📦 {formatear_tamano(meta['tamano_bytes'])}"
        )

        # Si ya existe un archivo <stem>_limpio en la misma carpeta, detectarlo para el comparador
        posible_limpio = None
        for ext in ("m4a", "mp3", "wav", "flac", "opus"):
            cand = ruta.parent / f"{ruta.stem}_limpio.{ext}"
            if cand.is_file() and cand.resolve() != ruta.resolve():
                posible_limpio = cand
                break

        self.archivo_resultado = posible_limpio
        self.btn_copiar_limpio.set_sensitive(posible_limpio is not None)
        self.reproductor.cargar_audios(ruta, posible_limpio, seleccionar_limpio=False)

        if posible_limpio:
            tam_orig = formatear_tamano(meta["tamano_bytes"])
            tam_limp = formatear_tamano(posible_limpio.stat().st_size)
            self.lbl_resumen_ab.set_text(
                f"✓ Versión limpia detectada: {posible_limpio.name}\n"
                f"Peso original: {tam_orig}   →   Peso limpio: {tam_limp}"
            )
        else:
            self.lbl_resumen_ab.set_text(
                f"Archivo cargado: {ruta.name} ({formatear_tiempo(meta['duracion'])})\n"
                "Pulsa '⚡ Probar 12s' para escuchar rápido o '✨ Limpiar y Guardar' para el archivo completo."
            )

        self._fijar_estado(f"Listo para procesar: {ruta.name}")

    def _construir_opciones(self) -> OpcionesProcesamiento:
        return OpcionesProcesamiento(
            perfil=self.perfil_actual,
            usar_deepfilter=self.chk_deepfilter.get_active(),
            intensidad_ruido=self.combo_ruido.get_active_id() or "equilibrada",
            aislar_voz_principal=self.combo_aislar.get_active_id() or "off",
            quitar_eco=self.chk_eco.get_active(),
            tono_voz=self.combo_tono.get_active_id() or "claridad",
            normalizar_lufs=self.chk_lufs.get_active(),
            reconstruir_voz=self.combo_reconstruir.get_active_id() or "off",
            formato_salida=self.combo_formato.get_active_id() or "m4a",
            reemplazar_original=self.chk_reemplazar.get_active(),
            carpeta_destino=self.archivo_origen.parent if self.archivo_origen else None,
        )

    def _iniciar_vista_previa(self, *_args):
        if self.ocupado:
            return
        if not self.archivo_origen or not self.archivo_origen.is_file():
            self._fijar_estado("Selecciona primero un archivo de audio", error=True)
            return

        inicio_seg = (
            self._ultima_pos_previa
            if self._en_vista_previa
            else max(0.0, float(self.reproductor.posicion_seg))
        )
        self._ultima_pos_previa = inicio_seg
        self.reproductor.detener(reiniciar=False)

        opciones = self._construir_opciones()
        self._fijar_ocupado(True)
        self.barra_progreso.set_fraction(0.05)
        self._fijar_estado("Preparando vista previa rápida de 12s...")

        archivo_in = self.archivo_origen

        def _progreso_ui(texto: str, fraccion: float):
            GLib.idle_add(self._actualizar_progreso_seguro, texto, fraccion)

        def _hilo():
            exito, orig_wav, ia_wav, es_completo, msg = self.procesador.preparar_vista_previa(
                archivo_in,
                opciones,
                inicio_seg=inicio_seg,
                duracion_seg=12.0,
                cb_progreso=_progreso_ui,
            )
            GLib.idle_add(
                self._al_terminar_vista_previa,
                exito, orig_wav, ia_wav, es_completo, msg, opciones, inicio_seg,
            )

        threading.Thread(target=_hilo, daemon=True).start()

    def _al_terminar_vista_previa(
        self,
        exito: bool,
        orig_wav: Path | None,
        ia_wav: Path | None,
        es_completo: bool,
        msg: str,
        opciones: OpcionesProcesamiento,
        inicio_seg: float,
    ):
        self._fijar_ocupado(False)
        if exito and orig_wav and ia_wav and ia_wav.is_file():
            self.barra_progreso.set_fraction(1.0)
            self._en_vista_previa = not es_completo
            filtro_live = construir_filtros_post_dsp(opciones, duracion=0.0, en_vivo=True)
            etiqueta = (
                f"Completo en vivo ({self.archivo_origen.name})"
                if es_completo
                else f"Vista Previa 12s (desde {formatear_tiempo(inicio_seg)})"
            )
            self.reproductor.cargar_audios(
                orig_wav,
                None,
                seleccionar_limpio=True,
                base_ia_live=ia_wav,
                filtro_live_b=filtro_live,
                usar_live_dsp=True,
                etiqueta_limpio=etiqueta,
            )
            self.lbl_resumen_ab.set_text(
                f"⚡ {etiqueta} · Fase IA en caché.\n"
                "Mueve los controles de 'Ajuste en Tiempo Real' arriba para oír el cambio al instante y luego pulsa '💾 Exportar Archivo Completo'."
            )
            self._fijar_estado(
                "⚡ Vista previa lista · Ajusta tono/eco/puerta en tiempo real",
                exito=True,
            )
            self._cambiar_pestana("reproductor")
            self.reproductor.iniciar_reproduccion(0.0)
        else:
            self.barra_progreso.set_fraction(0.0)
            self._fijar_estado(msg, error=True)
        return False

    def _mostrar_menu_recientes(self, boton):
        recientes = buscar_audios_recientes(limite=12)
        menu = Gtk.Menu()
        if not recientes:
            item = Gtk.MenuItem(label="No se encontraron audios recientes")
            item.set_sensitive(False)
            menu.append(item)
        else:
            for ruta in recientes:
                etiqueta = f"🎵  {ruta.name}   ({ruta.parent.name}/)"
                item = Gtk.MenuItem(label=etiqueta)
                item.connect("activate", lambda _i, r=ruta: self._fijar_archivo_origen(r))
                menu.append(item)
        menu.show_all()
        menu.popup_at_widget(boton, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)

    def _pegar_portapapeles(self, *_args):
        clip = leer_archivo_portapapeles()
        if clip:
            self._fijar_archivo_origen(clip)
        else:
            self._fijar_estado("El portapapeles no contiene un archivo de audio válido", error=True)

    def _elegir_archivo_dialogo(self, *_args):
        dlg = Gtk.FileChooserDialog(
            title="Seleccionar archivo de audio o video",
            parent=self.win,
            action=Gtk.FileChooserAction.OPEN,
        )
        dlg.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        if self.ultima_carpeta.is_dir():
            dlg.set_current_folder(str(self.ultima_carpeta))

        filtro_audio = Gtk.FileFilter()
        filtro_audio.set_name("Archivos de Audio y Video")
        for ext in EXTENSIONES_AUDIO:
            filtro_audio.add_pattern(f"*{ext}")
            filtro_audio.add_pattern(f"*{ext.upper()}")
        dlg.add_filter(filtro_audio)

        filtro_todos = Gtk.FileFilter()
        filtro_todos.set_name("Todos los archivos")
        filtro_todos.add_pattern("*")
        dlg.add_filter(filtro_todos)

        if dlg.run() == Gtk.ResponseType.OK:
            arch = dlg.get_filename()
            if arch:
                self._fijar_archivo_origen(Path(arch))
        dlg.destroy()

    def _al_soltar_archivo(self, _widget, _context, _x, _y, data, _info, _time):
        uris = data.get_uris()
        if uris:
            ruta_str = unquote(urlparse(uris[0]).path)
            p = Path(ruta_str)
            if p.is_file():
                self._fijar_archivo_origen(p)

    def _iniciar_procesamiento(self, *_args):
        if self.ocupado:
            return
        if not self.archivo_origen or not self.archivo_origen.is_file():
            self._fijar_estado("Selecciona primero un archivo de audio", error=True)
            return

        self.reproductor.detener(reiniciar=False)
        opciones = self._construir_opciones()

        self._fijar_ocupado(True)
        self.barra_progreso.set_fraction(0.03)
        if self.procesador.tiene_cache_ia_completo(self.archivo_origen, opciones):
            self._fijar_estado("Reutilizando Fase IA en caché · Exportando rápido...")
        else:
            self._fijar_estado("Iniciando motor de limpieza neuronal...")

        archivo_in = self.archivo_origen
        tam_antes = archivo_in.stat().st_size

        def _progreso_ui(texto: str, fraccion: float):
            GLib.idle_add(self._actualizar_progreso_seguro, texto, fraccion)

        def _hilo():
            exito, ruta_out, msg = self.procesador.procesar(
                archivo_in, opciones, cb_progreso=_progreso_ui
            )
            GLib.idle_add(self._al_terminar_proceso, exito, ruta_out, msg, tam_antes, opciones)

        threading.Thread(target=_hilo, daemon=True).start()

    def _actualizar_progreso_seguro(self, texto: str, fraccion: float):
        self.barra_progreso.set_fraction(max(0.0, min(1.0, fraccion)))
        self._fijar_estado(texto)
        return False

    def _al_terminar_proceso(
        self,
        exito: bool,
        ruta_out: Path | None,
        msg: str,
        tam_antes: int,
        opciones: OpcionesProcesamiento,
    ):
        self._fijar_ocupado(False)
        if exito and ruta_out and ruta_out.is_file():
            self.barra_progreso.set_fraction(1.0)
            self._en_vista_previa = False
            self.archivo_resultado = ruta_out
            self.ultima_carpeta = ruta_out.parent
            self.btn_copiar_limpio.set_sensitive(True)

            tam_despues = ruta_out.stat().st_size
            orig_para_ab = None if opciones.reemplazar_original else self.archivo_origen
            base_ia = self.procesador.obtener_base_ia_actual()
            filtro_live = construir_filtros_post_dsp(opciones, duracion=0.0, en_vivo=True)

            self.reproductor.cargar_audios(
                orig_para_ab or ruta_out,
                ruta_out,
                seleccionar_limpio=True,
                base_ia_live=base_ia,
                filtro_live_b=filtro_live,
                usar_live_dsp=False,
                etiqueta_limpio=ruta_out.name,
            )

            self.lbl_resumen_ab.set_text(
                f"✓ ¡Procesamiento completado! Archivo: {ruta_out.name}\n"
                f"Peso original: {formatear_tamano(tam_antes)}   →   "
                f"Peso final ({opciones.formato_salida.upper()}): {formatear_tamano(tam_despues)}   ·   "
                f"Si cambias algún ajuste arriba, exporta en ~1s usando la Fase IA en caché."
            )
            self._fijar_estado(f"✓ {msg} · Compara el antes y después aquí", exito=True)
            notificar("Voz Limpia completado ✓", ruta_out.name, sonido=True)

            # Cambiar automáticamente al Reproductor y Comparador A/B para escuchar el resultado
            self._cambiar_pestana("reproductor")
        else:
            self.barra_progreso.set_fraction(0.0)
            self._fijar_estado(msg, error=True)
            if "cancelado" not in msg.lower():
                notificar("Error en Voz Limpia", msg, critico=True)
        return False

    def _cancelar_proceso(self, *_args):
        if self.ocupado:
            self._fijar_estado("Cancelando y limpiando temporales...")
            self.procesador.cancelar()

    def _fijar_ocupado(self, activo: bool):
        self.ocupado = activo
        self.btn_ejecutar.set_sensitive(not activo)
        self.btn_probar.set_sensitive(not activo)
        if hasattr(self, "btn_reprobar_live"):
            self.btn_reprobar_live.set_sensitive(not activo)
        if hasattr(self, "btn_exportar_live"):
            self.btn_exportar_live.set_sensitive(not activo)
        if activo:
            self.btn_cancelar.show()
        else:
            self.btn_cancelar.hide()

    def _fijar_estado(self, texto: str, exito: bool = False, error: bool = False):
        self.lbl_estado.set_text(texto)
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

    def _copiar_resultado_portapapeles(self, *_args):
        if not self.archivo_resultado or not self.archivo_resultado.is_file():
            return
        uri = f"file://{self.archivo_resultado.resolve()}\r\n"
        try:
            subprocess.run(
                ["wl-copy", "--type", "text/uri-list"],
                input=uri,
                text=True,
                timeout=2.0,
            )
            self._fijar_estado(
                f"✓ Copiado al portapapeles: {self.archivo_resultado.name}",
                exito=True,
            )
        except Exception:
            pass

    def _abrir_carpeta_actual(self, *_args):
        carpeta = self.ultima_carpeta
        if self.archivo_resultado and self.archivo_resultado.is_file():
            carpeta = self.archivo_resultado.parent
        elif self.archivo_origen and self.archivo_origen.is_file():
            carpeta = self.archivo_origen.parent
        try:
            subprocess.Popen(
                ["xdg-open", str(carpeta)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def _al_pulsar_tecla(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.cerrar()
            return True
        if event.keyval == Gdk.KEY_space and self.stack.get_visible_child_name() == "reproductor":
            self.reproductor.alternar_play_pausa()
            return True
        return False

    def cerrar(self):
        if self.ocupado:
            self.procesador.cancelar()
        self.reproductor.detener(reiniciar=False)
        self.procesador.limpiar_cache()
        self.win.destroy()

    def _al_destruir(self, *_args):
        if self.ocupado:
            self.procesador.cancelar()
        self.reproductor.detener(reiniciar=False)
        self.procesador.limpiar_cache()
        Gtk.main_quit()

    def ejecutar(self):
        self.win.show_all()
        self.btn_cancelar.hide()
        Gtk.main()
