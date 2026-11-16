"""Motor de procesamiento de voz con IA (DeepFilterNet 3 + RNNoise + Cadena DSP Estudio)."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import urllib.request

from .tema import HOME, obtener_metadatos_audio

BASE_DATOS_IA = HOME / ".local/share/dotfiles/voz-limpia"
BIN_DIR = BASE_DATOS_IA / "bin"
MODELS_DIR = BASE_DATOS_IA / "models"

DEEPFILTER_BIN = BIN_DIR / "deep-filter"
RNNOISE_BD = MODELS_DIR / "bd.rnnn"
RNNOISE_SH = MODELS_DIR / "sh.rnnn"

URL_DEEPFILTER = (
    "https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/"
    "deep-filter-0.5.6-x86_64-unknown-linux-musl"
)
URL_RNNOISE_BD = (
    "https://raw.githubusercontent.com/GregorR/rnnoise-models/master/"
    "beguiling-drafter-2018-08-30/bd.rnnn"
)
URL_RNNOISE_SH = (
    "https://raw.githubusercontent.com/GregorR/rnnoise-models/master/"
    "somnolent-hogwash-2018-09-01/sh.rnnn"
)

PERFILES = {
    "estudio": {
        "nombre": "🎙️  Estudio / Podcast (Recomendado)",
        "descripcion": "Elimina fondo y ruido con IA (DeepFilterNet 3), da cuerpo cálido y nivela a -16 LUFS.",
        "usar_deepfilter": True,
        "intensidad_ruido": "maxima",
        "aislar_voz_principal": "moderado",
        "quitar_eco": True,
        "tono_voz": "locutor",
        "normalizar_lufs": True,
    },
    "aislar_voz": {
        "nombre": "👥  Anti-Voces Secundarias y Eco",
        "descripcion": "Suprime murmullos, gente hablando lejos y reverberación de salón; prioriza la voz cercana.",
        "usar_deepfilter": True,
        "intensidad_ruido": "maxima",
        "aislar_voz_principal": "estricto",
        "quitar_eco": True,
        "tono_voz": "claridad",
        "normalizar_lufs": True,
    },
    "rapido": {
        "nombre": "⚡  Limpieza Rápida y Natural",
        "descripcion": "Quita ruido constante y nivela el volumen ultrarrápido conservando el timbre natural.",
        "usar_deepfilter": False,
        "intensidad_ruido": "equilibrada",
        "aislar_voz_principal": "moderado",
        "quitar_eco": False,
        "tono_voz": "natural",
        "normalizar_lufs": True,
    },
    "personalizado": {
        "nombre": "🎛️  Personalizado",
        "descripcion": "Ajuste manual de cada etapa del procesador neuronal y acústico.",
    },
}

FORMATOS_SALIDA = [
    ("m4a", "M4A · AAC 192 kbps (Ligero y alta calidad · Recomendado)"),
    ("mp3", "MP3 · 320 kbps (Compatible universal)"),
    ("opus", "OPUS · 160 kbps (Máxima eficiencia en voz)"),
    ("flac", "FLAC · Sin pérdida comprimido"),
    ("wav", "WAV · PCM 48 kHz (Sin comprimir para edición)"),
]

INTENSIDADES_RUIDO = [
    ("suave", "Suave (22 dB · Conserva ambiente natural)"),
    ("equilibrada", "Equilibrada (48 dB · Limpieza limpia sin artefactos)"),
    ("maxima", "Máxima (100 dB · Silencio total de fondo)"),
]

NIVELES_AISLAMIENTO = [
    ("off", "Desactivado (Conservar todas las voces)"),
    ("moderado", "Moderado (Atenuar murmullos y voces lejanas)"),
    ("estricto", "Estricto (Aislar solo voz cercana + Puerta firme)"),
]

TONOS_VOZ = [
    ("natural", "Natural (Sin colorear el timbre)"),
    ("locutor", "Locutor Podcast (Cuerpo grave, presencia y De-Esser)"),
    ("claridad", "Claridad / Reunión (Máxima nitidez de dicción)"),
]


@dataclass
class OpcionesProcesamiento:
    perfil: str = "estudio"
    usar_deepfilter: bool = True
    intensidad_ruido: str = "maxima"          # "suave" | "equilibrada" | "maxima"
    aislar_voz_principal: str = "moderado"   # "off" | "moderado" | "estricto"
    quitar_eco: bool = True
    tono_voz: str = "locutor"                # "natural" | "locutor" | "claridad"
    normalizar_lufs: bool = True
    formato_salida: str = "m4a"              # "m4a" | "mp3" | "opus" | "flac" | "wav"
    reemplazar_original: bool = False
    carpeta_destino: Path | None = None


def estado_motores_ia() -> dict:
    """Verifica si los binarios y modelos de IA están listos localmente."""
    df_ok = DEEPFILTER_BIN.is_file() and os.access(DEEPFILTER_BIN, os.X_OK)
    rn_ok = RNNOISE_BD.is_file() and RNNOISE_SH.is_file()
    return {
        "deepfilter": df_ok,
        "rnnoise": rn_ok,
        "listo": df_ok and rn_ok,
    }


def asegurar_motores_ia(cb_estado=None) -> bool:
    """Descarga automáticamente DeepFilterNet 3 y modelos RNNoise si faltan."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if not (DEEPFILTER_BIN.is_file() and os.access(DEEPFILTER_BIN, os.X_OK)):
            if cb_estado:
                cb_estado("Descargando motor neuronal DeepFilterNet 3...", 0.05)
            tmp_df = DEEPFILTER_BIN.with_suffix(".tmp")
            urllib.request.urlretrieve(URL_DEEPFILTER, str(tmp_df))
            tmp_df.chmod(0o755)
            tmp_df.replace(DEEPFILTER_BIN)

        if not RNNOISE_BD.is_file():
            if cb_estado:
                cb_estado("Descargando modelo neuronal anti-murmullos (RNNoise BD)...", 0.08)
            urllib.request.urlretrieve(URL_RNNOISE_BD, str(RNNOISE_BD))

        if not RNNOISE_SH.is_file():
            if cb_estado:
                cb_estado("Descargando modelo neuronal de voz (RNNoise SH)...", 0.10)
            urllib.request.urlretrieve(URL_RNNOISE_SH, str(RNNOISE_SH))

        return True
    except Exception:
        return False


