#!/usr/bin/env bash
# =============================================================================
# IMPRESIÓN: Menú interactivo en Rofi para plotter e impresoras estándar
# =============================================================================
# Atajo: SUPER + P  |  Comando: imprimir [archivo]
# Permite seleccionar impresora, tamaño de papel/rollo, modo de calidad/ahorro,
# color/escala de grises, escala/redimensión y número de copias.

set -uo pipefail

# --- CONFIGURACIÓN Y ESTADO ---
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/impresion"
mkdir -p "$CACHE_DIR"

SONIDO="/run/current-system/sw/share/sounds/freedesktop/stereo/complete.oga"

notificar() {
    local titulo="$1" mensaje="$2" urgencia="${3:-normal}"
    notify-send -u "$urgencia" -a "Impresión" -i "printer" "$titulo" "$mensaje"
    if [ -f "$SONIDO" ] && command -v paplay >/dev/null 2>&1; then
        paplay "$SONIDO" 2>/dev/null &
    fi
}

error_notificar() {
    notify-send -u critical -a "Impresión" -i "dialog-error" "Error de impresión" "$1"
    exit 1
}

# --- DETECCIÓN DE IMPRESORAS ---
obtener_impresoras() {
    local printers
    printers=$(lpstat -e 2>/dev/null || lpstat -p 2>/dev/null | awk '{print $2}')
    if [ -z "$printers" ]; then
        # Intento con lpstat -a
        printers=$(lpstat -a 2>/dev/null | awk '{print $1}')
    fi
    printf '%s\n' "$printers" | sed '/^$/d' | sort -u
}

obtener_predeterminada() {
    local def
    def=$(lpstat -d 2>/dev/null | awk -F': ' '{print $2}' | tr -d ' ')
    if [ -z "$def" ]; then
        def=$(obtener_impresoras | head -n1)
    fi
    printf '%s' "$def"
}

# Selector de archivo gráfico nativo GTK si se pide examinar
examinar_archivo_gtk() {
    local cal_bin python_gtk
    cal_bin=$(command -v calendario 2>/dev/null || command -v multimedia 2>/dev/null || true)
    if [[ -n "$cal_bin" && -f "$cal_bin" ]]; then
        eval "$(grep '^export ' "$cal_bin")"
        python_gtk=$(awk '/^exec / { print $2 }' "$cal_bin")
        if [[ -n "$python_gtk" && -x "$python_gtk" ]]; then
            "$python_gtk" -c '
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

dialog = Gtk.FileChooserDialog(
    title="Seleccionar archivo para imprimir",
    action=Gtk.FileChooserAction.OPEN,
)
dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

filtro_docs = Gtk.FileFilter()
filtro_docs.set_name("Documentos e Imágenes (PDF, PNG, JPG, TIFF)")
for ext in ["*.pdf", "*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.ps", "*.txt"]:
    filtro_docs.add_pattern(ext)
dialog.add_filter(filtro_docs)

todos = Gtk.FileFilter()
todos.set_name("Todos los archivos")
todos.add_pattern("*")
dialog.add_filter(todos)

res = dialog.run()
if res == Gtk.ResponseType.OK:
    print(dialog.get_filename())
dialog.destroy()
'
            return
        fi
    fi

    # Fallback con zenity si estuviera instalado
    if command -v zenity >/dev/null 2>&1; then
        zenity --file-selection --title="Seleccionar archivo para imprimir" 2>/dev/null || true
    fi
}

# --- GESTOR DE COLA DE TRABAJOS ---
ver_cola_impresion() {
    while true; do
        local trabajos filas
        trabajos=$(lpstat -o 2>/dev/null || true)
        if [ -z "$trabajos" ]; then
            rofi -e "No hay trabajos pendientes en la cola de impresión." \
                -theme-str "window { width: 35%; }"
            return
        fi

        filas="<b>❌ Cancelar TODOS los trabajos</b>\0icon\x1fedit-delete\n"
        while IFS= read -r linea; do
            [ -z "$linea" ] && continue
            local id_job
            id_job=$(awk '{print $1}' <<< "$linea")
            filas+="<b>$id_job</b>   <span alpha='70%'>$linea</span>\0icon\x1fprinter\n"
        done <<< "$trabajos"

        local sel
        sel=$(printf '%b' "$filas" | rofi -dmenu -i -p "Cola de Impresión" -markup-rows \
            -mesg "Selecciona un trabajo para cancelarlo" \
            -theme-str "window { width: 50%; }" \
            -theme-str "listview { lines: 8; }")

        [ -z "$sel" ] && return

        if [[ "$sel" =~ "Cancelar TODOS" ]]; then
            cancel -a 2>/dev/null || true
            notificar "Cola limpiada" "Se han cancelado todos los trabajos activos."
            return
        else
            local id_cancelar
            id_cancelar=$(awk '{print $1}' <<< "$sel" | sed -E 's/<[^>]+>//g')
            if [ -n "$id_cancelar" ]; then
                cancel "$id_cancelar" 2>/dev/null || true
                notificar "Trabajo cancelado" "Se canceló $id_cancelar."
            fi
        fi
    done
}

