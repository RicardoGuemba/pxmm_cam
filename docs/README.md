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
- Para GigE via Harvester: `harvester-core` e um **GenTL Producer** do fabricante (arquivo `.cti`)

## Instalação

```bash
cd Pxmm_CAM
pip install -e .
# ou: pip install -r requirements.txt
# GigE (opcional): pip install harvester-core  ou  pip install -e ".[gige]"
```

## Configuração

Edite **`config.yaml`** na raiz do projeto:

- **streaming.source_type**: `usb` ou `gige`
- **streaming.usb_camera_index**: índice da câmera USB (0, 1, …)
- **streaming.gige_ip**, **streaming.gige_port**: IP e porta para GigE
- **streaming.gige_backend**: `auto` | `harvester` | `gstreamer` | `opencv`
- **streaming.gentl_producer_path**: caminho do GenTL Producer (necessário para Harvester)

Validação é feita com Pydantic; mensagens de erro indicam campos inválidos.

## Uso

1. **Operação**: escolha Fonte (USB ou GigE). Para USB informe o índice; para GigE informe IP, porta e backend. Clique em **Conectar**. O preview e o FPS aparecem na barra de status.
2. **Medição**: no vídeo, clique em dois pontos (A e B). Informe a distância real em mm no diálogo. A escala px/mm e mm/px é calculada e a medição entra no histórico.
3. **Exportar**: use o botão **Exportar** para salvar o histórico em CSV ou JSON (schema fixo).
4. **Diagnóstico**: em falha de conexão GigE, use **Abrir Diagnóstico** ou a aba **Diagnóstico** para verificar SO, Python, OpenCV, GStreamer, Harvester e GenTL.

## Logs

Os logs ficam em **`logs/pxmm_cam.log`** (rotação automática, ~2 MB por arquivo). Erros do launcher (.app): **`logs/launcher_error.log`**.

## GigE – backends

- **Auto**: tenta Harvester (se `gentl_producer_path` configurado), depois GStreamer (se OpenCV tiver suporte), depois OpenCV.
- **Harvester**: exige GenTL Producer do fabricante; configure `gentl_producer_path` no `config.yaml`.
- **GStreamer**: exige OpenCV compilado com GStreamer (aba Diagnóstico mostra sim/não).
- **OpenCV**: fallback com `gige://` ou URL HTTP; depende de drivers/SDK do fabricante.

Em caso de falha, as mensagens orientam e a aba Diagnóstico ajuda a checar o ambiente.
