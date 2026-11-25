"""Motor de procesamiento de voz con IA (DeepFilterNet 3 + RNNoise + Reconstructor Vocos + DSP en 2 fases)."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import urllib.request

from .reconstructor import (
    MODOS_RECONSTRUCCION,
    asegurar_modelos_reconstruccion,
    motores_reconstruccion_listos,
    reconstruir_archivo_wav,
)
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
        "nombre": "🎙️  Estudio / Voz Clara (Recomendado)",
        "descripcion": "Limpia el fondo con DeepFilterNet 3, quita resonancia de sala y nivela a -16 LUFS con timbre 100% humano.",
        "usar_deepfilter": True,
        "intensidad_ruido": "equilibrada",
        "aislar_voz_principal": "off",
        "quitar_eco": True,
        "tono_voz": "claridad",
        "normalizar_lufs": True,
        "reconstruir_voz": "off",
    },
    "rescate": {
        "nombre": "🔥  Rescate Bulla Fuerte",
        "descripcion": "Para ruido muy fuerte: supresión máxima DeepFilterNet 3 + brillo sutil IA sin voz robótica.",
        "usar_deepfilter": True,
        "intensidad_ruido": "maxima",
        "aislar_voz_principal": "moderado",
        "quitar_eco": True,
        "tono_voz": "claridad",
        "normalizar_lufs": True,
        "reconstruir_voz": "natural",
    },
    "aislar_voz": {
        "nombre": "👥  Anti-Voces Secundarias",
        "descripcion": "Atenúa murmullos lejanos y ecos de habitación con expansor suave sin cortar sílabas.",
        "usar_deepfilter": True,
        "intensidad_ruido": "maxima",
        "aislar_voz_principal": "estricto",
        "quitar_eco": True,
        "tono_voz": "claridad",
        "normalizar_lufs": True,
        "reconstruir_voz": "off",
    },
    "rapido": {
        "nombre": "⚡  Limpieza Rápida y Natural",
        "descripcion": "Quita ruido constante con RNNoise y nivela el volumen ultrarrápido conservando el timbre natural.",
        "usar_deepfilter": False,
        "intensidad_ruido": "equilibrada",
        "aislar_voz_principal": "off",
        "quitar_eco": False,
        "tono_voz": "natural",
        "normalizar_lufs": True,
        "reconstruir_voz": "off",
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
    ("off", "Desactivado · Sin compuerta (Cero cortes de voz · Recomendado)"),
    ("moderado", "Moderado · Expansor suave (Atenúa pausas sin cortar palabras)"),
    ("estricto", "Estricto · Puerta firme (Solo voz cercana)"),
]

TONOS_VOZ = [
    ("natural", "Natural · Timbre exacto (Sin colorear)"),
    ("claridad", "Claridad / Voz Nítida · Sin eco de caja (Recomendado)"),
    ("locutor", "Locutor Podcast · Cálido equilibrado y De-Esser"),
]


@dataclass
class OpcionesProcesamiento:
    perfil: str = "estudio"
    usar_deepfilter: bool = True
    intensidad_ruido: str = "equilibrada"       # "suave" | "equilibrada" | "maxima"
    aislar_voz_principal: str = "off"           # "off" | "moderado" | "estricto"
    quitar_eco: bool = True
    tono_voz: str = "claridad"                  # "natural" | "claridad" | "locutor"
    normalizar_lufs: bool = True
    reconstruir_voz: str = "off"                # "off" | "natural" | "estudio" | "rescate"
    formato_salida: str = "m4a"                 # "m4a" | "mp3" | "opus" | "flac" | "wav"
    reemplazar_original: bool = False
    carpeta_destino: Path | None = None


def estado_motores_ia() -> dict:
    """Verifica si los binarios y modelos de IA están listos localmente."""
    df_ok = DEEPFILTER_BIN.is_file() and os.access(DEEPFILTER_BIN, os.X_OK)
    rn_ok = RNNOISE_BD.is_file() and RNNOISE_SH.is_file()
    rec_ok = motores_reconstruccion_listos()
    return {
        "deepfilter": df_ok,
        "rnnoise": rn_ok,
        "reconstructor": rec_ok,
        "listo": df_ok and rn_ok and rec_ok,
    }


def asegurar_motores_ia(cb_estado=None, incluir_reconstructor: bool = True) -> bool:
    """Descarga automáticamente DeepFilterNet 3, RNNoise y modelos Vocos si faltan."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if not (DEEPFILTER_BIN.is_file() and os.access(DEEPFILTER_BIN, os.X_OK)):
            if cb_estado:
                cb_estado("Descargando motor neuronal DeepFilterNet 3...", 0.04)
            tmp_df = DEEPFILTER_BIN.with_suffix(".tmp")
            urllib.request.urlretrieve(URL_DEEPFILTER, str(tmp_df))
            tmp_df.chmod(0o755)
            tmp_df.replace(DEEPFILTER_BIN)

        if not RNNOISE_BD.is_file():
            if cb_estado:
                cb_estado("Descargando modelo neuronal anti-murmullos (RNNoise BD)...", 0.05)
            urllib.request.urlretrieve(URL_RNNOISE_BD, str(RNNOISE_BD))

        if not RNNOISE_SH.is_file():
            if cb_estado:
                cb_estado("Descargando modelo neuronal de voz (RNNoise SH)...", 0.06)
            urllib.request.urlretrieve(URL_RNNOISE_SH, str(RNNOISE_SH))

        if incluir_reconstructor and not motores_reconstruccion_listos():
            if not asegurar_modelos_reconstruccion(cb_estado=cb_estado):
                return False

        return True
    except Exception:
        return False


