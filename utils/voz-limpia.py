#!/usr/bin/env python3
# Utilidad gráfica de limpieza neuronal de voz, aislamiento de hablante principal y comparador A/B.
# Se abre o cierra con SUPER + A (utils/voz-limpia.sh) y toma la paleta activa de tema/tema.conf.

from pathlib import Path
import signal
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib

# Permitir importación del paquete modular utils/voz_limpia
sys.path.insert(0, str(Path(__file__).resolve().parent))

from voz_limpia.ventana import VozLimpiaWindow


def main():
    GLib.set_prgname("voz-limpia-util")
    GLib.set_application_name("Voz Limpia")
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    archivo_arg = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else None
    app = VozLimpiaWindow(archivo_inicial=archivo_arg)
    app.ejecutar()


if __name__ == "__main__":
    main()