def construir_filtros_ffmpeg(opciones: OpcionesProcesamiento, duracion: float = 0.0) -> str:
    """Construye la cadena de filtros de audio (DSP + RNNoise) para ffmpeg."""
    filtros: list[str] = []

    # 1. Paso alto para eliminar retumbo grave, viento y golpes de micrófono
    f_hp = 105 if opciones.tono_voz == "claridad" else 85
    filtros.append(f"highpass=f={f_hp}:poles=2")

    # 2. Eliminación de chasquidos y clics de boca
    filtros.append("adeclick=w=55:o=75:t=2.5")

    # 3. Red neuronal RNNoise (específica para separar voz humana de murmullos/fondo)
    if opciones.aislar_voz_principal == "estricto" and RNNOISE_BD.is_file():
        filtros.append(f"arnndn=m='{RNNOISE_BD}':mix=0.92")
    elif opciones.aislar_voz_principal == "moderado" and RNNOISE_BD.is_file():
        filtros.append(f"arnndn=m='{RNNOISE_BD}':mix=0.68")
    elif not opciones.usar_deepfilter and RNNOISE_SH.is_file():
        mix_rn = {"suave": 0.55, "equilibrada": 0.80, "maxima": 0.95}.get(
            opciones.intensidad_ruido, 0.80
        )
        filtros.append(f"arnndn=m='{RNNOISE_SH}':mix={mix_rn}")

    # 4. Supresión espectral dinámica de ruido estacionario residual
    nr_db = {"suave": 10, "equilibrada": 16, "maxima": 24}.get(
        opciones.intensidad_ruido, 16
    )
    if not opciones.usar_deepfilter or opciones.intensidad_ruido == "maxima":
        filtros.append(f"afftdn=nr={nr_db}:nf=-42:tn=1")

    # 5. Puerta de ruido inteligente (Noise Gate) para callar voces secundarias en silencios
    if opciones.aislar_voz_principal == "estricto":
        # Umbral más firme (-28 dB) y caída rápida para cortar conversaciones ajenas y eco
        filtros.append(
            "agate=threshold=0.04:ratio=4.5:attack=12:release=180:range=0.04:knee=2.5"
        )
    elif opciones.aislar_voz_principal == "moderado":
        # Puerta suave (-35 dB) que limpia los silencios entre frases sin cortar respiraciones
        filtros.append(
            "agate=threshold=0.018:ratio=2.8:attack=15:release=260:range=0.08:knee=2.8"
        )

    # 6. Modelado tonal de la voz (EQ + De-Esser)
    if opciones.tono_voz == "locutor":
        # Cuerpo cálido en 135 Hz, limpieza de encajonamiento en 250 Hz, presencia en 3.2 kHz y aire
        filtros.extend([
            "equalizer=f=135:t=q:w=1.2:g=2.5",
            "equalizer=f=250:t=q:w=1.5:g=-3.0",
            "equalizer=f=3200:t=q:w=1.4:g=3.0",
            "equalizer=f=9500:t=q:w=1.2:g=1.8",
            "deesser=i=0.35:m=0.5:f=0.5:s=o",
        ])
    elif opciones.tono_voz == "claridad":
        # Recorte de graves turbios y realce de inteligibilidad vocal (1.8 kHz - 4 kHz)
        filtros.extend([
            "equalizer=f=240:t=q:w=1.4:g=-4.0",
            "equalizer=f=2400:t=q:w=1.2:g=3.8",
            "equalizer=f=4200:t=q:w=1.4:g=2.5",
            "deesser=i=0.4:m=0.5:f=0.5:s=o",
        ])

    # 7. Compresión vocal y normalización de sonoridad (Podcast -16 LUFS)
    if opciones.normalizar_lufs:
        filtros.extend([
            "acompressor=threshold=-20dB:ratio=2.5:attack=15:release=200:makeup=2dB:knee=3dB",
            "speechnorm=p=0.85:e=6.0:r=0.0001:t=0.01:l=1",
        ])
        # loudnorm requiere ventana >= 3s para evitar NaN en clips muy cortos o casi mudos
        if duracion == 0.0 or duracion >= 3.5:
            filtros.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        else:
            filtros.append("alimiter=limit=0.84:level=false")

    return ",".join(filtros)


