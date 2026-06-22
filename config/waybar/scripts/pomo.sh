# --- CONFIGURACIÓN ---
WORK_TIME=1500    # 25 min
SHORT_BREAK=300   # 5 min
LONG_BREAK=900    # 15 min
DATA_FILE="/tmp/pomo_status"
PID_FILE="/tmp/pomo_pid"
SOUND="/run/current-system/sw/share/sounds/freedesktop/stereo/complete.oga"

alert() {
    notify-send "Pomodoro" "$1" -i timer-symbolic -u critical
    paplay "$SOUND"
}

timer_loop() {
    echo $BASHPID > "$PID_FILE"
    rounds=1

    while true; do
        # --- FASE TRABAJO ---
        alert "Ronda $rounds/4: ¡Enfoque total!"
        for ((i=$WORK_TIME; i>0; i--)); do
            echo "$i|WORK|Ronda $rounds" > "$DATA_FILE"
            sleep 1
        done

        if [ $rounds -lt 4 ]; then
            # --- DESCANSO CORTO ---
            alert "¡Tiempo! Descanso corto de 5 min."
            for ((i=$SHORT_BREAK; i>0; i--)); do
                echo "$i|BREAK|Descanso" > "$DATA_FILE"
                sleep 1
            done
            ((rounds++))
        else
            # --- DESCANSO LARGO ---
            alert "¡Excelente racha! Descanso largo de 15 min."
            for ((i=$LONG_BREAK; i>0; i--)); do
                echo "$i|LONG|Relax Largo" > "$DATA_FILE"
                sleep 1
            done
            rounds=1 # Reinicia el contador de rondas
        fi
    done
}

case "$1" in
    "start")
        if [ ! -f "$PID_FILE" ]; then
            timer_loop >/dev/null 2>&1 & disown
        fi
        ;;
    "stop")
        if [ -f "$PID_FILE" ]; then
            kill $(cat "$PID_FILE")
            rm -f "$DATA_FILE" "$PID_FILE"
            notify-send "Pomodoro" "Detenido correctamente."
        fi
        ;;
    *)
        if [ -f "$PID_FILE" ] && ! ps -p $(cat "$PID_FILE") > /dev/null; then
            rm -f "$DATA_FILE" "$PID_FILE"
        fi

        if [ -f "$DATA_FILE" ]; then
            # IMPORTANTE: Leemos 3 variables (sec, state, label)
            IFS='|' read -r sec state label <<< "$(cat "$DATA_FILE")"
            min=$((sec / 60))
            act_sec=$((sec % 60))
            time_str=$(printf "%02d:%02d" $min $act_sec)

            if [ "$state" == "WORK" ]; then
                echo "{\"text\": \"\", \"tooltip\": \"$label: $time_str\", \"class\": \"work\"}"
            elif [ "$state" == "BREAK" ]; then
                echo "{\"text\": \"󱐋\", \"tooltip\": \"$label: $time_str\", \"class\": \"break\"}"
            else
                echo "{\"text\": \"󰔟\", \"tooltip\": \"$label: $time_str\", \"class\": \"long\"}"
            fi
        else
            echo "{\"text\": \"󱎫\", \"tooltip\": \"Click para iniciar Pomodoro\", \"class\": \"idle\"}"
        fi
        ;;
esac
