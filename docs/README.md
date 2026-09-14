# Pxmm CAM

App desktop (Windows/macOS) para streaming de câmeras **USB** e **GigE Vision**, medição por dois cliques, calibração px↔mm e exportação CSV/JSON.

---

## Como iniciar a aplicação

Escolha **uma** das formas abaixo. A pasta de trabalho deve ser a **raiz do projeto** (onde estão `run.py` e `config.yaml`).

| Forma | Como fazer |
|-------|------------|
| **Cursor** | Abra o arquivo **`run.py`**, deixe-o selecionado e use **Run Python File** (ícone ▶ ou atalho de execução). |
| **Terminal** | Na raiz do projeto: `python run.py` ou `python -m pxmm_cam` (com `PYTHONPATH=src` se não tiver instalado com `pip install -e .`). |
| **macOS (Finder)** | Duplo clique em **`Pxmm CAM.app`** (o Terminal abre e em seguida a janela do app). Ou duplo clique em **`scripts/run_in_terminal.command`**. |
| **Windows** | Duplo clique em **`scripts\start_windows.bat`**. |

**Primeira vez:** instale as dependências (ver [Instalação](#instalação)). Se algo falhar, confira a pasta **`logs/`** (ex.: `launcher_error.log` ao usar o .app).

---

## Requisitos

- Python 3.9+
- PySide6, OpenCV, PyYAML, Pydantic, NumPy
- Câmera Omron Sentech: **SentechSDK** (ex. `/opt/sentech`) + wheel local **`stapipy`** (não está no PyPI). Não use Harvester/`.cti` para abrir a Sentech.

## Instalação

```bash
cd Pxmm_CAM
pip install -e .
# ou: pip install -r requirements.txt
# Sentech: instale o SentechSDK e o wheel stapipy da Omron (não há extra PyPI).
```

## Configuração

Edite **`config.yaml`** na raiz do projeto:

- **streaming.source_type**: `usb` ou `stapipy` (`gige` no yaml antigo vira `stapipy`)
- **streaming.usb_camera_index**: índice da câmera USB (0, 1, …)
- **streaming.device_index**: índice StApi (`0` = primeira câmera)
- **streaming.fetch_timeout_ms**: timeout de `retrieve_buffer`
- **streaming.gige_ip**: metadado/diagnóstico (ping); a abertura StApi **não** usa `gige://IP`
- `gige_backend` / `gentl_producer_path`: legado, ignorados

Validação é feita com Pydantic; mensagens de erro indicam campos inválidos.

## Uso

1. **Operação**: escolha Fonte (USB ou GigE/LAN). USB: detectar câmera. Sentech: Conectar usa StApi (`stapipy`). Clique em **Conectar**.
2. **Medição**: no vídeo, clique em dois pontos (A e B). Informe a distância real em mm no diálogo. A escala px/mm e mm/px é calculada e a medição entra no histórico.
3. **Exportar**: use o botão **Exportar** para salvar o histórico em CSV ou JSON (schema fixo).
4. **Diagnóstico**: stapipy importável, SentechSDK, `.stprofile`, device ocupado pelo StViewer.

## Logs

Os logs ficam em **`logs/pxmm_cam.log`** (rotação automática, ~2 MB por arquivo). Erros do launcher (.app): **`logs/launcher_error.log`**.

## Sentech (StApi / stapipy)

A câmera industrial abre com Sentech StApi: `initialize` → `create_system` → `create_first_device` → datastream → acquire. Sem Harvester, sem `libstgentl.cti` no caminho de produção, sem `gige://`.

Feche o StViewer antes de conectar. `close`/stop da aquisição corre no thread do `CaptureWorker` (não na UI).
