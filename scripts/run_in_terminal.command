#!/bin/bash
# Executado pelo Pxmm CAM.app para iniciar o app dentro do Terminal (evita restrição de permissão do macOS).

cd "$(dirname "$0")/.."

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

python3 run.py 2>&1
EXIT=$?
if [ $EXIT -ne 0 ]; then
    echo ""
    echo "Saída com erro (código $EXIT). Verifique logs em: $(pwd)/logs/"
    read -p "Pressione Enter para fechar..."
fi
exit $EXIT