# --- SELECCIÓN INTERACTIVA DE ARCHIVO ---
seleccionar_archivo() {
    local filas=""
    local clipboard
    clipboard=$(wl-paste 2>/dev/null | tr -d '\r\n' || true)
    clipboard="${clipboard#file://}"

    if [ -n "$clipboard" ] && [ -f "$clipboard" ]; then
        filas+="<b>📋 Usar archivo copiado en portapapeles</b>   <span alpha='70%'>$(basename "$clipboard")</span>\0icon\x1fedit-paste\x1finfo\x1f$clipboard\n"
    fi

    filas+="<b>📂 Examinar archivo con diálogo visual...</b>   <span alpha='70%'>Abrir explorador GTK</span>\0icon\x1ffolder-open\x1finfo\x1f__BUSCAR__\n"
    filas+="<b>📋 Ver cola de impresión y trabajos activos</b>   <span alpha='70%'>Ver estado o cancelar envíos</span>\0icon\x1fprinter\x1finfo\x1f__COLA__\n"
    filas+="<b>⚙️  Añadir / Configurar impresoras</b>   <span alpha='70%'>system-config-printer</span>\0icon\x1fpreferences-system\x1finfo\x1f__CONFIG__\n"

    # Buscar archivos recientes en Descargas, Documentos, Escritorio y carpeta actual
    local encontrados
    encontrados=$(find "$HOME/Descargas" "$HOME/Documentos" "$HOME/Escritorio" . -maxdepth 2 -type f \
        \( -iname "*.pdf" -o -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.tif" -o -iname "*.tiff" \) \
        -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n 15 | cut -d' ' -f2-)

    if [ -n "$encontrados" ]; then
        filas+="--- Archivos recientes detectados ---\0nonselectable\x1ftrue\n"
        while IFS= read -r ruta; do
            [ -z "$ruta" ] && continue
            local nombre dir
            nombre=$(basename "$ruta")
            dir=$(dirname "$ruta")
            filas+="<b>$nombre</b>   <span alpha='65%'>$dir</span>\0icon\x1fx-office-document\x1finfo\x1f$ruta\n"
        done <<< "$encontrados"
    fi

    local eleccion
    eleccion=$(printf '%b' "$filas" | rofi -dmenu -i -p "Imprimir Archivo" -markup-rows \
        -theme-str "window { width: 55%; }" \
        -theme-str "listview { lines: 12; }" \
        -theme-str "element { padding: 8px 10px; }")

    [ -z "$eleccion" ] && exit 0

    if [[ "$eleccion" =~ "Examinar archivo" ]]; then
        local examinado
        examinado=$(examinar_archivo_gtk)
        if [ -n "$examinado" ] && [ -f "$examinado" ]; then
            printf '%s' "$examinado"
            return
        fi
        exit 0
    elif [[ "$eleccion" =~ "Ver cola de impresión" ]]; then
        ver_cola_impresion
        seleccionar_archivo
        return
    elif [[ "$eleccion" =~ "Añadir / Configurar impresoras" ]]; then
        system-config-printer &
        exit 0
    elif [[ "$eleccion" =~ "archivo copiado en portapapeles" ]]; then
        printf '%s' "$clipboard"
        return
    else
        # Buscar el nombre en los encontrados
        local seleccionado_nombre
        seleccionado_nombre=$(sed -E 's/<[^>]+>//g' <<< "$eleccion" | awk '{print $1}')
        local match
        match=$(grep -m1 -F "/$seleccionado_nombre" <<< "$encontrados" || true)
        if [ -n "$match" ] && [ -f "$match" ]; then
            printf '%s' "$match"
            return
        fi
    fi
}

# =============================================================================
# INICIO DEL PROCESO
# =============================================================================

ARCHIVO="${1:-}"

if [[ "$ARCHIVO" == "-h" || "$ARCHIVO" == "--help" ]]; then
    echo "Uso: impresion.sh [archivo.pdf|imagen]"
    echo "Abre el gestor interactivo de impresión en Rofi (SUPER + P)."
    echo "Permite configurar impresora, tamaño de papel/rollo, ahorro de tinta, color y redimensión."
    exit 0
fi

# Si no se pasó archivo o no existe, preguntar
if [ -z "$ARCHIVO" ] || [ ! -f "$ARCHIVO" ]; then
    ARCHIVO=$(seleccionar_archivo)
fi

[ -n "$ARCHIVO" ] && [ -f "$ARCHIVO" ] || exit 0

# Impresora seleccionada
IMPRESORA=$(obtener_predeterminada)
if [ -z "$IMPRESORA" ]; then
    rofi -e "No se encontró ninguna impresora configurada en CUPS.\nPuedes añadir una abriendo system-config-printer." \
        -theme-str "window { width: 40%; }"
    exit 1
fi

# Detectar perfil inicial según impresora
es_plotter() {
    [[ "$IMPRESORA" =~ DesignJet|T650|Plotter|plotter ]]
}

if es_plotter; then
    MEDIA="A1"
    INPUT_SLOT="MainRoll"
else
    MEDIA="A4"
    INPUT_SLOT="Auto"
fi

CALIDAD="Draft"         # Modo ahorro por defecto como pidió el usuario
COLOR="RGB"             # RGB o Gray
ESCALA_TIPO="fit"       # fit, 100, 90, 80, 75, 70, 50, 2up, 4up
COPIAS="1"

# Bucle principal de ajustes
while true; do
    # Textos descriptivos actuales
    case "$CALIDAD" in
        Draft)  TXT_CALIDAD="⚡ Ahorro / Borrador (Draft)" ;;
        Normal) TXT_CALIDAD="⚖️ Normal" ;;
        High)   TXT_CALIDAD="💎 Alta Resolución (High)" ;;
        *)      TXT_CALIDAD="$CALIDAD" ;;
    esac

    case "$COLOR" in
        Gray) TXT_COLOR="⚫ Escala de Grises (Ahorro color)" ;;
        RGB)  TXT_COLOR="🌈 Todo Color" ;;
        *)    TXT_COLOR="$COLOR" ;;
    esac

    case "$ESCALA_TIPO" in
        fit)   TXT_ESCALA="📐 Ajustar a la página (fit-to-page)" ;;
        100)   TXT_ESCALA="💯 Tamaño original (100%)" ;;
        90)    TXT_ESCALA="🔍 90% (Contenido reducido, + margen)" ;;
        80)    TXT_ESCALA="🔍 80% (Contenido reducido, + margen)" ;;
        75)    TXT_ESCALA="🔍 75% (Contenido reducido, + margen)" ;;
        70)    TXT_ESCALA="🔍 70% (Contenido reducido, + margen)" ;;
        50)    TXT_ESCALA="🔍 50% (Reducido a la mitad)" ;;
        2up)   TXT_ESCALA="👥 2 páginas por hoja (number-up=2)" ;;
        4up)   TXT_ESCALA="👥 4 páginas por hoja (number-up=4)" ;;
        *)     TXT_ESCALA="$ESCALA_TIPO" ;;
    esac

    TXT_PAPEL="$MEDIA"
    [ "$INPUT_SLOT" = "MainRoll" ] && TXT_PAPEL+=" [Rollo Principal]"
    [ "$INPUT_SLOT" = "Auto" ] && TXT_PAPEL+=" [Bandeja Auto]"

    MENU="<b>🚀 IMPRIMIR AHORA</b>   <span alpha='70%'>Enviar orden a $IMPRESORA</span>\0icon\x1fprinter\n"
    MENU+="🖨️  <b>Impresora:</b>        <span alpha='85%'>$IMPRESORA</span>\0icon\x1fprinter\n"
    MENU+="📄  <b>Archivo:</b>          <span alpha='85%'>$(basename "$ARCHIVO")</span>\0icon\x1fx-office-document\n"
    MENU+="📏  <b>Tamaño de papel:</b>   <span alpha='85%'>$TXT_PAPEL</span>\0icon\x1fdocument-page-setup\n"
    MENU+="⚡  <b>Calidad / Tinta:</b>   <span alpha='85%'>$TXT_CALIDAD</span>\0icon\x1fcolor-management\n"
    MENU+="🎨  <b>Modo de color:</b>     <span alpha='85%'>$TXT_COLOR</span>\0icon\x1fimage-x-generic\n"
    MENU+="🔍  <b>Escala en hoja:</b>    <span alpha='85%'>$TXT_ESCALA</span>\0icon\x1fzoom-fit-best\n"
    MENU+="📑  <b>Copias:</b>           <span alpha='85%'>$COPIAS</span>\0icon\x1fedit-copy\n"
    MENU+="📋  <b>Ver cola / Cancelar</b> <span alpha='70%'>Gestionar trabajos activos</span>\0icon\x1fsystem-run\n"
    MENU+="❌  <b>Cancelar</b>          <span alpha='70%'>Salir sin imprimir</span>\0icon\x1fwindow-close\n"

    OPCION=$(printf '%b' "$MENU" | rofi -dmenu -i -p "Gestor de Impresión" -markup-rows \
        -mesg "Configura las opciones y selecciona 'IMPRIMIR AHORA'" \
        -theme-str "window { width: 50%; }" \
        -theme-str "listview { lines: 11; }" \
        -theme-str "element { padding: 8px 10px; }")

    [ -z "$OPCION" ] && exit 0

    if [[ "$OPCION" =~ "IMPRIMIR AHORA" ]]; then
        break
    elif [[ "$OPCION" =~ "Cancelar" ]]; then
        exit 0
    elif [[ "$OPCION" =~ "Ver cola / Cancelar" ]]; then
        ver_cola_impresion
    elif [[ "$OPCION" =~ "Impresora:" ]]; then
        TODAS=$(obtener_impresoras)
        FILAS_IMP=""
        while IFS= read -r pr; do
            [ -z "$pr" ] && continue
            local marca=""
            [ "$pr" = "$IMPRESORA" ] && marca="  ·  actual"
            FILAS_IMP+="<b>$pr</b><span alpha='65%'>$marca</span>\0icon\x1fprinter\n"
        done <<< "$TODAS"
        FILAS_IMP+="<b>⚙️  Añadir nueva impresora...</b>   <span alpha='65%'>Abrir system-config-printer</span>\0icon\x1fpreferences-system\n"

        SEL_IMP=$(printf '%b' "$FILAS_IMP" | rofi -dmenu -i -p "Seleccionar Impresora" -markup-rows \
            -theme-str "window { width: 45%; }")
        if [[ "$SEL_IMP" =~ "Añadir nueva impresora" ]]; then
            system-config-printer &
        elif [ -n "$SEL_IMP" ]; then
            IMPRESORA=$(sed -E 's/<[^>]+>//g' <<< "$SEL_IMP" | awk '{print $1}')
            if es_plotter; then
                MEDIA="A1"
                INPUT_SLOT="MainRoll"
            else
                MEDIA="A4"
                INPUT_SLOT="Auto"
            fi
        fi
    elif [[ "$OPCION" =~ "Archivo:" ]]; then
        NUEVO_ARCH=$(seleccionar_archivo)
        [ -n "$NUEVO_ARCH" ] && [ -f "$NUEVO_ARCH" ] && ARCHIVO="$NUEVO_ARCH"
    elif [[ "$OPCION" =~ "Tamaño de papel:" ]]; then
        FILAS_PAPEL=""
        if es_plotter; then
            FILAS_PAPEL+="<b>A1 (Rollo Plotter - 594x841 mm)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>A0 (Rollo Plotter - 841x1189 mm)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>A2 (Rollo Plotter - 420x594 mm)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>ARCH D (24x36\" - Rollo)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>ARCH C (18x24\" - Rollo)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>A3 (Bandeja / Hoja suelta)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>A4 (Bandeja / Hoja suelta)</b>\0icon\x1fdocument-page-setup\n"
        else
            FILAS_PAPEL+="<b>A4 (Estándar internacional)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>Letter (Carta)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>Legal (Oficio)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>A3 (Formato grande)</b>\0icon\x1fdocument-page-setup\n"
            FILAS_PAPEL+="<b>A5 (Medio folio)</b>\0icon\x1fdocument-page-setup\n"
        fi

        SEL_PAPEL=$(printf '%b' "$FILAS_PAPEL" | rofi -dmenu -i -p "Tamaño de Papel" -markup-rows \
            -theme-str "window { width: 40%; }")
        if [ -n "$SEL_PAPEL" ]; then
            if es_plotter; then
                INPUT_SLOT="MainRoll"
            else
                INPUT_SLOT="Auto"
            fi
            case "$SEL_PAPEL" in
                *"A1"*)     MEDIA="A1" ;;
                *"A0"*)     MEDIA="A0" ;;
                *"A2"*)     MEDIA="A2" ;;
                *"ARCH D"*) MEDIA="ARCHD"; INPUT_SLOT="MainRoll" ;;
                *"ARCH C"*) MEDIA="ARCHC"; INPUT_SLOT="MainRoll" ;;
                *"A3"*)     MEDIA="A3";    INPUT_SLOT="Auto" ;;
                *"A4"*)     MEDIA="A4";    INPUT_SLOT="Auto" ;;
                *"Letter"*) MEDIA="Letter"; INPUT_SLOT="Auto" ;;
                *"Legal"*)  MEDIA="Legal";  INPUT_SLOT="Auto" ;;
                *"A5"*)     MEDIA="A5";     INPUT_SLOT="Auto" ;;
            esac
        fi
    elif [[ "$OPCION" =~ "Calidad / Tinta:" ]]; then
        FILAS_CAL="<b>⚡ Modo Ahorro / Borrador (Draft)</b>   <span alpha='70%'>Menos tinta, impresión veloz</span>\0icon\x1fweather-few-clouds\n"
        FILAS_CAL+="<b>⚖️ Calidad Normal</b>   <span alpha='70%'>Balance óptimo texto/líneas</span>\0icon\x1fweather-clear\n"
        FILAS_CAL+="<b>💎 Alta Calidad (High)</b>   <span alpha='70%'>Máxima definición y densidad</span>\0icon\x1fweather-storm\n"

        SEL_CAL=$(printf '%b' "$FILAS_CAL" | rofi -dmenu -i -p "Calidad de Impresión" -markup-rows \
            -theme-str "window { width: 45%; }")
        if [[ "$SEL_CAL" =~ "Ahorro / Borrador" ]]; then
            CALIDAD="Draft"
        elif [[ "$SEL_CAL" =~ "Calidad Normal" ]]; then
            CALIDAD="Normal"
        elif [[ "$SEL_CAL" =~ "Alta Calidad" ]]; then
            CALIDAD="High"
        fi
    elif [[ "$OPCION" =~ "Modo de color:" ]]; then
        FILAS_COL="<b>⚫ Monocromo / Escala de Grises</b>   <span alpha='70%'>Ahorra tinta de color (tinta negra/gris)</span>\0icon\x1fimage-missing\n"
        FILAS_COL+="<b>🌈 Todo Color (RGB)</b>   <span alpha='70%'>Planos y documentos a todo color</span>\0icon\x1fimage-x-generic\n"

        SEL_COL=$(printf '%b' "$FILAS_COL" | rofi -dmenu -i -p "Modo de Color" -markup-rows \
            -theme-str "window { width: 45%; }")
        if [[ "$SEL_COL" =~ "Escala de Grises" ]]; then
            COLOR="Gray"
        elif [[ "$SEL_COL" =~ "Todo Color" ]]; then
            COLOR="RGB"
        fi
    elif [[ "$OPCION" =~ "Escala en hoja:" ]]; then
        FILAS_ESC="<b>📐 Ajustar a la página (fit-to-page)</b>   <span alpha='70%'>Escala el contenido al área imprimible</span>\n"
        FILAS_ESC+="<b>💯 100% Tamaño original</b>   <span alpha='70%'>Sin escalado</span>\n"
        FILAS_ESC+="<b>🔍 90% del tamaño</b>   <span alpha='70%'>Reducir contenido 10% para margen</span>\n"
        FILAS_ESC+="<b>🔍 85% del tamaño</b>   <span alpha='70%'>Reducir contenido 15% para margen</span>\n"
        FILAS_ESC+="<b>🔍 80% del tamaño</b>   <span alpha='70%'>Reducir contenido 20% para margen</span>\n"
        FILAS_ESC+="<b>🔍 75% del tamaño</b>   <span alpha='70%'>Reducir contenido 25% para margen</span>\n"
        FILAS_ESC+="<b>🔍 70% del tamaño</b>   <span alpha='70%'>Reducir contenido 30% para margen</span>\n"
        FILAS_ESC+="<b>🔍 50% del tamaño</b>   <span alpha='70%'>Reducir a la mitad</span>\n"
        FILAS_ESC+="<b>👥 2 páginas por hoja (number-up=2)</b>   <span alpha='70%'>2 páginas en una misma cara</span>\n"
        FILAS_ESC+="<b>👥 4 páginas por hoja (number-up=4)</b>   <span alpha='70%'>4 páginas en una misma cara</span>\n"

        SEL_ESC=$(printf '%b' "$FILAS_ESC" | rofi -dmenu -i -p "Escala y Redimensión" -markup-rows \
            -theme-str "window { width: 45%; }")
        if [[ "$SEL_ESC" =~ "Ajustar a la página" ]]; then
            ESCALA_TIPO="fit"
        elif [[ "$SEL_ESC" =~ "100%" ]]; then
            ESCALA_TIPO="100"
        elif [[ "$SEL_ESC" =~ "90%" ]]; then
            ESCALA_TIPO="90"
        elif [[ "$SEL_ESC" =~ "85%" ]]; then
            ESCALA_TIPO="85"
        elif [[ "$SEL_ESC" =~ "80%" ]]; then
            ESCALA_TIPO="80"
        elif [[ "$SEL_ESC" =~ "75%" ]]; then
            ESCALA_TIPO="75"
        elif [[ "$SEL_ESC" =~ "70%" ]]; then
            ESCALA_TIPO="70"
        elif [[ "$SEL_ESC" =~ "50%" ]]; then
            ESCALA_TIPO="50"
        elif [[ "$SEL_ESC" =~ "2 páginas" ]]; then
            ESCALA_TIPO="2up"
        elif [[ "$SEL_ESC" =~ "4 páginas" ]]; then
            ESCALA_TIPO="4up"
        fi
    elif [[ "$OPCION" =~ "Copias:" ]]; then
        SEL_COP=$(printf "1 copia\n2 copias\n3 copias\n4 copias\n5 copias\n10 copias" | rofi -dmenu -i -p "Número de Copias" \
            -theme-str "window { width: 25%; }")
        if [ -n "$SEL_COP" ]; then
            COPIAS=$(awk '{print $1}' <<< "$SEL_COP")
            [[ "$COPIAS" =~ ^[0-9]+$ ]] || COPIAS="1"
        fi
    fi
