#!/usr/bin/env python3
"""
Jarvis - Asistente de voz interactivo para NixOS / Hyprland.
Muestra un widget flotante con forma de bola de energía (Arc Reactor / Plasma Orb)
en la esquina inferior derecha mediante GtkLayerShell.
"""

import os
import sys
import time
import math
import re
import signal
import subprocess
import threading
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

USER = os.environ.get("USER", "nova")
HOME = Path.home()
PIDFILE = Path(f"/tmp/jarvis_{USER}.pid")
STOPFILE = Path(f"/tmp/jarvis_{USER}.stop")
AUDIO_FILE = Path(f"/tmp/jarvis_audio_{USER}.wav")
WHISPER_DIR = HOME / ".local/share/whisper"
WHISPER_MODEL = WHISPER_DIR / "ggml-base.bin"
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
TEMA_CONF = HOME / "dotfiles/tema/tema.conf"
VOZ_SCRIPT = HOME / "dotfiles/utils/voz.sh"

MAC_OLLAMA_URL = "http://100.109.249.113:11434/api/generate"


def leer_color_tema(clave: str, defecto: str) -> tuple[float, float, float]:
    """Lee un color hexadecimal del tema activo y lo devuelve en rango 0.0 - 1.0."""
    try:
        if TEMA_CONF.is_file():
            for linea in TEMA_CONF.read_text(encoding="utf-8").splitlines():
                linea = linea.strip()
                if linea.startswith(f"{clave}="):
                    val = linea.split("=", 1)[1].strip().strip('"\'')
                    if val.startswith("#") and len(val) == 7:
                        r = int(val[1:3], 16) / 255.0
                        g = int(val[3:5], 16) / 255.0
                        b = int(val[5:7], 16) / 255.0
                        return (r, g, b)
    except Exception:
        pass
    r = int(defecto[1:3], 16) / 255.0
    g = int(defecto[3:5], 16) / 255.0
    b = int(defecto[5:7], 16) / 255.0
    return (r, g, b)


def buscar_whisper_cli() -> str:
    """Encuentra el ejecutable whisper-cli en PATH o en el nix store."""
    en_path = subprocess.run(["which", "whisper-cli"], capture_output=True, text=True)
    if en_path.returncode == 0 and en_path.stdout.strip():
        return en_path.stdout.strip()
    candidatos = list(Path("/nix/store").glob("*-whisper-cpp-*/bin/whisper-cli"))
    if candidatos:
        return str(candidatos[0])
    return "whisper-cli"


def asegurar_modelo_whisper():
    """Descarga el modelo ggml-base si aún no existe."""
    if not WHISPER_MODEL.is_file():
        WHISPER_DIR.mkdir(parents=True, exist_ok=True)
        tmp = WHISPER_MODEL.with_suffix(".tmp")
        try:
            subprocess.run(
                ["curl", "-sSL", "-o", str(tmp), MODEL_URL],
                check=True,
                timeout=60,
            )
            tmp.rename(WHISPER_MODEL)
        except Exception as e:
            if tmp.exists():
                tmp.unlink()
            print(f"[Jarvis] Error descargando modelo Whisper: {e}", file=sys.stderr)


