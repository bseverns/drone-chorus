"""PyQt6 front-end for the MSP→MIDI bridge.

The GUI is intentionally chatty: every control is labeled with intent, and the
panels are arranged so pilots can watch telemetry become MIDI in real time.
Think of this as the lab notebook version of :mod:`msp_to_midi`—you can read the
code and immediately see which knobs the on-screen widgets are twiddling.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets
from serial.tools import list_ports
import mido

from gui_backend import BridgeBackend, BridgeStatus

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent.parent
DEFAULT_CONFIG = ROOT_DIR / "config" / "multi.yaml"
PRESETS_DIR = ROOT_DIR / "presets"


class StatusRelay(QtCore.QObject):
    status_ready = QtCore.pyqtSignal(object)

    def push(self, status: BridgeStatus) -> None:
        self.status_ready.emit(status)


class HeartbeatWidget(QtWidgets.QWidget):
    """Little LED that pulses when CC bursts are emitted."""

    def __init__(self) -> None:
        super().__init__()
        self._last_ts = 0.0
        self.setFixedSize(24, 24)

    def update_heartbeat(self, ts: float) -> None:
        self._last_ts = ts
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # pragma: no cover - UI paint
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        now = time.time()
        elapsed = now - self._last_ts if self._last_ts else 999
        intensity = 0.2 if elapsed > 1.5 else max(0.2, 1.0 - elapsed / 1.5)
        color = QtGui.QColor.fromHsl(120, 255, int(120 * intensity + 50))
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(self.rect().adjusted(2, 2, -2, -2))


class YamlHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, document: QtGui.QTextDocument) -> None:
        super().__init__(document)
        key_format = QtGui.QTextCharFormat()
        key_format.setForeground(QtGui.QColor("#ff66cc"))
        self.rules = [(QtCore.QRegularExpression(r"^[\s\-]*[\w]+:"), key_format)]
        number_format = QtGui.QTextCharFormat()
        number_format.setForeground(QtGui.QColor("#7dd3fc"))
        self.rules.append((QtCore.QRegularExpression(r"[-+]?[0-9]*\.?[0-9]+"), number_format))

    def highlightBlock(self, text: str) -> None:  # pragma: no cover - GUI
        for pattern, fmt in self.rules:
            for match in pattern.globalMatch(text):
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Drone Chorus MSP Control")
        self.backend = BridgeBackend()
        self.relay = StatusRelay()
        self.backend.set_state_callback(self.relay.push)
        self.relay.status_ready.connect(self.on_status)
        self.config_watcher = QtCore.QFileSystemWatcher()
        self.config_watcher.fileChanged.connect(self.on_config_changed)
        self.current_config = DEFAULT_CONFIG
        self.current_norm = None

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        layout.addLayout(self._build_top_bar())
        layout.addWidget(self._build_monitor_panel())
        layout.addWidget(self._build_config_editor())
        layout.addWidget(self._build_footer())

        self.serial_timer = QtCore.QTimer(self)
        self.serial_timer.timeout.connect(self.refresh_serial_ports)
        self.serial_timer.start(2000)

        self.midi_timer = QtCore.QTimer(self)
        self.midi_timer.timeout.connect(self.refresh_midi_ports)
        self.midi_timer.start(2000)

        self.ui_refresh = QtCore.QTimer(self)
        self.ui_refresh.timeout.connect(self._throttle_updates)
        self.ui_refresh.start(30)  # ~33 Hz for lightweight UI churn

        self.load_config(self.current_config)
        self.refresh_serial_ports()
        self.refresh_midi_ports()

    # --- UI construction -------------------------------------------------
    def _build_top_bar(self) -> QtWidgets.QLayout:
        layout = QtWidgets.QHBoxLayout()
        self.serial_combo = QtWidgets.QComboBox()
        layout.addWidget(QtWidgets.QLabel("Serial Port"))
        layout.addWidget(self.serial_combo)

        self.midi_combo = QtWidgets.QComboBox()
        layout.addWidget(QtWidgets.QLabel("MIDI Out"))
        layout.addWidget(self.midi_combo)

        self.sim_toggle = QtWidgets.QCheckBox("Debug Simulator")
        layout.addWidget(self.sim_toggle)

        self.start_btn = QtWidgets.QPushButton("Start Bridge")
        self.start_btn.clicked.connect(self.start_bridge)
        layout.addWidget(self.start_btn)

        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.stop_btn.clicked.connect(self.backend.stop)
        layout.addWidget(self.stop_btn)

        return layout

    def _build_monitor_panel(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Live MIDI Monitor")
        layout = QtWidgets.QVBoxLayout(box)
        header = QtWidgets.QHBoxLayout()
        header.addWidget(QtWidgets.QLabel("Heartbeat"))
        self.heartbeat = HeartbeatWidget()
        header.addWidget(self.heartbeat)
        header.addStretch()
        layout.addLayout(header)

        self.monitor = QtWidgets.QTreeWidget()
        self.monitor.setColumnCount(4)
        self.monitor.setHeaderLabels(["Drone", "Control", "CC", "Value"])
        layout.addWidget(self.monitor)
        return box

    def _build_config_editor(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Config + Presets")
        layout = QtWidgets.QVBoxLayout(box)

        preset_bar = QtWidgets.QHBoxLayout()
        preset_bar.addWidget(QtWidgets.QLabel("Preset:"))
        self.preset_combo = QtWidgets.QComboBox()
        preset_bar.addWidget(self.preset_combo)
        self.reload_presets()
        self.load_preset_btn = QtWidgets.QPushButton("Load Preset")
        self.load_preset_btn.clicked.connect(self.load_selected_preset)
        preset_bar.addWidget(self.load_preset_btn)
        layout.addLayout(preset_bar)

        path_bar = QtWidgets.QHBoxLayout()
        self.config_path = QtWidgets.QLineEdit(str(self.current_config))
        path_bar.addWidget(self.config_path)
        browse = QtWidgets.QPushButton("Browse…")
        browse.clicked.connect(self.pick_config)
        path_bar.addWidget(browse)
        layout.addLayout(path_bar)

        control_bar = QtWidgets.QHBoxLayout()
        self.unlock_toggle = QtWidgets.QCheckBox("Unlock editor")
        self.unlock_toggle.toggled.connect(self.toggle_editable)
        control_bar.addWidget(self.unlock_toggle)
        self.save_btn = QtWidgets.QPushButton("Save YAML")
        self.save_btn.clicked.connect(self.save_config)
        control_bar.addWidget(self.save_btn)
        layout.addLayout(control_bar)

        self.config_view = QtWidgets.QPlainTextEdit()
        self.config_view.setReadOnly(True)
        self.config_view.setMinimumHeight(180)
        self.highlighter = YamlHighlighter(self.config_view.document())
        layout.addWidget(self.config_view)

        self.status_label = QtWidgets.QLabel("Idle")
        layout.addWidget(self.status_label)
        return box

    def _build_footer(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Extras")
        layout = QtWidgets.QHBoxLayout(box)

        self.webmidi_toggle = QtWidgets.QCheckBox("WebMIDI preview server")
        self.webmidi_toggle.toggled.connect(self.backend.toggle_web_stream)
        layout.addWidget(self.webmidi_toggle)

        layout.addStretch()
        return box

    # --- Actions ---------------------------------------------------------
    def reload_presets(self) -> None:
        self.preset_combo.clear()
        if PRESETS_DIR.exists():
            for path in sorted(PRESETS_DIR.glob("*.yaml")):
                self.preset_combo.addItem(path.name, path)

    def load_selected_preset(self) -> None:
        path = self.preset_combo.currentData()
        if path:
            self.config_path.setText(str(path))
            self.load_config(path)

    def pick_config(self) -> None:
        file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select YAML", str(ROOT_DIR), "YAML Files (*.yaml *.yml)"
        )
        if file:
            self.config_path.setText(file)
            self.load_config(Path(file))

    def toggle_editable(self, checked: bool) -> None:
        self.config_view.setReadOnly(not checked)

    def save_config(self) -> None:
        path = Path(self.config_path.text())
        path.write_text(self.config_view.toPlainText(), encoding="utf-8")
        self.status_label.setText(f"Saved {path}")
        if path.exists():
            self.config_watcher.addPath(str(path))

    def start_bridge(self) -> None:
        try:
            norm = self.backend.load_config(Path(self.config_path.text()))
            self.current_norm = norm
            self.backend.start(
                serial_port=self.serial_combo.currentText(),
                midi_port=self.midi_combo.currentText(),
                norm=norm,
                simulated=self.sim_toggle.isChecked(),
            )
            self.status_label.setText("Bridge running")
        except Exception as exc:  # pragma: no cover - UI path
            self.status_label.setText(f"Error: {exc}")

    def load_config(self, path: Path) -> None:
        try:
            norm = self.backend.load_config(path)
            self.current_norm = norm
            self.config_view.setPlainText(path.read_text(encoding="utf-8"))
            self.status_label.setText(f"Loaded {path}")
            self.config_path.setText(str(path))
            self.config_watcher.addPath(str(path))
            if self.backend:
                self.backend.reload_config(norm)
        except Exception as exc:
            self.status_label.setText(f"Config error: {exc}")

    def on_config_changed(self, path: str) -> None:
        self.load_config(Path(path))

    def refresh_serial_ports(self) -> None:
        current = self.serial_combo.currentText()
        ports = [p.device for p in list_ports.comports()]
        self.serial_combo.blockSignals(True)
        self.serial_combo.clear()
        self.serial_combo.addItems(ports)
        idx = self.serial_combo.findText(current)
        if idx >= 0:
            self.serial_combo.setCurrentIndex(idx)
        self.serial_combo.blockSignals(False)

    def refresh_midi_ports(self) -> None:
        current = self.midi_combo.currentText()
        outputs = mido.get_output_names()
        self.midi_combo.blockSignals(True)
        self.midi_combo.clear()
        self.midi_combo.addItems(outputs)
        idx = self.midi_combo.findText(current)
        if idx >= 0:
            self.midi_combo.setCurrentIndex(idx)
        self.midi_combo.blockSignals(False)

    def _throttle_updates(self) -> None:
        # noop placeholder to keep a steady UI cadence for future animations
        pass

    def on_status(self, status: BridgeStatus) -> None:
        if status.heartbeat_ts:
            self.heartbeat.update_heartbeat(status.heartbeat_ts)
        self.refresh_monitor(status.cc_values)

    def refresh_monitor(self, cc_values: dict) -> None:
        self.monitor.setUpdatesEnabled(False)
        self.monitor.clear()
        for drone, controls in cc_values.items():
            for control, value in sorted(controls.items()):
                item = QtWidgets.QTreeWidgetItem(
                    [drone, self._control_name(control), str(control), str(value)]
                )
                self.monitor.addTopLevelItem(item)
        self.monitor.setUpdatesEnabled(True)

    @staticmethod
    def _control_name(control: int) -> str:
        labels = {
            14: "roll",
            15: "pitch",
            16: "yaw",
            17: "altitude",
            18: "rssi",
            19: "vbat",
            20: "throttle",
            64: "gate",
        }
        return labels.get(control, "cc")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.resize(960, 720)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
