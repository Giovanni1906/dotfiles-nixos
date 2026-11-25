"""Motor neuronal de reconstrucción y súper-resolución de voz (LavaSR: UL-UNAS + Vocos 48 kHz ONNX)."""

import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import urllib.request
import wave

try:
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view
    import onnxruntime as ort
    from scipy import signal

    ORT_DISPONIBLE = True
except ImportError:
    ORT_DISPONIBLE = False


HOME = Path.home()
BASE_DATOS_IA = HOME / ".local/share/dotfiles/voz-limpia"
LAVASR_DIR = BASE_DATOS_IA / "models/lavasr"
ORT_ENV_PYTHON = BASE_DATOS_IA / "ort-env/bin/python3"

BASE_URL_LAVASR = "https://github.com/Topping1/LavaSR-ONNX/releases/download/Alpha-v0.1"
ARCHIVOS_LAVASR = (
    "enhancer_backbone.onnx",
    "enhancer_backbone.onnx.data",
    "enhancer_spec_head.onnx",
    "enhancer_spec_head.onnx.data",
    "denoiser_core_legacy_fixed63.onnx",
)

MODOS_RECONSTRUCCION = [
    ("off", "Desactivada · Voz 100% original (Recomendado)"),
    ("natural", "Brillo Sutil · Claridad >5.2 kHz (Mezcla 35%, timbre intacto)"),
    ("estudio", "Nitidez Media · Micrófono opaco >4.0 kHz (Mezcla 55%)"),
    ("rescate", "Rescate Bulla · Audio apagado >3.2 kHz (Mezcla 65%)"),
]

# Parámetros fijos por modo: (frecuencia_corte_hz, usar_ulunas_si_sin_df, mezcla_wet)
CONFIG_MODOS = {
    "natural": (5200.0, False, 0.35),
    "estudio": (4000.0, False, 0.55),
    "rescate": (3200.0, True, 0.65),
}

# Constantes espectrales Mel Slaney compatibles con Vocos / torchaudio
_F_SP = 200.0 / 3.0
_MIN_LOG_HZ = 1000.0
_MIN_LOG_MEL = _MIN_LOG_HZ / _F_SP
_LOGSTEP = math.log(6.4) / 27.0


def motores_reconstruccion_listos() -> bool:
    """Verifica si todos los modelos ONNX de LavaSR están descargados."""
    return all((LAVASR_DIR / nombre).is_file() for nombre in ARCHIVOS_LAVASR)


def asegurar_modelos_reconstruccion(cb_estado=None) -> bool:
    """Descarga los modelos ONNX de reconstrucción de voz (LavaSR) si faltan."""
    LAVASR_DIR.mkdir(parents=True, exist_ok=True)
    try:
        faltantes = [n for n in ARCHIVOS_LAVASR if not (LAVASR_DIR / n).is_file()]
        if not faltantes:
            return True
        for idx, nombre in enumerate(faltantes, start=1):
            destino = LAVASR_DIR / nombre
            if cb_estado:
                cb_estado(
                    f"Descargando reconstructor neuronal Vocos ({idx}/{len(faltantes)})...",
                    0.06 + 0.04 * (idx / len(faltantes)),
                )
            tmp = destino.with_suffix(destino.suffix + ".tmp")
            urllib.request.urlretrieve(f"{BASE_URL_LAVASR}/{nombre}", str(tmp))
            tmp.replace(destino)
        return True
    except Exception:
        return False


