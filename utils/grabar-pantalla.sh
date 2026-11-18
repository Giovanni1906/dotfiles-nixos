#!/usr/bin/env bash
# =============================================================================
# GRABAR PANTALLA: Grabación continua para Hyprland (sin cortes por workspace)
# =============================================================================
# Atajo: SUPER + SHIFT + R (toggle: si está grabando detiene, si no abre menú)
#
# Características:
#   - Graba la pantalla activa (enfocada), un monitor específico o ambas pantallas
#   - Al grabar salidas físicas de monitor (-o OUTPUT), el cambio de workspace
#     en Hyprland (1 al 10) NO corta la grabación en ningún momento.
#   - Soporta captura dual multimonitor uniendo los flujos lado a lado con ffmpeg.
#   - Soporta recorte de área (slurp).
#   - Opciones de audio: Micrófono (@DEFAULT_SOURCE@), Audio del sistema (@DEFAULT_SINK@.monitor)
#     o Mudo (solo video).
#   - Notificaciones con sonido al iniciar y finalizar, guardando en ~/Vídeos/Grabaciones/.

set -uo pipefail

ESTADO_FILE="${XDG_RUNTIME_DIR:-/tmp}/dotfiles-grabacion-$USER.state"
DIR_DESTINO="$HOME/Vídeos/Grabaciones"
mkdir -p "$DIR_DESTINO"
SONIDO_INICIO="/run/current-system/sw/share/sounds/freedesktop/stereo/bell.oga"
SONIDO_FIN="/run/current-system/sw/share/sounds/freedesktop/stereo/complete.oga"

# -----------------------------------------------------------------------------
# Helpers de comando
# -----------------------------------------------------------------------------
get_wf_recorder_cmd() {
    if command -v wf-recorder >/dev/null 2>&1; then
        command -v wf-recorder
        return 0
    fi
    # Buscar binario en /nix/store (útil antes de nixos-rebuild switch)
    local store_bin
    store_bin=$(find /nix/store -maxdepth 3 -name wf-recorder -type f -perm -111 2>/dev/null | grep "/bin/wf-recorder" | head -n 1)
    if [ -n "$store_bin" ] && [ -x "$store_bin" ]; then
        echo "$store_bin"
        return 0
    fi
    echo "wf-recorder"
}

notificar() {
    local titulo="$1" mensaje="$2" urgencia="${3:-normal}" icono="${4:-media-record}"
    notify-send -u "$urgencia" -a "Grabador" -i "$icono" "$titulo" "$mensaje"
}

reproducir_sonido() {
    local sonido="$1"
    if [ -f "$sonido" ] && command -v paplay >/dev/null 2>&1; then
        paplay "$sonido" >/dev/null 2>&1 &
    fi
}

