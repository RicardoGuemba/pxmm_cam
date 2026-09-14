# Pxmm CAM

Aplicação desktop (Windows/macOS) para streaming de câmeras **USB** e **Omron Sentech (StApi/stapipy)**, medição por dois cliques e calibração px↔mm com exportação CSV/JSON.

## Clonar e executar

```bash
git clone https://github.com/RicardoGuemba/pxmm_cam.git
cd pxmm_cam
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python run.py
```

Documentação completa: [docs/README.md](docs/README.md).

## Requisitos

- Python 3.9+
- Dependências: PySide6, OpenCV, PyYAML, Pydantic, NumPy (instaladas via `pip install -e .`)
- Sentech: SentechSDK + wheel local `stapipy` (não está no PyPI)
