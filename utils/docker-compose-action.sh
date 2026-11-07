#!/usr/bin/env bash
# =============================================================================
# Ejecuta una acción de Docker Compose sobre todo el stack del contenedor dado
# =============================================================================

ACTION="${1:-stop}"
CID="$2"

if [ -z "$CID" ]; then
    echo "Uso: $0 <stop|down|restart|up> <container_id>"
    exit 1
fi

PROJECT=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$CID" 2>/dev/null)

if [ -z "$PROJECT" ]; then
    echo "Aviso: El contenedor $CID no pertenece a ningún proyecto de Docker Compose."
    exit 1
fi

echo "Ejecutando 'docker compose -p $PROJECT $ACTION'..."
docker compose -p "$PROJECT" "$ACTION"
