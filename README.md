# Medição por câmera em pixels e milímetros

Aplicação desktop (Windows/macOS) para streaming de câmeras **USB** e **Omron Sentech (StApi/stapipy)**, medição por dois cliques e calibração px↔mm com exportação CSV/JSON.

**Primeira experiência.** Use uma referência de dimensão conhecida no plano de medição para calibrar a escala. Marque dois pontos de outro objeto nesse plano e confira a medida com a dimensão conhecida.

**Arquivos de referência**

- [run.py](run.py)
- [docs/README.md](docs/README.md)
- [tests](tests)

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
