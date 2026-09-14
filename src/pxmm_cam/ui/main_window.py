"""Main window: Operation and Diagnosis tabs, video, connect/disconnect, measurement, export."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)

from pxmm_cam.config import (
    load_config,
    AppConfig,
    StreamingConfig,
    UIConfig,
    ExportConfig,
)
from pxmm_cam.streaming import (
    create_frame_source,
    CaptureWorker,
    detect_usb_camera_indices,
)
from pxmm_cam.streaming.frame_source import FrameSource
from pxmm_cam.measurement import distance_px, CalibrationState
from pxmm_cam.measurement.record import MeasurementRecord
from pxmm_cam.persistence import MeasurementHistory, export_csv, export_json
from .video_widget import VideoWidget
from .mm_dialog import MmDialog

logger = logging.getLogger(__name__)

# Tab indices
TAB_OPERATION = 0
TAB_DIAGNOSTIC = 1


class MainWindow(QMainWindow):
    """Main window with Operation and Diagnosis tabs, video, connect/disconnect, measurement, export."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pxmm CAM")
        self.setMinimumSize(640, 480)
        screen = QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            self.setGeometry(avail)
        else:
            self.resize(1280, 800)

        self._config: Optional[AppConfig] = None
        self._source: Optional[FrameSource] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[CaptureWorker] = None
        self._history = MeasurementHistory()
        self._calibration = CalibrationState()
        self._pending_points: List[Tuple[float, float]] = []

        self._load_config()

        self._video = VideoWidget()
        self._video.point_clicked.connect(self._on_point_clicked)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(2)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.addTab(self._build_operation_tab(), "Operação")
        self._tabs.addTab(self._build_diagnostic_tab(), "Diagnóstico")
        layout.addWidget(self._tabs)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Desconectado")

    def _load_config(self) -> None:
        try:
            self._config = load_config()
        except FileNotFoundError as e:
            logger.warning("Config não encontrado: %s. Usando defaults.", e)
            self._config = AppConfig()
        except Exception as e:
            logger.exception("Erro ao carregar config: %s", e)
            self._config = AppConfig()

    def _build_operation_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        bar = QWidget()
        bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(6)

        bar_layout.addWidget(QLabel("Fonte:"))
        self._source_combo = QComboBox()
        self._source_combo.addItems(["USB (entrada USB)", "GigE/LAN (Ethernet)"])
        self._source_combo.setMinimumWidth(160)
        self._source_combo.currentTextChanged.connect(self._on_source_type_changed)
        bar_layout.addWidget(self._source_combo)

        self._usb_index_label = QLabel("USB:")
        self._usb_camera_combo = QComboBox()
        self._usb_camera_combo.setMinimumWidth(140)
        self._usb_camera_combo.setToolTip(
            "Apenas câmera conectada na porta USB. Use Detectar para listar."
        )
        self._usb_camera_combo.addItem("Detectar câmera USB", -1)
        self._detect_usb_btn = QPushButton("Detectar")
        self._detect_usb_btn.clicked.connect(self._on_detect_usb_cameras)
        bar_layout.addWidget(self._usb_index_label)
        bar_layout.addWidget(self._usb_camera_combo)
        bar_layout.addWidget(self._detect_usb_btn)

        self._gige_widget = QWidget()
        gige_layout = QHBoxLayout(self._gige_widget)
        gige_layout.setContentsMargins(0, 0, 0, 0)
        gige_layout.setSpacing(4)
        gige_layout.addWidget(QLabel("IP:"))
        self._gige_ip_edit = QLineEdit()
        self._gige_ip_edit.setPlaceholderText("192.168.1.10")
        self._gige_ip_edit.setMaximumWidth(140)
        self._gige_ip_edit.setText(self._config.streaming.gige_ip if self._config else "")
        gige_layout.addWidget(self._gige_ip_edit)
        self._gige_widget.setVisible(False)
        bar_layout.addWidget(self._gige_widget)

        # Legado: snapshot ainda lê porta/backend, sem ocupar a área de vídeo.
        self._gige_port_spin = QSpinBox()
        self._gige_port_spin.setRange(1, 65535)
        self._gige_port_spin.setValue(self._config.streaming.gige_port if self._config else 3956)
        self._gige_port_spin.hide()
        self._gige_backend_combo = QComboBox()
        self._gige_backend_combo.addItems(["auto", "harvester", "gstreamer", "opencv"])
        self._gige_backend_combo.hide()

        bar_layout.addStretch(1)
        self._connect_btn = QPushButton("Conectar")
        self._connect_btn.clicked.connect(self._on_connect)
        self._disconnect_btn = QPushButton("Desconectar")
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        self._disconnect_btn.setEnabled(False)
        self._clear_pts_btn = QPushButton("Limpar pontos")
        self._clear_pts_btn.clicked.connect(self._on_clear_points)
        self._export_btn = QPushButton("Exportar")
        self._export_btn.clicked.connect(self._on_export)
        for btn in (
            self._connect_btn,
            self._disconnect_btn,
            self._clear_pts_btn,
            self._export_btn,
        ):
            bar_layout.addWidget(btn)

        layout.addWidget(bar, 0)

        self._video.setMinimumSize(320, 200)
        self._video.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        layout.addWidget(self._video, 1)

        self._history_table = QTableWidget()
        self._history_table.setColumnCount(6)
        self._history_table.setHorizontalHeaderLabels([
            "Data/Hora", "Fonte", "px", "mm", "px/mm", "mm/px",
        ])
        self._history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._history_table.verticalHeader().setVisible(False)
        self._history_table.setMaximumHeight(72)
        self._history_table.setMinimumHeight(48)
        self._history_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        layout.addWidget(self._history_table, 0)

        if self._config and self._config.streaming.source_type == "stapipy":
            self._source_combo.setCurrentIndex(1)

        return tab

    def _build_diagnostic_tab(self) -> QWidget:
        from .diagnostic_tab import DiagnosticTab
        return DiagnosticTab(self)

    def _get_usb_camera_index(self) -> int:
        """Índice da câmera USB selecionada no combo; -1 se ainda não detectou."""
        val = self._usb_camera_combo.currentData()
        if val is None or val < 0:
            return -1
        return int(val)

    def _on_source_type_changed(self, text: str) -> None:
        if not hasattr(self, "_gige_widget"):
            return
        is_gige = "GigE" in text or "LAN" in text or "Ethernet" in text
        self._gige_widget.setVisible(is_gige)
        self._usb_index_label.setVisible(not is_gige)
        self._usb_camera_combo.setVisible(not is_gige)
        self._detect_usb_btn.setVisible(not is_gige)

    def _on_detect_usb_cameras(self) -> None:
        """Lista apenas câmeras USB externas (entrada USB). Webcam não é listada."""
        indices = detect_usb_camera_indices(usb_only=True)
        self._usb_camera_combo.clear()
        if not indices:
            self._usb_camera_combo.addItem("Nenhuma câmera USB encontrada", -1)
            QMessageBox.information(
                self,
                "Entrada USB",
                "Nenhuma câmera na porta USB. Conecte a câmera USB e clique em Detectar.",
            )
            return
        for idx in indices:
            self._usb_camera_combo.addItem(f"Câmera USB (entrada {idx})", idx)
        self._usb_camera_combo.setCurrentIndex(0)
        self._status_bar.showMessage(f"Câmera USB detectada. Conecte para iniciar o streaming.")

    def _get_current_config_snapshot(self) -> AppConfig:
        """Build config from current UI (for connect)."""
        source_type = (
            "stapipy"
            if "GigE" in self._source_combo.currentText() or "LAN" in self._source_combo.currentText()
            else "usb"
        )
        usb_idx = max(0, self._get_usb_camera_index())
        streaming_cfg = self._config.streaming if self._config else None
        return AppConfig(
            streaming=StreamingConfig(
                source_type=source_type,
                usb_camera_index=usb_idx,
                device_index=streaming_cfg.device_index if streaming_cfg else 0,
                fetch_timeout_ms=streaming_cfg.fetch_timeout_ms if streaming_cfg else 400,
                gige_ip=self._gige_ip_edit.text().strip(),
                gige_port=self._gige_port_spin.value(),
                requested_width=streaming_cfg.requested_width if streaming_cfg else None,
                requested_height=streaming_cfg.requested_height if streaming_cfg else None,
                target_fps=streaming_cfg.target_fps if streaming_cfg else None,
            ),
            ui=UIConfig(auto_export=self._config.ui.auto_export if self._config else False),
            export=ExportConfig(default_dir=self._config.export.default_dir if self._config else ""),
        )

    def _on_connect(self) -> None:
        config = self._get_current_config_snapshot()
        if config.streaming.source_type == "usb" and self._get_usb_camera_index() < 0:
            QMessageBox.warning(
                self,
                "Entrada USB",
                "Clique em 'Detectar câmera USB' e depois em Conectar.",
            )
            return
        self._connect_btn.setEnabled(False)
        self._status_bar.showMessage("Conectando...")
        QApplication.processEvents()
        try:
            self._source = create_frame_source(config)
            self._worker = CaptureWorker(self._source)
            self._thread = QThread()
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.run)
            self._worker.frame_ready.connect(
                self._on_frame_ready,
                Qt.ConnectionType.QueuedConnection,
            )
            self._worker.error_occurred.connect(self._on_capture_error)
            self._worker.finished.connect(self._on_capture_finished)
            self._worker.start_capture()
            self._thread.start()
            self._disconnect_btn.setEnabled(True)
            self._status_bar.showMessage("Conectando... (aguarde o primeiro frame)")
        except Exception as e:
            logger.exception("Erro ao conectar: %s", e)
            self._connect_btn.setEnabled(True)
            self._status_bar.showMessage("Erro ao conectar")
            self._show_gige_error_and_diagnostic(str(e))
            self._source = None
            self._worker = None
            self._thread = None

    def _on_frame_ready(self, frame: object, fps: float) -> None:
        # Cópia do frame na thread principal para não reutilizar buffer da captura
        if frame is not None and hasattr(frame, "copy"):
            frame = frame.copy()
        self._video.set_frame(frame)
        if self._source:
            backend = self._source.get_status().backend
            self._status_bar.showMessage(f"Conectado | {backend} | FPS: {fps:.1f}")

    def _on_capture_error(self, message: str) -> None:
        logger.error("Capture error: %s", message)
        self._connect_btn.setEnabled(True)
        self._disconnect_btn.setEnabled(False)
        self._status_bar.showMessage("Erro: " + message)
        self._stop_capture()
        self._set_diagnostic_last_error(message)
        if self._source_combo.currentText() == "GigE":
            self._show_gige_error_and_diagnostic(message)

    def _set_diagnostic_last_error(self, message: str) -> None:
        diag = self._tabs.widget(TAB_DIAGNOSTIC)
        if hasattr(diag, "set_last_error"):
            diag.set_last_error(message)

    def _refresh_history_table(self) -> None:
        self._history_table.setRowCount(0)
        for r in self._history.records():
            row = self._history_table.rowCount()
            self._history_table.insertRow(row)
            self._history_table.setItem(row, 0, QTableWidgetItem(r.timestamp.strftime("%Y-%m-%d %H:%M:%S")))
            self._history_table.setItem(row, 1, QTableWidgetItem(f"{r.source_type} {r.source_id}"))
            self._history_table.setItem(row, 2, QTableWidgetItem(f"{r.distance_px:.2f}"))
            self._history_table.setItem(row, 3, QTableWidgetItem(f"{r.distance_mm}" if r.distance_mm is not None else ""))
            self._history_table.setItem(row, 4, QTableWidgetItem(f"{r.scale_px_per_mm:.4f}" if r.scale_px_per_mm is not None else ""))
            self._history_table.setItem(row, 5, QTableWidgetItem(f"{r.scale_mm_per_px:.6f}" if r.scale_mm_per_px is not None else ""))

    def _show_gige_error_and_diagnostic(self, message: str) -> None:
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Falha na conexão GigE")
        msg.setText(message)
        msg.setInformativeText(
            "Use a aba Diagnóstico (stapipy, SentechSDK, .stprofile). "
            "Feche o StViewer se a câmera estiver ocupada."
        )
        open_diag = msg.addButton("Abrir Diagnóstico", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Ok)
        msg.exec()
        if msg.clickedButton() == open_diag:
            self._tabs.setCurrentIndex(TAB_DIAGNOSTIC)

    def _on_capture_finished(self) -> None:
        self._stop_capture()
        self._connect_btn.setEnabled(True)
        self._disconnect_btn.setEnabled(False)
        self._status_bar.showMessage("Desconectado")

    def _stop_capture(self) -> None:
        if self._worker:
            self._worker.stop_capture()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        if self._source:
            try:
                self._source.close()
            except Exception:
                pass
            self._source = None
        self._worker = None
        self._thread = None

    def _on_disconnect(self) -> None:
        self._on_capture_finished()

    def _on_clear_points(self) -> None:
        self._video.clear_points()
        self._pending_points.clear()

    def _on_point_clicked(self, x: float, y: float) -> None:
        self._pending_points.append((x, y))
        self._video.set_points(self._pending_points)
        if len(self._pending_points) == 2:
            dist_px = distance_px(self._pending_points[0], self._pending_points[1])
            dlg = MmDialog(self, dist_px)
            if dlg.exec() == MmDialog.DialogCode.Accepted:
                mm = dlg.get_mm()
                if mm is not None and mm > 0:
                    self._calibration.set_from_measurement(dist_px, mm)
                    source_type = "gige" if "GigE" in self._source_combo.currentText() or "LAN" in self._source_combo.currentText() else "usb"
                    sid = self._get_usb_camera_index()
                    source_id = self._gige_ip_edit.text().strip() if source_type == "gige" else str(max(0, sid))
                    record = MeasurementRecord(
                        timestamp=datetime.now(),
                        source_type=source_type,
                        source_id=source_id,
                        point_a=self._pending_points[0],
                        point_b=self._pending_points[1],
                        distance_px=dist_px,
                        distance_mm=mm,
                        scale_px_per_mm=self._calibration.scale_px_per_mm,
                        scale_mm_per_px=self._calibration.scale_mm_per_px,
                    )
                    self._history.add(record)
                    self._refresh_history_table()
            self._pending_points.clear()
            self._video.set_points([])

    def _on_export(self) -> None:
        records = self._history.records()
        if not records:
            QMessageBox.information(self, "Exportar", "Nenhuma medição no histórico.")
            return
        default_dir = (self._config.export.default_dir if self._config else "") or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar medições",
            default_dir,
            "CSV (*.csv);;JSON (*.json);;Todos (*.*)",
        )
        if not path:
            return
        path = Path(path)
        try:
            if path.suffix.lower() == ".json":
                export_json(records, path)
            else:
                export_csv(records, path)
            QMessageBox.information(self, "Exportar", f"Exportado: {path}")
        except Exception as e:
            logger.exception("Erro ao exportar: %s", e)
            QMessageBox.critical(self, "Exportar", f"Erro: {e}")

    def closeEvent(self, event) -> None:
        self._on_disconnect()
        event.accept()