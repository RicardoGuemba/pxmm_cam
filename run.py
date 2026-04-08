#!/usr/bin/env python3
"""
Launcher para Pxmm CAM a partir da raiz do projeto.

Garante que o pacote seja encontrado (sys.path) e chama o bootstrap da aplicação.
Use este arquivo para iniciar o app:
  - Cursor: abra run.py e execute "Run Python File".
  - Terminal: na pasta do projeto, execute python run.py
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pxmm_cam.app import main

if __name__ == "__main__":
    sys.exit(main())