def _leer_wav_mono_float32(ruta: Path) -> tuple["np.ndarray", int]:
    """Lee un WAV PCM de 16 bits o 32 bits y lo devuelve normalizado a [-1.0, 1.0] en float32."""
    with wave.open(str(ruta), "rb") as wf:
        canales = wf.getnchannels()
        ancho = wf.getsampwidth()
        sr = wf.getframerate()
        crudo = wf.readframes(wf.getnframes())

    if ancho == 2:
        muestras = np.frombuffer(crudo, dtype=np.int16).astype(np.float32) / 32768.0
    elif ancho == 4:
        muestras = np.frombuffer(crudo, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Formato WAV no soportado (ancho de muestra: {ancho} bytes).")

    if canales > 1:
        muestras = muestras.reshape(-1, canales).mean(axis=1)
    return muestras.astype(np.float32, copy=False), int(sr)


def _guardar_wav_mono_16bit(ruta: Path, muestras: "np.ndarray", sr: int = 48000) -> None:
    """Guarda un array float32 mono en un archivo WAV PCM de 16 bits."""
    recortado = np.clip(muestras, -1.0, 1.0)
    pcm = (recortado * 32767.0).astype(np.int16)
    with wave.open(str(ruta), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def _resample_1d(x: "np.ndarray", sr_in: int, sr_out: int) -> "np.ndarray":
    if sr_in == sr_out:
        return x.astype(np.float32, copy=False)
    g = math.gcd(sr_in, sr_out)
    return signal.resample_poly(x, sr_out // g, sr_in // g).astype(np.float32)


def _hann_periodic(win_len: int) -> "np.ndarray":
    return np.hanning(win_len + 1)[:-1].astype(np.float32)


def _stft_same_reflect(x: "np.ndarray", n_fft: int, hop_length: int) -> "np.ndarray":
    pad = (n_fft - hop_length) // 2
    xpad = np.pad(x, (pad, pad), mode="reflect")
    if xpad.shape[0] < n_fft:
        xpad = np.pad(xpad, (0, n_fft - xpad.shape[0]))
    frames = sliding_window_view(xpad, n_fft)[::hop_length]
    frames = frames * _hann_periodic(n_fft)[None, :]
    return np.fft.rfft(frames, n=n_fft, axis=1).T.astype(np.complex64)


def _istft_same(spec: "np.ndarray", n_fft: int, hop_length: int, target_len: int) -> "np.ndarray":
    window = _hann_periodic(n_fft)
    pad = (n_fft - hop_length) // 2
    ifft = np.fft.irfft(spec, n=n_fft, axis=0).astype(np.float32)[:n_fft, :]
    ifft *= window[:, None]

    num_frames = ifft.shape[1]
    out_size = (num_frames - 1) * hop_length + n_fft
    y = np.zeros(out_size, dtype=np.float32)
    wenv = np.zeros(out_size, dtype=np.float32)
    win_sq = window ** 2
    for t in range(num_frames):
        ini = t * hop_length
        y[ini:ini + n_fft] += ifft[:, t]
        wenv[ini:ini + n_fft] += win_sq

    y = y[pad:-pad]
    wenv = wenv[pad:-pad]
    y = y / np.clip(wenv, 1e-8, None)

    if y.shape[0] < target_len:
        return np.pad(y, (0, target_len - y.shape[0])).astype(np.float32)
    return y[:target_len].astype(np.float32)


def _hz_to_mel_slaney(f: "np.ndarray") -> "np.ndarray":
    f = np.asanyarray(f, dtype=np.float32)
    m = f / _F_SP
    log_t = f >= _MIN_LOG_HZ
    if np.any(log_t):
        m = m.copy()
        m[log_t] = _MIN_LOG_MEL + np.log(f[log_t] / _MIN_LOG_HZ) / _LOGSTEP
    return m


def _mel_to_hz_slaney(m: "np.ndarray") -> "np.ndarray":
    m = np.asanyarray(m, dtype=np.float32)
    f = _F_SP * m
    log_t = m >= _MIN_LOG_MEL
    if np.any(log_t):
        f = f.copy()
        f[log_t] = _MIN_LOG_HZ * np.exp(_LOGSTEP * (m[log_t] - _MIN_LOG_MEL))
    return f


def _construir_banco_mel(sr: int = 44100, n_fft: int = 2048, n_mels: int = 80, fmin: float = 0.0, fmax: float = 8000.0) -> "np.ndarray":
    n_freqs = n_fft // 2 + 1
    fftfreqs = np.linspace(0.0, sr / 2.0, n_freqs, dtype=np.float32)
    m_min = _hz_to_mel_slaney(np.array([fmin], dtype=np.float32))[0]
    m_max = _hz_to_mel_slaney(np.array([fmax], dtype=np.float32))[0]
    m_pts = np.linspace(m_min, m_max, n_mels + 2, dtype=np.float32)
    f_pts = _mel_to_hz_slaney(m_pts)
    fdiff = np.diff(f_pts)
    ramps = f_pts[:, None] - fftfreqs[None, :]

    fb = np.zeros((n_mels, n_freqs), dtype=np.float32)
    for i in range(n_mels):
        lower = -ramps[i] / max(fdiff[i], 1e-12)
        upper = ramps[i + 2] / max(fdiff[i + 1], 1e-12)
        fb[i] = np.maximum(0.0, np.minimum(lower, upper))

    enorm = 2.0 / np.maximum(f_pts[2:n_mels + 2] - f_pts[:n_mels], 1e-12)
    fb *= enorm[:, None]
    return fb.astype(np.float32)


def _cruce_linkwitz_riley(reconstruida: "np.ndarray", original: "np.ndarray", sr: int = 48000, cutoff_hz: float = 2800.0, transicion_hz: float = 420.0) -> "np.ndarray":
    """Combina los graves/medios naturales del audio limpio con los armónicos reconstruidos por Vocos."""
    spec_rec = np.fft.rfft(reconstruida)
    spec_orig = np.fft.rfft(original)
    n_bins = spec_rec.shape[-1]
    nyquist = sr / 2.0
    cutoff_bin = int((cutoff_hz / nyquist) * n_bins)
    trans_bins = max(8, int((transicion_hz / nyquist) * n_bins))
    mitad = trans_bins // 2

    inicio = max(0, cutoff_bin - mitad)
    fin = min(n_bins, cutoff_bin + mitad)

    mascara = np.ones(n_bins, dtype=np.float32)
    mascara[:inicio] = 0.0
    if fin > inicio:
        t = np.linspace(0.0, 1.0, num=fin - inicio, dtype=np.float32)
        mascara[inicio:fin] = (3.0 * t**2 - 2.0 * t**3).astype(np.float32)
    mascara[fin:] = 1.0

    spec_final = spec_orig + (spec_rec - spec_orig) * mascara.astype(np.complex64)
    return np.fft.irfft(spec_final, n=len(reconstruida)).astype(np.float32)


class MotorLavaSR:
    """Ejecutor ONNX modular por bloques para UL-UNAS (16 kHz) y Vocos BWE (48 kHz)."""

    def __init__(self, num_hilos: int | None = None):
        hilos = num_hilos or min(8, max(2, (os.cpu_count() or 4) // 2))

        so_enh = ort.SessionOptions()
        so_enh.intra_op_num_threads = hilos
        so_enh.inter_op_num_threads = 1
        so_enh.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.backbone = ort.InferenceSession(
            str(LAVASR_DIR / "enhancer_backbone.onnx"),
            sess_options=so_enh,
            providers=["CPUExecutionProvider"],
        )
        self.spec_head = ort.InferenceSession(
            str(LAVASR_DIR / "enhancer_spec_head.onnx"),
            sess_options=so_enh,
            providers=["CPUExecutionProvider"],
        )
        self.bb_in = self.backbone.get_inputs()[0].name
        self.bb_out = self.backbone.get_outputs()[0].name
        self.sh_in = self.spec_head.get_inputs()[0].name
        self.sh_outs = [o.name for o in self.spec_head.get_outputs()[:2]]
        self.mel_fb = _construir_banco_mel()
        self._denoiser = None

    def _cargar_denoiser(self):
        if self._denoiser is not None:
            return self._denoiser
        so_den = ort.SessionOptions()
        so_den.intra_op_num_threads = min(6, max(2, (os.cpu_count() or 4) // 2))
        so_den.inter_op_num_threads = 1
        so_den.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        self._denoiser = ort.InferenceSession(
            str(LAVASR_DIR / "denoiser_core_legacy_fixed63.onnx"),
            sess_options=so_den,
            providers=["CPUExecutionProvider"],
        )
        return self._denoiser

    def _aplicar_ulunas_16k(self, wav_16k: "np.ndarray", cancelar_evento=None) -> "np.ndarray":
        """Limpia residuos difíciles en la banda 0-8 kHz usando UL-UNAS ONNX."""
        n_fft, hop = 512, 256
        pad = n_fft // 2
        xpad = np.pad(wav_16k, (pad, pad), mode="reflect")
        if xpad.shape[0] < n_fft:
            xpad = np.pad(xpad, (0, n_fft - xpad.shape[0]))
        frames = sliding_window_view(xpad, n_fft)[::hop] * _hann_periodic(n_fft)[None, :]
        spec = np.fft.rfft(frames, n=n_fft, axis=1).T.astype(np.complex64)  # [F, T]
        spec_ri = np.transpose(np.stack([spec.real, spec.imag], axis=0), (0, 2, 1))[None, ...].astype(np.float32)

        sess = self._cargar_denoiser()
        in_name = sess.get_inputs()[0].name
        out_name = sess.get_outputs()[0].name

        _, _, t_total, f_bins = spec_ri.shape
        l_chunk, h_chunk = 63, 21
        w = signal.windows.hann(l_chunk, sym=True).astype(np.float32)
        w = np.clip(w ** 2, 1e-4, None).reshape(1, 1, l_chunk, 1)

        if t_total <= l_chunk:
            bloque = np.pad(spec_ri, ((0, 0), (0, 0), (0, l_chunk - t_total), (0, 0)))
            spec_enh_ri = sess.run([out_name], {in_name: bloque})[0][:, :, :t_total, :]
        else:
            inicios = list(range(0, max(1, t_total - l_chunk + 1), h_chunk))
            if inicios[-1] != t_total - l_chunk:
                inicios.append(t_total - l_chunk)
            acc = np.zeros((1, 2, t_total, f_bins), dtype=np.float32)
            wacc = np.zeros((1, 1, t_total, 1), dtype=np.float32)
            for ini in inicios:
                if cancelar_evento and cancelar_evento.is_set():
                    return wav_16k
                fin = ini + l_chunk
                out_b = sess.run([out_name], {in_name: spec_ri[:, :, ini:fin, :]})[0]
                acc[:, :, ini:fin, :] += out_b * w
                wacc[:, :, ini:fin, :] += w
            spec_enh_ri = acc / np.clip(wacc, 1e-6, None)

        spec_enh = spec_enh_ri[0, 0].T + 1j * spec_enh_ri[0, 1].T  # [F, T]
        window = _hann_periodic(n_fft)
        ifft = np.fft.irfft(spec_enh, n=n_fft, axis=0).astype(np.float32)[:n_fft, :] * window[:, None]
        n_frames = ifft.shape[1]
        out_sz = (n_frames - 1) * hop + n_fft
        raw = np.zeros(out_sz, dtype=np.float32)
        wenv = np.zeros(out_sz, dtype=np.float32)
        win_sq = window ** 2
        for t in range(n_frames):
            st = t * hop
            raw[st:st + n_fft] += ifft[:, t]
            wenv[st:st + n_fft] += win_sq
        raw = raw[pad:-pad] / np.clip(wenv[pad:-pad], 1e-8, None)
        if raw.shape[0] < wav_16k.shape[0]:
            return np.pad(raw, (0, wav_16k.shape[0] - raw.shape[0])).astype(np.float32)
        return raw[:wav_16k.shape[0]].astype(np.float32)

    def _reconstruir_bloque_48k(
        self,
        bloque_48k: "np.ndarray",
        gain_norm: float,
        cutoff_hz: float,
        wet_mix: float = 0.50,
    ) -> "np.ndarray":
        x_norm = bloque_48k * gain_norm
        spec_stft = _stft_same_reflect(x_norm, n_fft=2048, hop_length=512)
        mel = self.mel_fb @ np.abs(spec_stft).astype(np.float32)
        mel_log = np.log(np.clip(mel, 1e-5, None)).astype(np.float32)[None, :, :]

        hidden = self.backbone.run([self.bb_out], {self.bb_in: mel_log})[0]
        real, imag = self.spec_head.run(self.sh_outs, {self.sh_in: hidden.astype(np.float32)})
        spec_pred = real[0].astype(np.float32) + 1j * imag[0].astype(np.float32)

        # Mezcla espectral preservando la fase original donde el micrófono ya tiene señal,
        # evitando voz robótica o cancelación de fase en los medios/agudos vocales.
        n_bins = spec_stft.shape[0]
        freqs = np.linspace(0.0, 24000.0, n_bins, dtype=np.float32)[:, None]
        trans_hz = 700.0
        t = np.clip((freqs - (cutoff_hz - trans_hz * 0.5)) / trans_hz, 0.0, 1.0)
        mascara = (3.0 * t**2 - 2.0 * t**3) * float(max(0.0, min(1.0, wet_mix)))

        mag_orig = np.abs(spec_stft)
        mag_pred = np.abs(spec_pred)
        mag_objetivo = (1.0 - mascara) * mag_orig + mascara * np.maximum(mag_orig, mag_pred)
        s_fase_orig = (spec_stft / np.maximum(mag_orig, 1e-8)) * mag_objetivo

        # Solo delegar la fase a Vocos cuando la banda original está realmente muda/apagada
        umbral_vacio = np.maximum(0.18 * mag_pred, 1e-4)
        peso_pred = np.exp(-((mag_orig / umbral_vacio) ** 2)) * mascara
        spec_final = (1.0 - peso_pred) * s_fase_orig + peso_pred * spec_pred

        y_final = _istft_same(spec_final, n_fft=2048, hop_length=512, target_len=len(bloque_48k))
        return (y_final / gain_norm).astype(np.float32)

    def procesar_audio(
        self,
        wav: "np.ndarray",
        sr: int,
        modo: str = "estudio",
        forzar_ulunas: bool = False,
        cb_progreso=None,
        cancelar_evento=None,
    ) -> "np.ndarray":
        cutoff_hz, ulunas_modo, wet_mix = CONFIG_MODOS.get(modo, (4000.0, False, 0.55))
        # UL-UNAS (16 kHz) solo se aplica si DeepFilterNet 3 no está activo (forzar_ulunas),
        # evitando apilar dos redes de ruido que destruyen la fase y vuelven robótica la voz.
        usar_ulunas = bool(forzar_ulunas)

        if sr != 48000:
            wav_48k = _resample_1d(wav, sr, 48000)
        else:
            wav_48k = wav.astype(np.float32, copy=False)

        if len(wav_48k) < 4096:
            return wav_48k

        if usar_ulunas:
            if cb_progreso:
                cb_progreso("IA UL-UNAS: limpiando residuos en banda vocal...", 0.60)
            wav_16k = _resample_1d(wav_48k, 48000, 16000)
            wav_16k = self._aplicar_ulunas_16k(wav_16k, cancelar_evento=cancelar_evento)
            if cancelar_evento and cancelar_evento.is_set():
                return wav_48k
            wav_48k_limpio = _resample_1d(wav_16k, 16000, 48000)
            # Ajustar longitud exacta al muestreo original 48 kHz
            if len(wav_48k_limpio) < len(wav_48k):
                wav_48k = np.pad(wav_48k_limpio, (0, len(wav_48k) - len(wav_48k_limpio)))
            else:
                wav_48k = wav_48k_limpio[:len(wav_48k)]

        pico_global = float(np.max(np.abs(wav_48k)))
        if pico_global < 1e-4:
            return wav_48k
        gain_norm = min(25.0, 0.78 / pico_global)

        # Procesamiento por bloques de 20 s con solapamiento de 0.8 s para bajo consumo de RAM
        tam_bloque = 20 * 48000
        solape = int(0.8 * 48000)
        n_total = len(wav_48k)

        if n_total <= tam_bloque:
            if cb_progreso:
                cb_progreso("IA Vocos 48 kHz: reconstruyendo armónicos y nitidez...", 0.68)
            return self._reconstruir_bloque_48k(wav_48k, gain_norm, cutoff_hz, wet_mix)

        paso = tam_bloque - solape
        inicios = list(range(0, n_total - solape, paso))
        if inicios[-1] + tam_bloque < n_total:
            inicios.append(max(0, n_total - tam_bloque))

        salida = np.zeros(n_total, dtype=np.float32)
        pesos = np.zeros(n_total, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, solape, dtype=np.float32)
        fade_out = 1.0 - fade_in

        total_b = len(inicios)
        for idx, ini in enumerate(inicios):
            if cancelar_evento and cancelar_evento.is_set():
                return wav_48k
            fin = min(n_total, ini + tam_bloque)
            bloque = wav_48k[ini:fin]
            rec = self._reconstruir_bloque_48k(bloque, gain_norm, cutoff_hz, wet_mix)

            w = np.ones(len(rec), dtype=np.float32)
            if idx > 0 and len(rec) >= solape:
                w[:solape] = fade_in
            if idx < total_b - 1 and len(rec) >= solape:
                w[-solape:] = fade_out

            salida[ini:fin] += rec * w
            pesos[ini:fin] += w

            if cb_progreso:
                frac = 0.62 + 0.14 * ((idx + 1) / total_b)
                cb_progreso(
                    f"IA Vocos 48 kHz: reconstruyendo armónicos ({idx + 1}/{total_b})...",
                    frac,
                )

        return (salida / np.clip(pesos, 1e-6, None)).astype(np.float32)


def reconstruir_archivo_wav(
    ruta_entrada: Path,
    ruta_salida: Path,
    modo: str = "estudio",
    forzar_ulunas: bool = False,
    cb_progreso=None,
    cancelar_evento: threading.Event | None = None,
) -> tuple[bool, str]:
    """
    Aplica reconstrucción neuronal de voz (LavaSR) sobre un WAV mono 48 kHz.
    Si onnxruntime no está en el Python activo, delega automáticamente al entorno `ort-env`.
    """
    if modo == "off":
        return True, "Reconstrucción omitida."

    if not asegurar_modelos_reconstruccion(cb_estado=cb_progreso):
        return False, "No se pudieron descargar los modelos ONNX de reconstrucción."

    if ORT_DISPONIBLE:
        try:
            wav, sr = _leer_wav_mono_float32(ruta_entrada)
            motor = MotorLavaSR()
            salida = motor.procesar_audio(
                wav,
                sr,
                modo=modo,
                forzar_ulunas=forzar_ulunas,
                cb_progreso=cb_progreso,
                cancelar_evento=cancelar_evento,
            )
            if cancelar_evento and cancelar_evento.is_set():
                return False, "Proceso cancelado por el usuario."
            _guardar_wav_mono_16bit(ruta_salida, salida, sr=48000)
            return True, "Reconstrucción neuronal completada."
        except Exception as err:
            return False, f"Error en reconstrucción neuronal: {err}"

    # Fallback automático si aún no se ejecutó nix-switch: invocar ort-env aislado
    if not ORT_ENV_PYTHON.is_file():
        return False, "Falta onnxruntime en el entorno (ejecuta nix-switch o crea ort-env)."

    cmd = [
        str(ORT_ENV_PYTHON),
        str(Path(__file__).resolve()),
        str(ruta_entrada),
        str(ruta_salida),
        "--modo",
        modo,
    ]
    if forzar_ulunas:
        cmd.append("--ulunas")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        if proc.stdout:
            for linea in proc.stdout:
                if cancelar_evento and cancelar_evento.is_set():
                    proc.terminate()
                    proc.wait(timeout=3)
                    return False, "Proceso cancelado por el usuario."
                linea = linea.strip()
                if linea.startswith("PROG|") and cb_progreso:
                    partes = linea.split("|", 2)
                    if len(partes) == 3:
                        try:
                            cb_progreso(partes[2], float(partes[1]))
                        except ValueError:
                            pass
        _, err_txt = proc.communicate()
        if cancelar_evento and cancelar_evento.is_set():
            return False, "Proceso cancelado por el usuario."
        if proc.returncode != 0 or not ruta_salida.is_file():
            detalle = err_txt.strip().splitlines()[-1] if err_txt and err_txt.strip() else ""
            return False, f"Fallo en el subproceso de reconstrucción. {detalle}"
        return True, "Reconstrucción neuronal completada."
    except Exception as err:
        try:
            proc.terminate()
        except Exception:
            pass
        return False, f"Error lanzando reconstrucción IA: {err}"


def _cli_main():
    import argparse

    parser = argparse.ArgumentParser(description="Worker CLI para reconstrucción LavaSR ONNX.")
    parser.add_argument("entrada", type=Path)
    parser.add_argument("salida", type=Path)
    parser.add_argument("--modo", default="estudio", choices=["natural", "estudio", "rescate"])
    parser.add_argument("--ulunas", action="store_true")
    args = parser.parse_args()

    if not ORT_DISPONIBLE:
        sys.stderr.write("onnxruntime/scipy/numpy no disponibles en este intérprete.\n")
        sys.exit(2)

    def _cb(msg: str, frac: float):
        print(f"PROG|{frac:.3f}|{msg}", flush=True)

    ok, msg = reconstruir_archivo_wav(
        args.entrada,
        args.salida,
        modo=args.modo,
        forzar_ulunas=args.ulunas,
        cb_progreso=_cb,
    )
    if not ok:
        sys.stderr.write(msg + "\n")
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
