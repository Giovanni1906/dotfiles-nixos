"""Gestión del tema visual GTK3 (desde tema/tema.conf) y utilidades del sistema."""

import json
import os
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk

HOME = Path.home()
TEMA_CONF = HOME / "dotfiles/tema/tema.conf"
SONIDO_COMPLETADO = Path("/run/current-system/sw/share/sounds/freedesktop/stereo/complete.oga")

EXTENSIONES_AUDIO = {
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus",
    ".mp4", ".mkv", ".mov", ".webm", ".wma",
}

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
    "INFO": "#89dceb",
    "RADIO": "10",
    "BORDE": "2",
    "FUENTE": "JetBrainsMono Nerd Font",
    "OPACIDAD_MENU": "0.95",
}


def _sin_comentario(linea: str) -> str:
    entre_comillas = False
    for indice, caracter in enumerate(linea):
        if caracter == '"':
            entre_comillas = not entre_comillas
        elif caracter == "#" and not entre_comillas:
            return linea[:indice]
    return linea


def leer_tema() -> dict:
    """Lee la paleta activa de ~/dotfiles/tema/tema.conf con fallback seguro."""
    valores = dict(TEMA_BASE)
    if TEMA_CONF.is_file():
        try:
            for linea in TEMA_CONF.read_text(encoding="utf-8").splitlines():
                linea = _sin_comentario(linea).strip()
                if "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip().strip('"')
        except Exception:
            pass
    return valores