def construir_filtros_pre_ia(opciones: OpcionesProcesamiento) -> list[str]:
    """
    Construye los filtros ligeros previos de Fase 1 (antes de Vocos / cuando no hay DeepFilter).
    No apila RNNoise ni FFT sobre DeepFilterNet 3 para evitar artefactos metálicos/robóticos.
    """
    filtros: list[str] = [
        "highpass=f=80:poles=2",
        "adeclick=w=55:o=75:t=2.5",
    ]

    if not opciones.usar_deepfilter:
        if opciones.aislar_voz_principal in ("moderado", "estricto") and RNNOISE_BD.is_file():
            mix_bd = 0.85 if opciones.aislar_voz_principal == "estricto" else 0.65
            filtros.append(f"arnndn=m='{RNNOISE_BD}':mix={mix_bd}")
        elif RNNOISE_SH.is_file():
            mix_rn = {"suave": 0.55, "equilibrada": 0.80, "maxima": 0.92}.get(
                opciones.intensidad_ruido, 0.80
            )
            filtros.append(f"arnndn=m='{RNNOISE_SH}':mix={mix_rn}")

        nr_db = {"suave": 10, "equilibrada": 15, "maxima": 22}.get(
            opciones.intensidad_ruido, 15
        )
        filtros.append(f"afftdn=nr={nr_db}:nf=-44:tn=1")

    return filtros