done

# =============================================================================
# EJECUCIÓN DEL COMANDO LP
# =============================================================================

COMANDO=(lp -d "$IMPRESORA" -o media="$MEDIA" -n "$COPIAS")

# Bandeja / Origen
if [ -n "$INPUT_SLOT" ]; then
    COMANDO+=(-o "InputSlot=$INPUT_SLOT")
fi

# Calidad
if [ -n "$CALIDAD" ]; then
    COMANDO+=(-o "cupsPrintQuality=$CALIDAD")
fi

# Color
if [ -n "$COLOR" ]; then
    COMANDO+=(-o "ColorModel=$COLOR")
fi

# Escala / Redimensión
case "$ESCALA_TIPO" in
    fit) COMANDO+=(-o "fit-to-page") ;;
    100) COMANDO+=(-o "scaling=100") ;;
    90|80|85|75|70|50) COMANDO+=(-o "scaling=$ESCALA_TIPO") ;;
    2up) COMANDO+=(-o "number-up=2") ;;
    4up) COMANDO+=(-o "number-up=4") ;;
esac

COMANDO+=("$ARCHIVO")

# Ejecución y captura de salida
SALIDA=$("${COMANDO[@]}" 2>&1)
ESTADO=$?

if [ $ESTADO -eq 0 ]; then
    JOB_ID=$(grep -oP 'request id is \K[^ ]+' <<< "$SALIDA" || echo "Enviado")
    notificar "Impresión iniciada" "ID: $JOB_ID\nImpresora: $IMPRESORA\nArchivo: $(basename "$ARCHIVO")"
else
    error_notificar "Fallo al enviar la impresión:\n$SALIDA"
fi