class JarvisWindow(Gtk.Window):
    def __init__(self):
        super().__init__()

        # Inicialización de GtkLayerShell para Wayland
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM, 55)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 35)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)

        # Configuración de transparencia y tamaño
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_size_request(260, 260)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        # Colores del tema
        self.color_acento = leer_color_tema("ACENTO", "#a77bf3")
        self.color_secundario = leer_color_tema("SECUNDARIO", "#7ee08f")
        self.color_info = leer_color_tema("INFO", "#8fd3f4")

        # Estados: RECORDING -> PROCESSING -> SPEAKING -> CLOSING
        self.state = "RECORDING"
        self.phase = 0.0
        self.alpha = 0.0  # Para fade-in suave
        self.target_alpha = 1.0
        self.subtitle = "● Escuchando... [Espacio]"
        self.response_text = ""
        self.recorder_proc = None
        self.is_done = False

        # Área de dibujo con Cairo
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.connect("draw", self.on_draw)
        self.draw_area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.draw_area.connect("button-press-event", self.on_button_press)
        self.add(self.draw_area)

        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.on_destroy)

        # Iniciar grabación de micrófono
        self.iniciar_grabacion()

        # Timers: animación a 30 FPS y monitor de stopfile
        GLib.timeout_add(33, self.on_tick)
        GLib.timeout_add(100, self.verificar_stopfile)

    def iniciar_grabacion(self):
        """Inicia la captura de audio en 16kHz mono con ffmpeg."""
        if AUDIO_FILE.exists():
            try:
                AUDIO_FILE.unlink()
            except Exception:
                pass

        try:
            self.recorder_proc = subprocess.Popen(
                [
                    "ffmpeg", "-y", "-loglevel", "quiet",
                    "-f", "pulse", "-i", "default",
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                    str(AUDIO_FILE)
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[Jarvis] Error iniciando grabación: {e}", file=sys.stderr)
            self.subtitle = "Error de micrófono"

    def terminar_grabacion_y_procesar(self):
        """Detiene la grabación y pasa al estado PROCESSING en un hilo secundario."""
        if self.state != "RECORDING":
            return
        self.state = "PROCESSING"
        self.subtitle = "◌ Procesando orden..."

        if self.recorder_proc:
            try:
                self.recorder_proc.terminate()
                self.recorder_proc.wait(timeout=1.5)
            except Exception:
                try:
                    self.recorder_proc.kill()
                except Exception:
                    pass
            self.recorder_proc = None

        # Procesar en segundo plano para no congelar la UI de Cairo
        threading.Thread(target=self._hilo_proceso_y_respuesta, daemon=True).start()

    def _hilo_proceso_y_respuesta(self):
        """Transcribe el audio y ejecuta la acción orquestada."""
        time.sleep(0.1)
        if not AUDIO_FILE.is_file() or AUDIO_FILE.stat().st_size < 1000:
            self._actualizar_estado_habla("No se detectó audio del micrófono.")
            return

        whisper_bin = buscar_whisper_cli()
        asegurar_modelo_whisper()

        prompt_contexto = "Jarvis, Hermes, terminal, proyecto, git, dotfiles, código, abre, ejecuta, corre, cursor"
        texto_transcrito = ""

        try:
            res = subprocess.run(
                [
                    whisper_bin,
                    "-m", str(WHISPER_MODEL),
                    "-f", str(AUDIO_FILE),
                    "-l", "es",
                    "--no-timestamps",
                    "-nt",
                    "--prompt", prompt_contexto
                ],
                capture_output=True,
                text=True,
                timeout=12,
            )
            lineas = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            texto_transcrito = " ".join(lineas)
        except Exception as e:
            print(f"[Jarvis] Error en Whisper: {e}", file=sys.stderr)

        # Limpiar ruidos comunes de whisper
        texto_limpio = re.sub(r"\[.*?\]|\(.*?\)", "", texto_transcrito).strip()

        if not texto_limpio or len(texto_limpio) < 2:
            self._actualizar_estado_habla("No entendí la orden, por favor intenta de nuevo.")
            return

        print(f"[Jarvis] Reconocido: {texto_limpio}")
        self._actualizar_subtitulo(f"\"{texto_limpio}\"")

        # Orquestador: ejecutar acción y obtener respuesta
        respuesta_voz = self.orquestar_comando(texto_limpio)
        self._actualizar_estado_habla(respuesta_voz)

    def orquestar_comando(self, texto: str) -> str:
        """Enruta la intención hacia la terminal, proyectos, sistema o IA."""
        t_lower = texto.lower()

        # 1. Terminal / Escribir comandos en terminal activa
        # Ej: "escribe en la terminal git status", "corre en la terminal npm test"
        match_terminal = re.search(
            r"(?:escribe|corre|ejecuta)(?: en la terminal)?\s+(?:el comando\s+)?(.+)",
            t_lower
        )
        if match_terminal and ("terminal" in t_lower or "corre" in t_lower or "ejecuta" in t_lower):
            cmd = match_terminal.group(1).strip()
            # Inyectar a la ventana activa con wtype
            try:
                subprocess.Popen(["wtype", cmd + "\n"])
                return f"Comando enviado a la terminal: {cmd}"
            except Exception:
                return f"No pude inyectar el comando a la terminal."

        # 2. Abrir proyectos en Cursor / Sublime / Kitty
        # Ej: "abre el proyecto dotfiles en cursor", "abre context hub"
        match_proyecto = re.search(
            r"abre (?:el )?proyecto\s+([a-zA-Z0-9_\-]+)(?:\s+en\s+([a-zA-Z0-9_\-]+))?",
            t_lower
        )
        if match_proyecto or (t_lower.startswith("abre ") and ("cursor" in t_lower or "proyecto" in t_lower or "dotfiles" in t_lower or "context" in t_lower)):
            nombre_p = ""
            editor = "cursor"

            if match_proyecto:
                nombre_p = match_proyecto.group(1).strip()
                if match_proyecto.group(2):
                    editor = match_proyecto.group(2).strip()
            elif "dotfiles" in t_lower:
                nombre_p = "dotfiles"
            elif "context" in t_lower:
                nombre_p = "context-hub"

            # Encontrar ruta del proyecto
            ruta_p = None
            if nombre_p == "dotfiles":
                ruta_p = HOME / "dotfiles"
            elif "context" in nombre_p:
                for cand in [HOME / "Proyectos/personal/context-hub", HOME / "Proyectos/context-hub"]:
                    if cand.is_dir():
                        ruta_p = cand
                        break
            else:
                for base in [HOME / "Proyectos", HOME / "Proyectos/personal"]:
                    if base.is_dir():
                        for d in base.iterdir():
                            if d.is_dir() and nombre_p in d.name.lower():
                                ruta_p = d
                                break
                    if ruta_p:
                        break

            if ruta_p and ruta_p.is_dir():
                if "sublime" in editor or "subl" in editor:
                    subprocess.Popen(["subl", str(ruta_p)])
                    return f"Abriendo {ruta_p.name} en Sublime Text."
                elif "terminal" in editor or "kitty" in editor:
                    subprocess.Popen(["kitty", "--directory", str(ruta_p)])
                    return f"Abriendo terminal en {ruta_p.name}."
                else:
                    subprocess.Popen(["cursor", str(ruta_p)])
                    return f"Abriendo {ruta_p.name} en Cursor."

        # 3. Control de Sistema y Aplicaciones
        if "terminal" in t_lower or "kitty" in t_lower:
            subprocess.Popen(["kitty"])
            return "Terminal abierta."
        if "navegador" in t_lower or "zen" in t_lower or "internet" in t_lower:
            subprocess.Popen(["flatpak", "run", "app.zen_browser.zen"])
            return "Abriendo navegador Zen."
        if "bloquea" in t_lower or "bloquear" in t_lower:
            subprocess.Popen(["hyprlock"])
            return "Bloqueando pantalla."
        if "gestor de archivos" in t_lower or "archivos" in t_lower or "thunar" in t_lower:
            subprocess.Popen(["thunar"])
            return "Abriendo gestor de archivos."
        if "docker" in t_lower or "lazydocker" in t_lower:
            subprocess.Popen(["kitty", "--class", "lazydocker", "-e", "lazydocker"])
            return "Abriendo Lazydocker."
        if "sube" in t_lower and "volumen" in t_lower:
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%+"])
            return "Subiendo volumen."
        if "baja" in t_lower and "volumen" in t_lower:
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%-"])
            return "Bajando volumen."
        if "silencio" in t_lower or "mute" in t_lower or "mutear" in t_lower:
            subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
            return "Volumen alternado."

        # 4. Agentes IA explícitos
        if "hermes" in t_lower:
            subprocess.Popen(["kitty", "--class", "hermes-agent", "-e", "hermes"])
            return "Iniciando Hermes Agent."
        if "claude" in t_lower:
            subprocess.Popen(["kitty", "-e", "claude"])
            return "Iniciando Claude Code."
        if "antigravity" in t_lower or "agy" in t_lower:
            subprocess.Popen(["kitty", "-e", "agy"])
            return "Iniciando Antigravity."

        # 5. Consulta Inteligente (Ollama en Mac Mini / Llama 3.1)
        prompt_ia = (
            "Eres Jarvis, el asistente de voz inteligente del sistema NixOS de Nova. "
            f"El usuario te ha dicho por voz: \"{texto}\". "
            "Responde en español de forma natural, concisa y directa (máximo 1 o 2 oraciones breves). "
            "Sin texto de relleno, sin markdown ni listas, optimizado para ser leído por voz."
        )

        try:
            import urllib.request
            import json

            payload = json.dumps({
                "model": "llama3.1:8b",
                "prompt": prompt_ia,
                "stream": False
            }).encode("utf-8")

            req = urllib.request.Request(
                MAC_OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                res_ollama = data.get("response", "").strip()
                if res_ollama:
                    return res_ollama
        except Exception:
            pass

        # Fallback si no hay conexión al Mac Mini
        return f"Entendido. Procesando: {texto}"

    def _actualizar_subtitulo(self, texto: str):
        def _cb():
            self.subtitle = texto
            self.draw_area.queue_draw()
            return False
        GLib.idle_add(_cb)

    def _actualizar_estado_habla(self, respuesta: str):
        """Pasa a estado SPEAKING y reproduce la respuesta con voz."""
        def _cb():
            self.state = "SPEAKING"
            self.response_text = respuesta
            self.subtitle = f"🔊 Jarvis: {respuesta[:45]}..." if len(respuesta) > 45 else f"🔊 {respuesta}"
            self.draw_area.queue_draw()
            return False
        GLib.idle_add(_cb)

        # Reproducir voz
        try:
            subprocess.run([str(VOZ_SCRIPT), "--silencio", respuesta], timeout=15)
        except Exception as e:
            print(f"[Jarvis] Error al hablar: {e}", file=sys.stderr)

        # Finalizar y cerrar
        time.sleep(0.4)
        def _cerrar():
            self.state = "CLOSING"
            self.target_alpha = 0.0
            return False
        GLib.idle_add(_cerrar)

    def verificar_stopfile(self):
        """Verifica si jarvis.sh envió señal para detener la escucha."""
        if STOPFILE.exists():
            try:
                STOPFILE.unlink()
            except Exception:
                pass
            if self.state == "RECORDING":
                self.terminar_grabacion_y_procesar()
        return True

    def on_key_press(self, widget, event):
        """Control por teclado: Espacio o Enter para enviar, Escape para cancelar."""
        keyval = event.keyval
        if keyval in (Gdk.KEY_space, Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self.state == "RECORDING":
                self.terminar_grabacion_y_procesar()
                return True
        elif keyval == Gdk.KEY_Escape:
            self.cerrar_inmediato()
            return True
        return False

    def on_button_press(self, widget, event):
        """Clic en la bola de energía: termina la grabación."""
        if self.state == "RECORDING":
            self.terminar_grabacion_y_procesar()
            return True
        elif self.state in ("SPEAKING", "PROCESSING"):
            self.cerrar_inmediato()
            return True
        return False

    def on_tick(self):
        """Loop de animación de 30 FPS."""
        self.phase += 0.06

        # Suavizado de fade-in / fade-out
        if self.alpha < self.target_alpha:
            self.alpha = min(self.target_alpha, self.alpha + 0.12)
        elif self.alpha > self.target_alpha:
            self.alpha = max(self.target_alpha, self.alpha - 0.15)
            if self.alpha <= 0.01:
                self.destroy()
                return False

        self.draw_area.queue_draw()
        return True

    def on_draw(self, widget, cr):
        """Renderizado vectorial de la bola de energía tipo Reactor Arc de Jarvis."""
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx = w / 2.0
        cy = h / 2.0 - 15.0

        # Fondo transparente
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        if self.alpha <= 0.001:
            return

        alpha = self.alpha
        t = self.phase

        # Selección de paleta según estado
        if self.state == "RECORDING":
            r_c, g_c, b_c = self.color_info
            pulse = 0.55 + 0.35 * math.sin(t * 4.0)
            speed = 1.6
        elif self.state == "PROCESSING":
            r_c, g_c, b_c = (0.95, 0.75, 0.25)  # Resplandor dorado/ámbar
            pulse = 0.65 + 0.30 * math.sin(t * 8.0)
            speed = 3.5
        elif self.state == "SPEAKING":
            r_c, g_c, b_c = self.color_secundario  # Verde neón / esmeralda
            pulse = 0.50 + 0.45 * math.sin(t * 6.5)
            speed = 2.0
        else:
            r_c, g_c, b_c = self.color_acento
            pulse = 0.5
            speed = 1.0

        # 1. Aura de Resplandor Exterior (Glow)
        rad_glow = cairo.RadialGradient(cx, cy, 15, cx, cy, 105)
        rad_glow.add_color_stop_rgba(0.0, r_c, g_c, b_c, 0.40 * alpha * pulse)
        rad_glow.add_color_stop_rgba(0.5, r_c * 0.7, g_c * 0.7, b_c * 0.9, 0.18 * alpha * pulse)
        rad_glow.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
        cr.arc(cx, cy, 105, 0, 2 * math.pi)
        cr.set_source(rad_glow)
        cr.fill()

        # 2. Ondas Expansivas de Energía (Ripples)
        for i in range(3):
            wave_r = ((t * 22.0 + i * 28.0) % 65.0) + 38.0
            wave_fade = max(0.0, 1.0 - (wave_r - 38.0) / 65.0)
            cr.set_line_width(1.6)
            cr.set_source_rgba(r_c, g_c, b_c, wave_fade * 0.45 * alpha)
            cr.arc(cx, cy, wave_r, 0, 2 * math.pi)
            cr.stroke()

        # 3. Anillos de Reactor Giratorios (Segmented Arcs)
        # Anillo exterior girando horario
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(t * speed)
        cr.set_line_width(2.4)
        cr.set_source_rgba(r_c, g_c, b_c, 0.85 * alpha)
        for i in range(3):
            ang = i * (2 * math.pi / 3)
            cr.arc(0, 0, 68, ang, ang + 1.2)
            cr.stroke()
        cr.restore()

        # Anillo interior girando antihorario
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(-t * speed * 1.4)
        cr.set_line_width(1.8)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.75 * alpha)
        for i in range(4):
            ang = i * (2 * math.pi / 4)
            cr.arc(0, 0, 54, ang, ang + 0.8)
            cr.stroke()
        cr.restore()

        # 4. Núcleo de Plasma (Core Sphere)
        core_r = 36.0 + 3.0 * math.sin(t * 5.0)
        rad_core = cairo.RadialGradient(cx - core_r * 0.3, cy - core_r * 0.3, 2, cx, cy, core_r)
        rad_core.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.98 * alpha)  # Centro blanco brillante
        rad_core.add_color_stop_rgba(0.35, r_c, g_c, b_c, 0.92 * alpha)  # Color energía principal
        rad_core.add_color_stop_rgba(0.80, r_c * 0.4, g_c * 0.4, b_c * 0.8, 0.80 * alpha)
        rad_core.add_color_stop_rgba(1.0, 0.05, 0.05, 0.15, 0.0)

        cr.arc(cx, cy, core_r, 0, 2 * math.pi)
        cr.set_source(rad_core)
        cr.fill()

        # 5. Insignia / Subtítulo inferior
        self.dibujar_insignia(cr, cx, h - 28, alpha)

    def dibujar_insignia(self, cr, x, y, alpha):
        """Dibuja la píldora translúcida con el estado o subtítulo."""
        texto = self.subtitle
        cr.select_font_face("JetBrainsMono Nerd Font", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(10.5)
        extents = cr.text_extents(texto)

        badge_w = min(240, max(140, extents.width + 24))
        badge_h = 24
        bx = x - badge_w / 2.0
        by = y - badge_h / 2.0
        r = 12

        # Fondo píldora
        cr.new_sub_path()
        cr.arc(bx + badge_w - r, by + r, r, -math.pi / 2, 0)
        cr.arc(bx + badge_w - r, by + badge_h - r, r, 0, math.pi / 2)
        cr.arc(bx + r, by + badge_h - r, r, math.pi / 2, math.pi)
        cr.arc(bx + r, by + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

        cr.set_source_rgba(0.06, 0.04, 0.12, 0.88 * alpha)
        cr.fill_preserve()

        # Borde píldora
        cr.set_line_width(1.2)
        cr.set_source_rgba(self.color_acento[0], self.color_acento[1], self.color_acento[2], 0.70 * alpha)
        cr.stroke()

        # Texto dentro de la píldora
        tx = x - extents.width / 2.0
        ty = y + extents.height / 2.0 - 2
        cr.move_to(tx, ty)
        cr.set_source_rgba(0.95, 0.93, 1.0, 0.95 * alpha)
        cr.show_text(texto)

    def cerrar_inmediato(self):
        """Detiene cualquier proceso y cierra la ventana."""
        if self.recorder_proc:
            try:
                self.recorder_proc.terminate()
                self.recorder_proc.kill()
            except Exception:
                pass
        self.target_alpha = 0.0
        self.state = "CLOSING"

    def on_destroy(self, widget):
        if PIDFILE.exists():
            try:
                PIDFILE.unlink()
            except Exception:
                pass
        if STOPFILE.exists():
            try:
                STOPFILE.unlink()
            except Exception:
                pass
        if AUDIO_FILE.exists():
            try:
                AUDIO_FILE.unlink()
            except Exception:
                pass
        Gtk.main_quit()


def manejar_sigusr1(signum, frame):
    """Manejo de señal para terminar grabación desde jarvis.sh."""
    STOPFILE.touch()


def main():
    signal.signal(signal.SIGUSR1, manejar_sigusr1)
    PIDFILE.write_text(str(os.getpid()))

    win = JarvisWindow()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