def construir_filtros_post_dsp(
    opciones: OpcionesProcesamiento,
    duracion: float = 0.0,
    en_vivo: bool = False,
) -> str:
    """
    Construye la cadena rápida de Fase 2 (Post-IA en tiempo real y exportación final):
    Anti-resonancia de sala + Expansor suave + Modelado tonal + Compresión sin bombeo.
    """
    filtros: list[str] = []

    # 1. Anti-eco / Anti-resonancia de sala ("quitar sonido hueco/cine")
    if opciones.quitar_eco:
        filtros.extend([
            "highpass=f=105:poles=2",
            "equalizer=f=220:t=q:w=1.1:g=-2.8",
            "equalizer=f=410:t=q:w=1.2:g=-1.6",
        ])

    # 2. Expansor / Puerta suave (sin cortar palabras ni chocar con normalizador)
    if opciones.aislar_voz_principal == "estricto":
        filtros.append(
            "agate=threshold=0.012:ratio=2.4:attack=15:release=280:range=0.16:knee=3.5"
        )
    elif opciones.aislar_voz_principal == "moderado":
        filtros.append(
            "agate=threshold=0.006:ratio=1.7:attack=20:release=340:range=0.32:knee=4.0"
        )
    elif opciones.quitar_eco:
        # Atenuación ultra sutil solo en silencios profundos (< -52 dB) para domar colas de reverberación
        filtros.append(
            "agate=threshold=0.0025:ratio=1.5:attack=25:release=360:range=0.45:knee=4.0"
        )

    # 3. Modelado tonal de la voz (EQ + De-Esser sin inflar graves cavernosos)
    if opciones.tono_voz == "claridad":
        if not opciones.quitar_eco:
            filtros.append("equalizer=f=230:t=q:w=1.2:g=-2.5")
        filtros.extend([
            "equalizer=f=2650:t=q:w=1.3:g=2.8",
            "equalizer=f=5800:t=q:w=1.3:g=1.6",
            "deesser=i=0.28:m=0.5:f=0.5:s=o",
        ])
    elif opciones.tono_voz == "locutor":
        filtros.append("equalizer=f=145:t=q:w=1.2:g=1.0")
        if not opciones.quitar_eco:
            filtros.append("equalizer=f=270:t=q:w=1.3:g=-2.5")
        filtros.extend([
            "equalizer=f=3200:t=q:w=1.4:g=2.4",
            "equalizer=f=8500:t=q:w=1.2:g=1.2",
            "deesser=i=0.30:m=0.5:f=0.5:s=o",
        ])

    # 4. Compresión vocal limpia y nivelación (sin speechnorm para evitar bombeo de volumen)
    if opciones.normalizar_lufs:
        makeup = "3.5dB" if en_vivo else "2.0dB"
        filtros.append(
            f"acompressor=threshold=-20dB:ratio=2.2:attack=15:release=220:makeup={makeup}:knee=4dB"
        )
        if en_vivo or (0.0 < duracion < 3.5):
            filtros.append("alimiter=limit=0.89:level=false")
        else:
            filtros.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    return ",".join(filtros) if filtros else "anull"


def construir_filtros_limpieza(opciones: OpcionesProcesamiento) -> list[str]:
    """Alias de compatibilidad para filtros previos de Fase 1."""
    return construir_filtros_pre_ia(opciones)


def construir_filtros_master(opciones: OpcionesProcesamiento, duracion: float = 0.0) -> list[str]:
    """Alias de compatibilidad que devuelve la lista de filtros de Fase 2."""
    cadena = construir_filtros_post_dsp(opciones, duracion=duracion, en_vivo=False)
    return [] if cadena == "anull" else cadena.split(",")


