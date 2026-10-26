#!/usr/bin/env bash
# Cliente Qsync de esta PC de oficina. El espacio de Qsync no aparece al montar
# la NAS por IP: hace falta el mismo cliente que el portátil. El .deb es de
# Ubuntu 22.04 y corre en un contenedor (distrobox); las carpetas quedan en el
# home de esta PC. Solo esta máquina tiene distrobox (nixos/equipos/pc-admision-jorge).

set -euo pipefail

CAJA=qsync
IMAGEN=ubuntu:22.04
DEB_URL="https://download.qnap.com/Storage/Utility/QNAPQsyncClientUbuntux64-1.0.12.2202.deb"
DEB_NOMBRE="QNAPQsyncClientUbuntux64-1.0.12.2202.deb"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles"
DEB="$CACHE/$DEB_NOMBRE"
BIN=/usr/local/bin/QNAP/QsyncClient/Qsync
LANZADOR=/usr/local/bin/QNAP/QsyncClient/Qsync.sh
ICONO="$HOME/.local/share/icons/Qsync.png"
ESCRITORIO="$HOME/.local/share/applications/qsync.desktop"
LOCAL="$HOME/dotfiles/config/hypr/local.conf"
LOG="$CACHE/qsync.log"
# Librerías que el .deb no declara y Ubuntu mínimo no trae (Qt va dentro del paquete).
PAQUETES="libgl1 libegl1 libglib2.0-0 libdbus-1-3 libnss3 libnspr4 libusb-1.0-0 libx11-6 libxcb1 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render0 libxcb-render-util0 libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-xfixes0 libxcb-xkb1 libxkbcommon0 libxkbcommon-x11-0 libfontconfig1 libfreetype6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 libxtst6 libxi6 libxrender1 libsm6 libice6 libcups2 libpango-1.0-0 libatk1.0-0 libatk-bridge2.0-0 libdrm2 libgbm1 libxss1 libxshmfence1 libglu1-mesa ca-certificates libasound2 fonts-dejavu-core"

export DBX_CONTAINER_MANAGER=docker

avisar() {
    notify-send "Qsync" "$1" || true
}

if ! command -v distrobox >/dev/null; then
    echo "Falta distrobox. En esta PC ejecuta nix-switch y vuelve a lanzar qsync." >&2
    avisar "Falta distrobox. Ejecuta nix-switch y vuelve a lanzar qsync."
    exit 1
fi

caja_existe() {
    distrobox list --no-color 2>/dev/null | awk -F'|' 'NR > 1 { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2 }' | grep -qx "$CAJA"
}

en_marcha() {
    distrobox enter --name "$CAJA" -- pgrep -x Qsync >/dev/null 2>&1
}

mkdir -p "$CACHE" "$HOME/.local/share/icons" "$HOME/.local/share/applications"

if [[ ! -f "$DEB" ]]; then
    curl -fL --retry 3 -o "$DEB.parcial" "$DEB_URL"
    mv "$DEB.parcial" "$DEB"
fi

# Docker 29 no arranca la caja si Distrobox tapa /dev/ptmx con /dev/null.
crear_caja() {
    local shim docker_real
    shim=$(mktemp -d)
    docker_real=$(command -v docker)
    cat >"$shim/docker" <<EOF
#!/usr/bin/env bash
args=()
while [[ \$# -gt 0 ]]; do
    if [[ "\$1" == "--volume" && ( "\$2" == "/dev/null:/dev/ptmx" || "\$2" == "/dev/pts" ) ]]; then
        shift 2
        continue
    fi
    args+=("\$1")
    shift
done
exec $(printf '%q' "$docker_real") "\${args[@]}"
EOF
    chmod +x "$shim/docker"
    PATH="$shim:$PATH" distrobox create --yes --name "$CAJA" --image "$IMAGEN" --additional-packages "$PAQUETES"
    rm -rf "$shim"
}

if ! caja_existe; then
    crear_caja
fi

if ! distrobox enter --name "$CAJA" -- test -x "$BIN"; then
    distrobox enter --name "$CAJA" -- sudo dpkg --unpack "$DEB"
fi

# El .deb no tiene Depends; si falta alguna librería del sistema, se instala ahora.
faltan=$(distrobox enter --name "$CAJA" -- bash -lc "LD_LIBRARY_PATH=/usr/local/lib/QNAP/QsyncClient /usr/bin/ldd '$BIN'" | awk '/not found/ { print $1 }' || true)
if [[ -n "$faltan" ]]; then
    distrobox enter --name "$CAJA" -- sudo apt-get update
    distrobox enter --name "$CAJA" -- sudo apt-get install -y $PAQUETES
    faltan=$(distrobox enter --name "$CAJA" -- bash -lc "LD_LIBRARY_PATH=/usr/local/lib/QNAP/QsyncClient /usr/bin/ldd '$BIN'" | awk '/not found/ { print $1 }' || true)
fi
if [[ -n "$faltan" ]]; then
    echo "Al cliente le faltan librerías:" >&2
    echo "$faltan" >&2
    avisar "El cliente no arranca: faltan librerías. Mira la terminal."
    exit 1
fi

if [[ ! -s "$ICONO" ]]; then
    distrobox enter --name "$CAJA" -- cat /usr/share/pixmaps/Qsync.png >"$ICONO" 2>/dev/null || true
fi

cat >"$ESCRITORIO" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Qsync
Comment=Carpetas de la NAS en esta PC
Exec=$HOME/dotfiles/utils/qsync.sh
Icon=$ICONO
Terminal=false
Categories=Network;FileTransfer;
EOF

if [[ -f "$LOCAL" ]] && ! grep -qxF 'exec-once = ~/dotfiles/utils/qsync.sh' "$LOCAL"; then
    printf '\n# Cliente Qsync: el espacio de la NAS no se ve al montarla por IP.\nexec-once = ~/dotfiles/utils/qsync.sh\n' >>"$LOCAL"
fi

if en_marcha; then
    exit 0
fi

# Qt viejo: XWayland es más estable que su plugin de Wayland en Hyprland.
# WebEngine dentro del contenedor no puede usar su sandbox.
nohup distrobox enter --name "$CAJA" -- env \
    QT_QPA_PLATFORM=xcb \
    QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox \
    "$LANZADOR" >>"$LOG" 2>&1 &
disown || true
avisar "Abre la ventana, entra con la IP de la NAS y elige las mismas carpetas que el portátil."
