#!/bin/bash
# Doble clic en Finder para abrir el clasificador en la Terminal (Mac).
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "No se encontro la instalacion todavia (.venv)."
    echo "Instalala una sola vez desde la Terminal, en esta carpeta, con:"
    echo "  uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt"
    echo
    read -n 1 -s -r -p "Presiona una tecla para cerrar..."
    exit 1
fi

.venv/bin/python clasificar_fotos.py "$@"

echo
read -n 1 -s -r -p "Presiona una tecla para cerrar..."
