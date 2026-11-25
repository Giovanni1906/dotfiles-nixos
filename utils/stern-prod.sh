#!/usr/bin/env bash
# =============================================================================
# stern-prod: seguimiento de logs de pods en el cluster de producción (admisión)
# =============================================================================
# Uso:
#   stern-prod                  # Sigue logs de todos los pods (query: .)
#   stern-prod <pod-query>      # Sigue logs de pods que coincidan con la regex/query
#   stern-prod [flags]          # Pasa flags a stern con query por defecto (.)
#   stern-prod <pod> [flags]    # Pasa flags a stern con la query indicada
# =============================================================================

set -euo pipefail

KUBECONFIG="${KUBECONFIG:-/home/admision/.kube/dalthon-server-kubeconfig.yaml}"

if [ ! -f "$KUBECONFIG" ]; then
    echo "Error: Kubeconfig no encontrado en $KUBECONFIG" >&2
    exit 1
fi

# Si no se pasan argumentos, o si el primer argumento es una bandera (-*),
# se usa '.' por defecto para mostrar los logs de todos los pods.
if [ $# -eq 0 ]; then
    exec stern --kubeconfig="$KUBECONFIG" .
elif [[ "$1" == -* ]]; then
    exec stern --kubeconfig="$KUBECONFIG" . "$@"
else
    exec stern --kubeconfig="$KUBECONFIG" "$@"
fi
