#!/bin/bash
# Pxmm CAM - Inicialização 1-clique (macOS)
# Dar permissão: chmod +x scripts/start_mac.command

cd "$(dirname "$0")/.."

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

python "$PWD/run.py"