# -----------------------------------------------------------------------------
# Comprobación y Detención de Grabación Activa
# -----------------------------------------------------------------------------
esta_grabando() {
    if [ ! -f "$ESTADO_FILE" ]; then
        return 1
    fi
    # Leer PIDs guardados
    local pids
    pids=$(grep "^PIDS=" "$ESTADO_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"')
    if [ -z "$pids" ]; then
        rm -f "$ESTADO_FILE"
        return 1
    fi

    local algun_vivo=0
    for pid in $pids; do
        if kill -0 "$pid" 2>/dev/null; then
            algun_vivo=1
            break
        fi
    done

    if [ "$algun_vivo" -eq 1 ]; then
        return 0
    else
        rm -f "$ESTADO_FILE"
        return 1
    fi
}

detener_grabacion() {
    if [ ! -f "$ESTADO_FILE" ]; then
        notificar "Grabador" "No hay ninguna grabación en curso." "low"
        exit 0
    fi

    # Cargar variables del estado
    # shellcheck disable=SC1090
    source "$ESTADO_FILE"

    notificar "Grabador" "Finalizando grabación y guardando archivo..." "normal" "media-playback-stop"

    # Enviar SIGINT para que wf-recorder cierre los contenedores MP4 correctamente
    for pid in $PIDS; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -INT "$pid" 2>/dev/null || true
        fi
    done

    # Esperar a que terminen los procesos
    local timeout=10
    local count=0
    while :; do
        local activos=0
        for pid in $PIDS; do
            if kill -0 "$pid" 2>/dev/null; then
                activos=1
                break
            fi
        done
        [ "$activos" -eq 0 ] && break

        sleep 0.5
        count=$((count + 1))
        if [ "$count" -ge $((timeout * 2)) ]; then
            for pid in $PIDS; do
                kill -TERM "$pid" 2>/dev/null || true
            done
            break
        fi
    done

    # Si era modo dual (dos pantallas simultáneas), unir con ffmpeg hstack
    if [ "${MODO:-}" = "dual" ] && [ -f "${TEMP_LEFT:-}" ] && [ -f "${TEMP_RIGHT:-}" ]; then
        notificar "Grabador" "Uniendo pantallas en video panorámico..." "normal" "video-x-generic"
        
        # Unir lado a lado
        if [ "${TIENE_AUDIO:-0}" -eq 1 ]; then
            ffmpeg -y -hide_banner -loglevel error \
                -i "$TEMP_LEFT" -i "$TEMP_RIGHT" \
                -filter_complex "[0:v][1:v]hstack=inputs=2[v]" \
                -map "[v]" -map 0:a? \
                -c:v libx264 -crf 20 -preset superfast -c:a copy \
                "$SALIDA"
        else
            ffmpeg -y -hide_banner -loglevel error \
                -i "$TEMP_LEFT" -i "$TEMP_RIGHT" \
                -filter_complex "[0:v][1:v]hstack=inputs=2[v]" \
                -map "[v]" \
                -c:v libx264 -crf 20 -preset superfast \
                "$SALIDA"
        fi

        rm -f "$TEMP_LEFT" "$TEMP_RIGHT"
    fi

    rm -f "$ESTADO_FILE"
    reproducir_sonido "$SONIDO_FIN"

    if [ -f "$SALIDA" ]; then
        local tamano duracion_texto=""
        tamano=$(du -h "$SALIDA" 2>/dev/null | awk '{print $1}')
        if [ -n "${INICIO_TS:-}" ]; then
            local segs=$(( $(date +%s) - INICIO_TS ))
            local mins=$(( segs / 60 ))
            local rem=$(( segs % 60 ))
            if [ "$mins" -gt 0 ]; then
                duracion_texto="${mins}m ${rem}s"
            else
                duracion_texto="${rem}s"
            fi
        fi

        notificar "Grabación guardada" "Archivo: $(basename "$SALIDA")\nTamaño: ${tamano:-desconocido}${duracion_texto:+ | Duración: $duracion_texto}\nGuardado en: ~/Vídeos/Grabaciones/" "normal" "video-x-generic"
    else
        notificar "Grabador" "La grabación se detuvo pero no se generó el archivo." "critical" "dialog-error"
    fi

    exit 0
}

# -----------------------------------------------------------------------------
# Detección de Monitores (Hyprland)
# -----------------------------------------------------------------------------
obtener_monitores() {
    python3 -c "
import json, subprocess, sys
try:
    data = json.loads(subprocess.check_output(['hyprctl', 'monitors', '-j']))
    # Ordenar por coordenada X de izquierda a derecha
    data.sort(key=lambda m: m.get('x', 0))
    for m in data:
        name = m.get('name', '')
        x = m.get('x', 0)
        w = m.get('width', 1920)
        h = m.get('height', 1080)
        rr = int(round(m.get('refreshRate', 60)))
        focused = '1' if m.get('focused', False) else '0'
        desc = m.get('description', '')
        print(f'{name}|{x}|{w}|{h}|{rr}|{focused}|{desc}')
except Exception as e:
    sys.exit(1)
"
}

# -----------------------------------------------------------------------------
# Menú de Selección e Inicio
# -----------------------------------------------------------------------------
iniciar_grabacion_menu() {
    mkdir -p "$DIR_DESTINO"
    local WF_BIN
    WF_BIN=$(get_wf_recorder_cmd)

    local monitores_raw
    monitores_raw=$(obtener_monitores)

    local -a nombres=() xs=() ws=() hs=() rrs=() focuseds=() descs=()
    local monitor_enfocado=""
    local monitor_enfocado_desc=""

    while IFS='|' read -r m_name m_x m_w m_h m_rr m_foc m_desc; do
        [ -z "$m_name" ] && continue
        nombres+=("$m_name")
        xs+=("$m_x")
        ws+=("$m_w")
        hs+=("$m_h")
        rrs+=("$m_rr")
        focuseds+=("$m_foc")
        descs+=("$m_desc")
        if [ "$m_foc" = "1" ]; then
            monitor_enfocado="$m_name"
            monitor_enfocado_desc="$m_desc"
        fi
    done <<< "$monitores_raw"

    local total_monitores=${#nombres[@]}
    if [ "$total_monitores" -eq 0 ]; then
        notificar "Error" "No se detectaron monitores activos en Hyprland." "critical"
        exit 1
    fi

    [ -z "$monitor_enfocado" ] && monitor_enfocado="${nombres[0]}"

    # Construir opciones para Rofi
    local -a opciones_menu=()
    opciones_menu+=("🖥️  Pantalla actual (${monitor_enfocado} - ${monitor_enfocado_desc})")

    if [ "$total_monitores" -gt 1 ]; then
        for i in "${!nombres[@]}"; do
            local etiqueta="Monitor"
            if [ "$i" -eq 0 ]; then
                etiqueta="Monitor izquierdo"
            elif [ "$i" -eq $((total_monitores - 1)) ]; then
                etiqueta="Monitor derecho"
            fi
            opciones_menu+=("📺  ${etiqueta} (${nombres[$i]} - ${ws[$i]}x${hs[$i]}@${rrs[$i]}Hz)")
        done
        opciones_menu+=("👥  Ambas pantallas (Multimonitor lado a lado)")
    fi

    opciones_menu+=("✂️  Seleccionar área (con el ratón)")

    local sel_pantalla
    sel_pantalla=$(printf '%s\n' "${opciones_menu[@]}" | rofi -dmenu -i -p "📹 Grabar pantalla" -mesg "La grabación es continua y no se corta al cambiar de workspace.")
    [ -z "$sel_pantalla" ] && exit 0

    # Menú de Audio
    local -a opciones_audio=(
        "🔇  Sin audio (solo video)"
        "🎤  Con micrófono (voz)"
        "🔊  Con audio del sistema (lo que suena en la PC)"
    )

    local sel_audio
    sel_audio=$(printf '%s\n' "${opciones_audio[@]}" | rofi -dmenu -i -p "🎙️ Modo de audio" -mesg "¿Deseas capturar audio durante la grabación?")
    [ -z "$sel_audio" ] && exit 0

    local audio_arg="" tiene_audio=0
    case "$sel_audio" in
        *"micrófono"*)
            audio_arg="-a"
            tiene_audio=1
            ;;
        *"audio del sistema"*)
            audio_arg="--audio=@DEFAULT_SINK@.monitor"
            tiene_audio=1
            ;;
        *)
            audio_arg=""
            tiene_audio=0
            ;;
    esac

    local timestamp
    timestamp=$(date +'%Y-%m-%d_%H-%M-%S')
    local archivo_salida="$DIR_DESTINO/grabacion_${timestamp}.mp4"
    local inicio_ts
    inicio_ts=$(date +%s)

    # Identificar la opción de pantalla seleccionada
    if [[ "$sel_pantalla" =~ ^"🖥️  Pantalla actual" ]]; then
        notificar "Grabando pantalla" "Grabando pantalla actual ($monitor_enfocado)...\nPresiona SUPER + SHIFT + R para detener." "normal"
        reproducir_sonido "$SONIDO_INICIO"

        # wf-recorder command
        local cmd=($WF_BIN -o "$monitor_enfocado" -c libx264 -x yuv420p -p preset=superfast -p tune=zerolatency -p crf=20)
        [ -n "$audio_arg" ] && cmd+=("$audio_arg")
        cmd+=(-f "$archivo_salida")

        "${cmd[@]}" >/dev/null 2>&1 &
        local pid=$!

        cat <<EOF > "$ESTADO_FILE"