def parametros_encoder(formato: str) -> list[str]:
    """Devuelve los argumentos de codificación de ffmpeg según el formato elegido."""
    if formato == "m4a":
        return ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    if formato == "mp3":
        return ["-c:a", "libmp3lame", "-b:a", "320k"]
    if formato == "opus":
        return ["-c:a", "libopus", "-b:a", "160k", "-vbr", "on"]
    if formato == "flac":
        return ["-c:a", "flac", "-compression_level", "8"]
    return ["-c:a", "pcm_s16le"]


class ProcesadorVoz:
    """Orquesta el procesamiento de voz con soporte de progreso en tiempo real y cancelación."""

    TAMANO_SEGMENTO_SEG = 180  # Segmentos de 3 minutos para archivos largos

    def __init__(self):
        self.cancelar_evento = threading.Event()
        self._procesos_activos: list[subprocess.Popen] = []
        self._lock = threading.Lock()

    def cancelar(self) -> None:
        self.cancelar_evento.set()
        with self._lock:
            for proc in list(self._procesos_activos):
                try:
                    proc.terminate()
                except Exception:
                    pass

    def _ejecutar_cmd(self, cmd: list[str]) -> bool:
        if self.cancelar_evento.is_set():
            return False
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        with self._lock:
            self._procesos_activos.append(proc)
        try:
            _, _ = proc.communicate()
            return proc.returncode == 0 and not self.cancelar_evento.is_set()
        finally:
            with self._lock:
                if proc in self._procesos_activos:
                    self._procesos_activos.remove(proc)

    def _argumentos_deepfilter(self, opciones: OpcionesProcesamiento, dir_salida: Path) -> list[str]:
        atten = {"suave": "22", "equilibrada": "48", "maxima": "100"}.get(
            opciones.intensidad_ruido, "100"
        )
        cmd = [
            str(DEEPFILTER_BIN),
            "-D",  # Compensar retardo para alineación exacta A/B
            "-a", atten,
            "-o", str(dir_salida),
        ]

        # Post-Filter para suprimir reverberación y voces lejanas de bajo SNR
        if opciones.quitar_eco or opciones.aislar_voz_principal != "off":
            cmd.append("--pf")
            if opciones.aislar_voz_principal == "estricto":
                cmd.extend(["--pf-beta=0.085", "--min-db-thresh=-7"])
            elif opciones.aislar_voz_principal == "moderado":
                cmd.extend(["--pf-beta=0.045", "--min-db-thresh=-11"])
            else:
                cmd.extend(["--pf-beta=0.025"])

        return cmd

    def procesar(
        self,
        archivo_entrada: Path,
        opciones: OpcionesProcesamiento,
        cb_progreso=None,
    ) -> tuple[ bool, Path | None, str ]:
        """
        Ejecuta el pipeline completo sobre `archivo_entrada`.
        Limpia garantizadamente cualquier archivo temporal al finalizar o cancelar.
        Devuelve (exito, ruta_salida, mensaje).
        """
        self.cancelar_evento.clear()

        if not archivo_entrada.is_file():
            return False, None, "El archivo de origen no existe."

        asegurar_motores_ia(cb_estado=cb_progreso)

        meta = obtener_metadatos_audio(archivo_entrada)
        duracion = max(1.0, meta["duracion"])

        # Determinar ruta final de salida
        ext = opciones.formato_salida.lower().lstrip(".")
        dir_destino = opciones.carpeta_destino or archivo_entrada.parent
        dir_destino.mkdir(parents=True, exist_ok=True)

        if opciones.reemplazar_original:
            # Si cambia la extensión o reemplaza el mismo archivo
            ruta_final = archivo_entrada.with_suffix(f".{ext}")
        else:
            stem = archivo_entrada.stem
            if stem.endswith("_limpio"):
                stem_salida = stem
            else:
                stem_salida = f"{stem}_limpio"
            ruta_final = dir_destino / f"{stem_salida}.{ext}"
            if ruta_final.resolve() == archivo_entrada.resolve():
                ruta_final = dir_destino / f"{stem}_procesado.{ext}"

        # Directorio temporal aislado en /tmp (se borra SIEMPRE en el bloque finally)
        workdir = Path(tempfile.mkdtemp(prefix="voz_limpia_work_"))

        try:
            usar_df = opciones.usar_deepfilter and DEEPFILTER_BIN.is_file()

            if usar_df:
                if cb_progreso:
                    cb_progreso("Preparando bloques de audio a 48 kHz...", 0.08)

                dir_segmentos_in = workdir / "seg_in"
                dir_segmentos_out = workdir / "seg_out"
                dir_segmentos_in.mkdir(parents=True, exist_ok=True)
                dir_segmentos_out.mkdir(parents=True, exist_ok=True)

                # Dividir en segmentos WAV mono 48 kHz para procesamiento paralelo en CPU
                patron_seg = str(dir_segmentos_in / "seg_%04d.wav")
                cmd_split = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(archivo_entrada),
                    "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le",
                    "-f", "segment", "-segment_time", str(self.TAMANO_SEGMENTO_SEG),
                    patron_seg,
                ]
                if not self._ejecutar_cmd(cmd_split):
                    if self.cancelar_evento.is_set():
                        return False, None, "Proceso cancelado por el usuario."
                    return False, None, "No se pudo decodificar el archivo de audio."

                segmentos = sorted(dir_segmentos_in.glob("seg_*.wav"))
                if not segmentos:
                    return False, None, "No se encontraron pistas de audio válidas."

                total_seg = len(segmentos)
                completados = 0
                base_cmd_df = self._argumentos_deepfilter(opciones, dir_segmentos_out)

                # Ejecutar DeepFilterNet 3 en paralelo (hasta 4 hilos simultáneos)
                max_workers = min(4, max(1, (os.cpu_count() or 4) // 4), total_seg)

                def _procesar_segmento(seg_path: Path) -> bool:
                    return self._ejecutar_cmd(base_cmd_df + [str(seg_path)])

                if cb_progreso:
                    cb_progreso(
                        f"IA DeepFilterNet 3: limpiando voz (0/{total_seg} bloques)...",
                        0.15,
                    )

                with ThreadPoolExecutor(max_workers=max_workers) as pool:
                    futuros = {pool.submit(_procesar_segmento, s): s for s in segmentos}
                    for fut in as_completed(futuros):
                        if self.cancelar_evento.is_set():
                            break
                        if not fut.result():
                            return False, None, "Fallo durante el filtrado neuronal DeepFilterNet."
                        completados += 1
                        fraccion = 0.15 + 0.55 * (completados / total_seg)
                        if cb_progreso:
                            cb_progreso(
                                f"IA DeepFilterNet 3: limpiando voz ({completados}/{total_seg} bloques)...",
                                fraccion,
                            )

                if self.cancelar_evento.is_set():
                    return False, None, "Proceso cancelado por el usuario."

                # Preparar lista de concatenación para ffmpeg
                segmentos_limpios = sorted(dir_segmentos_out.glob("seg_*.wav"))
                lista_concat = workdir / "concat.txt"
                lista_concat.write_text(
                    "\n".join(f"file '{s}'" for s in segmentos_limpios),
                    encoding="utf-8",
                )
                argumentos_entrada_dsp = ["-f", "concat", "-safe", "0", "-i", str(lista_concat)]
            else:
                argumentos_entrada_dsp = ["-i", str(archivo_entrada)]

            # Etapa final: Cadena DSP de estudio (RNNoise + Gate + EQ + De-Esser + Loudnorm) + Codificación
            if cb_progreso:
                cb_progreso("Aplicando puerta anti-murmullos, ecualización y masterización (-16 LUFS)...", 0.75)

            cadena_af = construir_filtros_ffmpeg(opciones, duracion=duracion)
            archivo_temp_salida = workdir / f"salida_final.{ext}"

            cmd_master = [
                "ffmpeg", "-y", "-hide_banner", "-nostats", "-progress", "pipe:1",
                *argumentos_entrada_dsp,
                "-vn",
                "-af", cadena_af,
                "-ar", "48000",
                "-ac", "1",
                *parametros_encoder(ext),
                str(archivo_temp_salida),
            ]

            log_master = workdir / "ffmpeg_master.log"
            with open(log_master, "w", encoding="utf-8", errors="replace") as f_err:
                proc = subprocess.Popen(
                    cmd_master,
                    stdout=subprocess.PIPE,
                    stderr=f_err,
                    text=True,
                    bufsize=1,
                )
                with self._lock:
                    self._procesos_activos.append(proc)

                try:
                    if proc.stdout:
                        for linea in proc.stdout:
                            if self.cancelar_evento.is_set():
                                proc.terminate()
                                break
                            linea = linea.strip()
                            if linea.startswith("out_time_ms="):
                                try:
                                    us = int(linea.split("=", 1)[1])
                                    seg_actual = us / 1_000_000.0
                                    base_p = 0.75 if usar_df else 0.10
                                    rango_p = 0.23 if usar_df else 0.88
                                    p = min(0.98, base_p + rango_p * min(1.0, seg_actual / duracion))
                                    if cb_progreso:
                                        cb_progreso(
                                            f"Masterizando y codificando ({int(p * 100)}%)...",
                                            p,
                                        )
                                except ValueError:
                                    pass
                    proc.wait()
                finally:
                    with self._lock:
                        if proc in self._procesos_activos:
                            self._procesos_activos.remove(proc)

            if self.cancelar_evento.is_set():
                return False, None, "Proceso cancelado por el usuario."

            if proc.returncode != 0 or not archivo_temp_salida.is_file():
                err_txt = ""
                if log_master.is_file():
                    lineas_err = log_master.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                    err_txt = lineas_err[-1] if lineas_err else ""
                return False, None, f"Error en la masterización de audio. {err_txt}"

            # Si es modo reemplazo, respaldar temporalmente por seguridad o mover de forma atómica
            shutil.move(str(archivo_temp_salida), str(ruta_final))
            if opciones.reemplazar_original and ruta_final.resolve() != archivo_entrada.resolve():
                try:
                    archivo_entrada.unlink()
                except OSError:
                    pass

            if cb_progreso:
                cb_progreso("¡Voz limpia y masterizada con éxito!", 1.0)

            return True, ruta_final, f"Guardado en {ruta_final.name}"

        finally:
            # Garantía absoluta: eliminar siempre todos los archivos temporales
            shutil.rmtree(workdir, ignore_errors=True)
