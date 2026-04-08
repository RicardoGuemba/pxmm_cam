# Pxmm CAM

Aplicação desktop (Windows/macOS) para streaming de câmeras **USB** e **GigE/LAN**, medição por dois cliques e calibração px↔mm com exportação CSV/JSON.

## Clonar e executar

```bash
git clone https://github.com/SEU_USUARIO/Pxmm_CAM.git
cd Pxmm_CAM
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python run.py
```

Documentação completa: [docs/README.md](docs/README.md).

## Requisitos

- Python 3.9+
- Dependências: PySide6, OpenCV, PyYAML, Pydantic, NumPy (instaladas via `pip install -e .`)