PIDS="$pid"
MODO="single"
SALIDA="$archivo_salida"
INICIO_TS="$inicio_ts"
TIENE_AUDIO="$tiene_audio"
EOF

    elif [[ "$sel_pantalla" =~ ^"📺  " ]]; then
        # Extraer nombre del monitor entre paréntesis
        local mon_sel
        mon_sel=$(echo "$sel_pantalla" | sed -n 's/.*(\([A-Za-z0-9_-]*\) - .*/\1/p')
        [ -z "$mon_sel" ] && mon_sel="$monitor_enfocado"

        notificar "Grabando monitor" "Grabando monitor $mon_sel...\nPresiona SUPER + SHIFT + R para detener." "normal"
        reproducir_sonido "$SONIDO_INICIO"

        local cmd=($WF_BIN -o "$mon_sel" -c libx264 -x yuv420p -p preset=superfast -p tune=zerolatency -p crf=20)
        [ -n "$audio_arg" ] && cmd+=("$audio_arg")
        cmd+=(-f "$archivo_salida")

        "${cmd[@]}" >/dev/null 2>&1 &
        local pid=$!

        cat <<EOF > "$ESTADO_FILE"
PIDS="$pid"
MODO="single"
SALIDA="$archivo_salida"
INICIO_TS="$inicio_ts"
TIENE_AUDIO="$tiene_audio"
EOF

    elif [[ "$sel_pantalla" =~ ^"👥  Ambas pantallas" ]]; then
        local mon_left="${nombres[0]}"
        local mon_right="${nombres[1]}"
        local temp_left="/tmp/wf_dual_left_${timestamp}.mp4"
        local temp_right="/tmp/wf_dual_right_${timestamp}.mp4"

        notificar "Grabando ambas pantallas" "Grabando multimonitor ($mon_left + $mon_right)...\nPresiona SUPER + SHIFT + R para detener." "normal"
        reproducir_sonido "$SONIDO_INICIO"

        # Monitor izquierdo (con audio si aplica)
        local cmd_left=($WF_BIN -o "$mon_left" -c libx264 -x yuv420p -p preset=superfast -p tune=zerolatency -p crf=20)
        [ -n "$audio_arg" ] && cmd_left+=("$audio_arg")
        cmd_left+=(-f "$temp_left")

        # Monitor derecho (sin audio para evitar duplicar pistas)
        local cmd_right=($WF_BIN -o "$mon_right" -c libx264 -x yuv420p -p preset=superfast -p tune=zerolatency -p crf=20 -f "$temp_right")

        "${cmd_left[@]}" >/dev/null 2>&1 &
        local pid_left=$!
        "${cmd_right[@]}" >/dev/null 2>&1 &
        local pid_right=$!

        cat <<EOF > "$ESTADO_FILE"