def hex_a_rgb_float(hex_color: str) -> tuple[float, float, float]:
    """Convierte '#rrggbb' a tupla (r, g, b) en rango 0.0 - 1.0 para Cairo."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        h = "3399cc"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r / 255.0, g / 255.0, b / 255.0)


def rgba(hex_color: str, alpha: str | float) -> str:
    """Convierte '#rrggbb' a cadena CSS rgba(r, g, b, alpha)."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        h = "3399cc"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def aplicar_css_tema(tema: dict) -> None:
    """Inyecta la hoja de estilos GTK3 adaptada al tema activo."""
    t = tema
    fondo = rgba(t["FONDO"], "0.98")
    superficie = rgba(t["SUPERFICIE"], "0.88")
    superficie_baja = rgba(t["SUPERFICIE"], "0.45")
    superficie_hover = t["SUPERFICIE"]
    acento_suave = rgba(t["ACENTO"], "0.26")
    exito_suave = rgba(t["EXITO"], "0.22")
    borde_suave = rgba(t["ACENTO"], "0.42")
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
    .badge-ia {{
        background-color: {acento_suave};
        border: 1px solid {t["ACENTO"]};
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 10px;
        font-weight: 700;
        color: {t["ACENTO"]};
    }}
    .tarjeta-panel {{
        background-color: {superficie_baja};
        border: 1px solid {borde_suave};
        border-radius: 9px;
        padding: 10px 12px;
    }}
    .caja-drop {{
        background-color: {superficie};
        border: 1px dashed {borde_suave};
        border-radius: 8px;
        padding: 10px 12px;
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
    button.chip-exito {{
        background-color: {exito_suave};
        border: 1px solid {t["EXITO"]};
    }}
    button.chip-exito label {{
        color: {t["EXITO"]};
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
    scale trough {{
        background-color: {superficie};
        border-radius: 6px;
        min-height: 6px;
    }}
    scale highlight {{
        background-color: {t["ACENTO"]};
        border-radius: 6px;
    }}
    scale slider {{
        background-color: {t["TEXTO"]};
        border: 2px solid {t["ACENTO"]};
        border-radius: 50%;
        min-width: 14px;
        min-height: 14px;
        margin: -5px 0;
    }}
    separator {{
        background-color: {borde_suave};
        min-height: 1px;
    }}
    """
    proveedor = Gtk.CssProvider()
    proveedor.load_from_data(css.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        proveedor,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def carpeta_xdg(nombre: str, por_defecto: str) -> Path:
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


def notificar(titulo: str, cuerpo: str = "", critico: bool = False, sonido: bool = False) -> None:
    cmd = ["notify-send", "-a", "Voz Limpia", "-i", "audio-input-microphone"]
    if critico:
        cmd += ["-u", "critical"]
    cmd += [titulo, cuerpo]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if sonido and SONIDO_COMPLETADO.is_file():
            subprocess.Popen(
                ["paplay", str(SONIDO_COMPLETADO)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


def leer_archivo_portapapeles() -> Path | None:
    """Devuelve un Path si el portapapeles contiene la ruta o URI de un archivo de audio."""
    try:
        res = subprocess.run(
            ["wl-paste", "--no-newline"],
            capture_output=True,
            text=True,
            timeout=1.0,
        )
        if res.returncode == 0 and res.stdout:
            texto = res.stdout.strip().splitlines()[0].strip()
            if texto.startswith("file://"):
                texto = unquote(urlparse(texto).path)
            p = Path(texto).expanduser()
            if p.is_file() and p.suffix.lower() in EXTENSIONES_AUDIO:
                return p.resolve()
    except Exception:
        pass
    return None


def buscar_audios_recientes(limite: int = 12) -> list[Path]:
    """Busca los archivos de audio más recientes en las carpetas del usuario."""
    carpetas = [
        (HOME, 1),
        (carpeta_xdg("DOWNLOAD", "Descargas"), 3),
        (carpeta_xdg("MUSIC", "Música"), 3),
        (carpeta_xdg("DOCUMENTS", "Documentos"), 3),
        (HOME / "Grabaciones", 3),
    ]
    encontrados: dict[Path, float] = {}
    for base, max_depth in carpetas:
        if not base.is_dir():
            continue
        try:
            for raiz, dirs, archivos in os.walk(base):
                profundidad = len(Path(raiz).relative_to(base).parts)
                if profundidad >= max_depth:
                    dirs[:] = []
                # Ignorar carpetas ocultas o de entorno
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__")
                ]
                for nombre in archivos:
                    if nombre.startswith("."):
                        continue
                    ruta = Path(raiz) / nombre
                    if ruta.suffix.lower() in EXTENSIONES_AUDIO:
                        try:
                            encontrados[ruta.resolve()] = ruta.stat().st_mtime
                        except OSError:
                            pass
        except Exception:
            pass

    ordenados = sorted(encontrados.items(), key=lambda x: x[1], reverse=True)
    return [ruta for ruta, _ in ordenados[:limite]]


def obtener_metadatos_audio(archivo: Path) -> dict:
    """Extrae duración, sample_rate, canales, códec y tamaño mediante ffprobe."""
    info = {
        "duracion": 0.0,
        "sample_rate": 48000,
        "canales": 2,
        "codec": archivo.suffix.lstrip(".").upper(),
        "tamano_bytes": archivo.stat().st_size if archivo.is_file() else 0,
    }
    try:
        res = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,sample_rate,channels:format=duration",
                "-of", "json",
                str(archivo),
            ],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if res.returncode == 0 and res.stdout:
            datos = json.loads(res.stdout)
            fmt = datos.get("format", {})
            if "duration" in fmt:
                info["duracion"] = float(fmt["duration"])
            streams = datos.get("streams", [])
            if streams:
                st = streams[0]
                if "sample_rate" in st:
                    info["sample_rate"] = int(st["sample_rate"])
                if "channels" in st:
                    info["canales"] = int(st["channels"])
                if "codec_name" in st:
                    info["codec"] = st["codec_name"].upper()
    except Exception:
        pass
    return info


def formatear_tamano(num_bytes: int | float) -> str:
    valor = float(num_bytes)
    for unidad in ("B", "KB", "MB", "GB"):
        if valor < 1024.0:
            return f"{valor:.1f} {unidad}"
        valor /= 1024.0
    return f"{valor:.1f} TB"


def formatear_tiempo(segundos: float) -> str:
    if segundos <= 0:
        return "00:00"
    m, s = divmod(int(segundos), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