def construir_filtros_ffmpeg(opciones: OpcionesProcesamiento, duracion: float = 0.0) -> str:
    """Construye la cadena combinada completa para ffmpeg."""
    pre = construir_filtros_pre_ia(opciones)
    post = construir_filtros_master(opciones, duracion=duracion)
    todos = pre + post
    return ",".join(todos) if todos else "anull"


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
    """
    Orquesta el procesamiento de voz en 2 fases con caché de Fase IA:
    - Fase 1 (IA pesada: DeepFilterNet 3 + opcional Vocos): se cachea por sesión.
    - Fase 2 (DSP rápido: EQ, anti-eco, puerta suave, compresor): instantáneo en tiempo real.
    """

    TAMANO_SEGMENTO_SEG = 180

    def __init__(self):
        self.cancelar_evento = threading.Event()
        self._procesos_activos: list[subprocess.Popen] = []
        self._lock = threading.Lock()

        self._cache_dir = Path(tempfile.mkdtemp(prefix="voz_limpia_cache_"))
        self._cache_clave: tuple | None = None
        self._cache_es_completo: bool = False
        self._cache_orig_wav: Path | None = None
        self._cache_ia_wav: Path | None = None
        self._cache_duracion: float = 0.0

    def limpiar_cache(self) -> None:
        """Elimina los archivos cacheados de la sesión actual."""
        self._cache_clave = None
        self._cache_es_completo = False
        self._cache_orig_wav = None
        self._cache_ia_wav = None
        self._cache_duracion = 0.0
        if self._cache_dir.exists():
            shutil.rmtree(self._cache_dir, ignore_errors=True)

    def _asegurar_cache_dir(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _clave_stage1(
        self,
        archivo: Path,
        opciones: OpcionesProcesamiento,
        inicio_seg: float,
        duracion_seg: float | None,
    ) -> tuple:
        st = archivo.stat()
        aislar_en_fase1 = opciones.aislar_voz_principal if not opciones.usar_deepfilter else "df"
        return (
            str(archivo.resolve()),
            st.st_mtime_ns,
            st.st_size,
            round(inicio_seg, 2),
            round(duracion_seg, 2) if duracion_seg is not None else None,
            bool(opciones.usar_deepfilter),
            opciones.intensidad_ruido,
            bool(opciones.quitar_eco),
            opciones.reconstruir_voz,
            aislar_en_fase1,
        )

    def tiene_cache_ia_completo(self, archivo: Path | None, opciones: OpcionesProcesamiento) -> bool:
        """Indica si ya existe la Fase IA pre-generada para el archivo completo con estos parámetros."""
        if not archivo or not archivo.is_file() or not self._cache_es_completo:
            return False
        if not self._cache_ia_wav or not self._cache_ia_wav.is_file():
            return False
        return self._clave_stage1(archivo, opciones, 0.0, None) == self._cache_clave

    def obtener_base_ia_actual(self) -> Path | None:
        if self._cache_ia_wav and self._cache_ia_wav.is_file():
            return self._cache_ia_wav
        return None

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
            opciones.intensidad_ruido, "48"
        )
        cmd = [
            str(DEEPFILTER_BIN),
            "-D",  # Compensar retardo para alineación exacta A/B
            "-a", atten,
            "-o", str(dir_salida),
        ]

        # Post-filter suave: evita artefactos metálicos manteniendo limpieza de fondo
        if opciones.quitar_eco:
            cmd.extend(["--pf", "--pf-beta=0.025", "--min-db-thresh=-13"])

        return cmd

    def _ejecutar_ffmpeg_con_progreso(
        self,
        cmd: list[str],
        log_path: Path,
        duracion: float,
        base_p: float,
        rango_p: float,
        etiqueta: str,
        cb_progreso=None,
    ) -> tuple[bool, str]:
        """Ejecuta un comando ffmpeg reportando progreso por `out_time_ms`."""
        with open(log_path, "w", encoding="utf-8", errors="replace") as f_err:
            proc = subprocess.Popen(
                cmd,
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
                                p = min(base_p + rango_p, base_p + rango_p * min(1.0, seg_actual / duracion))
                                if cb_progreso:
                                    cb_progreso(f"{etiqueta} ({int(p * 100)}%)...", p)
                            except ValueError:
                                pass
                proc.wait()
            finally:
                with self._lock:
                    if proc in self._procesos_activos:
                        self._procesos_activos.remove(proc)

        if self.cancelar_evento.is_set():
            return False, "Proceso cancelado por el usuario."
        if proc.returncode != 0:
            err_txt = ""
            if log_path.is_file():
                lineas_err = log_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                err_txt = lineas_err[-1] if lineas_err else ""
            return False, err_txt
        return True, ""

    def _ejecutar_fase_ia(
        self,
        archivo_entrada: Path,
        opciones: OpcionesProcesamiento,
        workdir: Path,
        duracion: float,
        inicio_seg: float = 0.0,
        duracion_seg: float | None = None,
        ruta_orig_out: Path | None = None,
        ruta_ia_out: Path | None = None,
        cb_progreso=None,
    ) -> tuple[bool, Path | None, str]:
        """
        Ejecuta únicamente la Fase 1 (IA Base: Decodificación 48 kHz + DeepFilterNet 3 + Pre-IA + Vocos).
        El resultado queda en `ruta_ia_out` listo para aplicar cualquier Fase 2 DSP en tiempo real.
        """
        usar_reconstructor = opciones.reconstruir_voz in ("natural", "estudio", "rescate")
        usar_df = opciones.usar_deepfilter and DEEPFILTER_BIN.is_file()

        args_seek = ["-ss", f"{inicio_seg:.2f}"] if inicio_seg > 0.01 else []
        args_dur = ["-t", f"{duracion_seg:.2f}"] if duracion_seg is not None else []

        # Si se pidió un archivo original exacto del fragmento (para vista previa A/B alineada)
        if ruta_orig_out is not None:
            if cb_progreso:
                cb_progreso("Extrayendo fragmento de prueba a 48 kHz...", 0.08)
            cmd_ext = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                *args_seek,
                "-i", str(archivo_entrada),
                *args_dur,
                "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le",
                str(ruta_orig_out),
            ]
            if not self._ejecutar_cmd(cmd_ext) or not ruta_orig_out.is_file():
                if self.cancelar_evento.is_set():
                    return False, None, "Proceso cancelado por el usuario."
                return False, None, "No se pudo extraer el fragmento de audio."
            fuente_para_ia = ruta_orig_out
            args_seek_ia: list[str] = []
            args_dur_ia: list[str] = []
        else:
            fuente_para_ia = archivo_entrada
            args_seek_ia = args_seek
            args_dur_ia = args_dur

        if usar_df:
            if cb_progreso:
                cb_progreso("Preparando bloques de audio a 48 kHz...", 0.10)

            dir_segmentos_in = workdir / "seg_in"
            dir_segmentos_out = workdir / "seg_out"
            dir_segmentos_in.mkdir(parents=True, exist_ok=True)
            dir_segmentos_out.mkdir(parents=True, exist_ok=True)

            patron_seg = str(dir_segmentos_in / "seg_%04d.wav")
            cmd_split = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                *args_seek_ia,
                "-i", str(fuente_para_ia),
                *args_dur_ia,
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
            max_workers = min(4, max(1, (os.cpu_count() or 4) // 4), total_seg)

            def _procesar_segmento(seg_path: Path) -> bool:
                return self._ejecutar_cmd(base_cmd_df + [str(seg_path)])

            rango_df = 0.38 if usar_reconstructor else 0.56
            if cb_progreso:
                cb_progreso(
                    f"IA DeepFilterNet 3: limpiando voz (0/{total_seg} bloques)...",
                    0.12,
                )

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futuros = {pool.submit(_procesar_segmento, s): s for s in segmentos}
                for fut in as_completed(futuros):
                    if self.cancelar_evento.is_set():
                        break
                    if not fut.result():
                        return False, None, "Fallo durante el filtrado neuronal DeepFilterNet."
                    completados += 1
                    fraccion = 0.12 + rango_df * (completados / total_seg)
                    if cb_progreso:
                        cb_progreso(
                            f"IA DeepFilterNet 3: limpiando voz ({completados}/{total_seg} bloques)...",
                            fraccion,
                        )

            if self.cancelar_evento.is_set():
                return False, None, "Proceso cancelado por el usuario."

            segmentos_limpios = sorted(dir_segmentos_out.glob("seg_*.wav"))
            lista_concat = workdir / "concat.txt"
            lista_concat.write_text(
                "\n".join(f"file '{s}'" for s in segmentos_limpios),
                encoding="utf-8",
            )
            args_in_pre = ["-f", "concat", "-safe", "0", "-i", str(lista_concat)]
        else:
            args_in_pre = [*args_seek_ia, "-i", str(fuente_para_ia), *args_dur_ia]

        wav_pre_ia = workdir / "limpio_pre_ia.wav"
        filtros_pre = construir_filtros_pre_ia(opciones)
        af_pre = ",".join(filtros_pre) if filtros_pre else "anull"

        base_pre = 0.52 if usar_df else 0.12
        rango_pre = 0.10 if usar_df else 0.45
        cmd_pre = [
            "ffmpeg", "-y", "-hide_banner", "-nostats", "-progress", "pipe:1",
            *args_in_pre,
            "-vn", "-af", af_pre,
            "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le",
            str(wav_pre_ia),
        ]
        ok_pre, err_pre = self._ejecutar_ffmpeg_con_progreso(
            cmd_pre,
            workdir / "ffmpeg_pre.log",
            duracion,
            base_pre,
            rango_pre,
            "Acondicionando fase base",
            cb_progreso,
        )
        if not ok_pre or not wav_pre_ia.is_file():
            if self.cancelar_evento.is_set():
                return False, None, "Proceso cancelado por el usuario."
            return False, None, f"Error preparando base de audio. {err_pre}"

        destino_ia = ruta_ia_out or (workdir / "base_ia.wav")
        if usar_reconstructor:
            if cb_progreso:
                cb_progreso("IA Vocos 48 kHz: reconstruyendo armónicos sutiles...", 0.64)
            ok_rec, msg_rec = reconstruir_archivo_wav(
                wav_pre_ia,
                destino_ia,
                modo=opciones.reconstruir_voz,
                forzar_ulunas=(not usar_df),
                cb_progreso=cb_progreso,
                cancelar_evento=self.cancelar_evento,
            )
            if not ok_rec or not destino_ia.is_file():
                return False, None, msg_rec
        else:
            shutil.move(str(wav_pre_ia), str(destino_ia))

        return True, destino_ia, "Fase IA completada."

    def preparar_vista_previa(
        self,
        archivo_entrada: Path,
        opciones: OpcionesProcesamiento,
        inicio_seg: float = 0.0,
        duracion_seg: float = 12.0,
        cb_progreso=None,
    ) -> tuple[bool, Path | None, Path | None, bool, str]:
        """
        Genera una vista previa rápida (~12 s) cacheando la Fase IA para que el usuario
        pueda ajustar tono, anti-eco, puerta y compresor en tiempo real sin esperas.
        Devuelve (exito, ruta_orig_wav, ruta_ia_wav, es_completo, mensaje).
        """
        self.cancelar_evento.clear()
        if not archivo_entrada.is_file():
            return False, None, None, False, "El archivo de origen no existe."

        usar_reconstructor = opciones.reconstruir_voz in ("natural", "estudio", "rescate")
        asegurar_motores_ia(cb_estado=cb_progreso, incluir_reconstructor=usar_reconstructor)

        meta = obtener_metadatos_audio(archivo_entrada)
        dur_total = max(1.0, meta["duracion"])

        if dur_total <= duracion_seg + 1.0:
            inicio = 0.0
            dur_real: float | None = None
            dur_proc = dur_total
            es_completo = True
        else:
            inicio = max(0.0, min(float(inicio_seg), max(0.0, dur_total - duracion_seg)))
            dur_real = duracion_seg
            dur_proc = duracion_seg
            es_completo = False

        clave = self._clave_stage1(archivo_entrada, opciones, inicio, dur_real)
        if (
            clave == self._cache_clave
            and self._cache_ia_wav
            and self._cache_ia_wav.is_file()
            and (self._cache_orig_wav and self._cache_orig_wav.is_file())
        ):
            if cb_progreso:
                cb_progreso("Vista previa lista desde caché IA.", 1.0)
            return True, self._cache_orig_wav, self._cache_ia_wav, self._cache_es_completo, "Vista previa cargada desde caché."

        self._asegurar_cache_dir()
        workdir = Path(tempfile.mkdtemp(prefix="voz_limpia_prev_"))
        try:
            cache_orig = self._cache_dir / "preview_orig.wav"
            cache_ia = self._cache_dir / ("full_ia.wav" if es_completo else "preview_ia.wav")

            ok, _, msg = self._ejecutar_fase_ia(
                archivo_entrada,
                opciones,
                workdir,
                duracion=dur_proc,
                inicio_seg=inicio,
                duracion_seg=dur_real,
                ruta_orig_out=cache_orig,
                ruta_ia_out=cache_ia,
                cb_progreso=cb_progreso,
            )
            if not ok:
                return False, None, None, False, msg

            self._cache_clave = clave
            self._cache_es_completo = es_completo
            self._cache_orig_wav = cache_orig
            self._cache_ia_wav = cache_ia
            self._cache_duracion = dur_proc

            if cb_progreso:
                cb_progreso("¡Vista previa lista! Ajusta el sonido en tiempo real.", 1.0)
            return True, cache_orig, cache_ia, es_completo, f"Vista previa ({int(dur_proc)}s) lista."
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def procesar(
        self,
        archivo_entrada: Path,
        opciones: OpcionesProcesamiento,
        cb_progreso=None,
    ) -> tuple[bool, Path | None, str]:
        """
        Ejecuta el pipeline completo sobre `archivo_entrada`.
        Si la Fase IA del archivo completo ya está en caché, la reutiliza y solo corre
        el post-procesado DSP + codificación en ~1-2 segundos.
        """
        self.cancelar_evento.clear()

        if not archivo_entrada.is_file():
            return False, None, "El archivo de origen no existe."

        usar_reconstructor = opciones.reconstruir_voz in ("natural", "estudio", "rescate")
        asegurar_motores_ia(cb_estado=cb_progreso, incluir_reconstructor=usar_reconstructor)

        meta = obtener_metadatos_audio(archivo_entrada)
        duracion = max(1.0, meta["duracion"])

        ext = opciones.formato_salida.lower().lstrip(".")
        dir_destino = opciones.carpeta_destino or archivo_entrada.parent
        dir_destino.mkdir(parents=True, exist_ok=True)

        if opciones.reemplazar_original:
            ruta_final = archivo_entrada.with_suffix(f".{ext}")
        else:
            stem = archivo_entrada.stem
            stem_salida = stem if stem.endswith("_limpio") else f"{stem}_limpio"
            ruta_final = dir_destino / f"{stem_salida}.{ext}"
            if ruta_final.resolve() == archivo_entrada.resolve():
                ruta_final = dir_destino / f"{stem}_procesado.{ext}"

        workdir = Path(tempfile.mkdtemp(prefix="voz_limpia_work_"))
        try:
            self._asegurar_cache_dir()
            clave_full = self._clave_stage1(archivo_entrada, opciones, 0.0, None)
            cache_ia_full = self._cache_dir / "full_ia.wav"

            if (
                clave_full == self._cache_clave
                and self._cache_es_completo
                and self._cache_ia_wav
                and self._cache_ia_wav.is_file()
            ):
                if cb_progreso:
                    cb_progreso("Reutilizando Fase IA en caché · Aplicando ajustes finales...", 0.72)
                wav_base_ia = self._cache_ia_wav
            else:
                ok_ia, wav_base_ia, msg_ia = self._ejecutar_fase_ia(
                    archivo_entrada,
                    opciones,
                    workdir,
                    duracion=duracion,
                    inicio_seg=0.0,
                    duracion_seg=None,
                    ruta_orig_out=None,
                    ruta_ia_out=cache_ia_full,
                    cb_progreso=cb_progreso,
                )
                if not ok_ia or not wav_base_ia or not wav_base_ia.is_file():
                    return False, None, msg_ia

                self._cache_clave = clave_full
                self._cache_es_completo = True
                self._cache_orig_wav = None
                self._cache_ia_wav = cache_ia_full
                self._cache_duracion = duracion

            # Fase 2 rápida: EQ + Anti-eco + Puerta suave + Masterización (-16 LUFS) + Codificación
            archivo_temp_salida = workdir / f"salida_final.{ext}"
            af_post = construir_filtros_post_dsp(opciones, duracion=duracion, en_vivo=False)
            cmd_master = [
                "ffmpeg", "-y", "-hide_banner", "-nostats", "-progress", "pipe:1",
                "-i", str(wav_base_ia),
                "-vn", "-af", af_post,
                "-ar", "48000", "-ac", "1",
                *parametros_encoder(ext),
                str(archivo_temp_salida),
            ]
            ok_m, err_m = self._ejecutar_ffmpeg_con_progreso(
                cmd_master,
                workdir / "ffmpeg_master.log",
                duracion,
                0.78,
                0.20,
                "Masterizando y codificando",
                cb_progreso,
            )
            if not ok_m or not archivo_temp_salida.is_file():
                if self.cancelar_evento.is_set():
                    return False, None, "Proceso cancelado por el usuario."
                return False, None, f"Error en la masterización final. {err_m}"

            shutil.move(str(archivo_temp_salida), str(ruta_final))
            if opciones.reemplazar_original and ruta_final.resolve() != archivo_entrada.resolve():
                try:
                    archivo_entrada.unlink()
                except OSError:
                    pass
                self._cache_clave = None

            if cb_progreso:
                cb_progreso("¡Voz limpia y masterizada con éxito!", 1.0)

            return True, ruta_final, f"Guardado en {ruta_final.name}"

        finally:
            shutil.rmtree(workdir, ignore_errors=True)