PIDS="$pid_left $pid_right"
MODO="dual"
TEMP_LEFT="$temp_left"
TEMP_RIGHT="$temp_right"
SALIDA="$archivo_salida"
INICIO_TS="$inicio_ts"
TIENE_AUDIO="$tiene_audio"
EOF

    elif [[ "$sel_pantalla" =~ ^"✂️  Seleccionar área" ]]; then
        local geometria
        geometria=$(slurp 2>/dev/null)
        if [ -z "$geometria" ]; then
            exit 0
        fi

        notificar "Grabando área" "Grabando región seleccionada...\nPresiona SUPER + SHIFT + R para detener." "normal"
        reproducir_sonido "$SONIDO_INICIO"

        local cmd=($WF_BIN -g "$geometria" -c libx264 -x yuv420p -p preset=superfast -p tune=zerolatency -p crf=20)
        [ -n "$audio_arg" ] && cmd+=("$audio_arg")
        cmd+=(-f "$archivo_salida")

        "${cmd[@]}" >/dev/null 2>&1 &
        local pid=$!

        cat <<EOF > "$ESTADO_FILE"
PIDS="$pid"
MODO="single"
SALIDA="$archivo_salida"
INICIO_TS="$inicio_ts"
TIENE_AUDIO="$tiene_audio"
EOF
    fi

    exit 0
}

# -----------------------------------------------------------------------------
# Dispatcher Principal
# -----------------------------------------------------------------------------
accion="${1:-toggle}"

case "$accion" in
    stop)
        detener_grabacion
        ;;
    status)
        if esta_grabando; then
            echo "RECORDING"
            exit 0
        else
            echo "IDLE"
            exit 1
        fi
        ;;
    toggle)
        if esta_grabando; then
            detener_grabacion
        else
            iniciar_grabacion_menu
        fi
        ;;
    menu)
        iniciar_grabacion_menu
        ;;
    *)
        echo "Uso: $(basename "$0") [toggle|stop|status|menu]"
        exit 1
        ;;
esac
