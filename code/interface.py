from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Callable

import cv2
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from drone import AppConfig, DetectionResult, DetectorEngine, VideoSource

try:
    from motor import DCMotorController
except Exception:  # pragma: no cover
    DCMotorController = None

try:
    from servo import TiltServoController
except Exception:  # pragma: no cover
    TiltServoController = None


WORKSPACE = Path(__file__).resolve().parent
LOG_DIR = WORKSPACE / "log"
SHOT_DIR = WORKSPACE / "shot"


def timestamp_filename() -> str:
    now = datetime.now()
    return f"{now.year}-{now.month}-{now.day} {now.hour:02d}-{now.minute:02d}"


class RockerSwitch(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_mode = "Mode 1"
        self.setFixedSize(96, 220)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_mode(self, mode: str) -> None:
        self.current_mode = mode
        self.update()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            mode = "Mode 1" if event.position().y() <= self.height() / 2 else "Mode 2"
            self.clicked.emit(mode)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        outer = QRectF(18, 20, self.width() - 36, self.height() - 40)
        painter.setPen(QPen(QColor("#5e5e5e"), 2))
        painter.setBrush(QColor("#d7d7d7"))
        painter.drawRoundedRect(outer, 24, 24)

        groove = outer.adjusted(6, 6, -6, -6)
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
        painter.setBrush(QColor("#c6c6c6"))
        painter.drawRoundedRect(groove, 20, 20)

        if self.current_mode == "Mode 1":
            rocker = QRectF(groove.left() + 4, groove.top() + 4, groove.width() - 8, groove.height() / 2 - 6)
        else:
            rocker = QRectF(groove.left() + 4, groove.center().y() + 2, groove.width() - 8, groove.height() / 2 - 6)

        rocker_path = QPainterPath()
        rocker_path.addRoundedRect(rocker, 18, 18)
        painter.fillPath(rocker_path, QColor("#efefef"))
        painter.setPen(QPen(QColor("#6b6b6b"), 2))
        painter.drawRoundedRect(rocker, 18, 18)

        painter.setPen(QPen(QColor("#262626"), 1))
        painter.drawText(QRectF(0, 0, self.width(), 24), Qt.AlignmentFlag.AlignCenter, "Mode 1")
        painter.drawText(QRectF(0, self.height() - 24, self.width(), 24), Qt.AlignmentFlag.AlignCenter, "Mode 2")


class MediaButton(QToolButton):
    def __init__(self, icon_type: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icon_type = icon_type
        self.setFixedSize(66, 66)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QToolButton { background: transparent; border: none; }")

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(3, 3, self.width() - 6, self.height() - 6)
        painter.setPen(QPen(QColor("#202020"), 2))
        painter.setBrush(QColor("#111111") if not self.isDown() else QColor("#1b1b1b"))
        painter.drawEllipse(rect)

        highlight = QPainterPath()
        highlight.moveTo(rect.left() + 4, rect.center().y() + 2)
        highlight.quadTo(rect.center().x(), rect.top() + 6, rect.right() - 4, rect.top() + 18)
        highlight.lineTo(rect.right() - 4, rect.top() + 4)
        highlight.lineTo(rect.left() + 12, rect.top() + 4)
        highlight.closeSubpath()
        painter.fillPath(highlight, QColor(255, 255, 255, 38))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        self._draw_icon(painter, rect)

    def _draw_icon(self, painter: QPainter, rect: QRectF) -> None:
        if self.icon_type == "play":
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(rect.left() + 22, rect.top() + 16),
                        QPointF(rect.left() + 22, rect.bottom() - 16),
                        QPointF(rect.right() - 18, rect.center().y()),
                    ]
                )
            )
        elif self.icon_type == "pause":
            painter.drawRoundedRect(QRectF(rect.left() + 18, rect.top() + 15, 8, rect.height() - 30), 4, 4)
            painter.drawRoundedRect(QRectF(rect.right() - 26, rect.top() + 15, 8, rect.height() - 30), 4, 4)
        elif self.icon_type == "stop":
            painter.drawRect(QRectF(rect.left() + 18, rect.top() + 18, rect.width() - 36, rect.height() - 36))


class MockPanTiltController:
    def __init__(self, tilt_limit: float) -> None:
        self.pan_angle = 0.0
        self.tilt_angle = 0.0
        self.tilt_limit = tilt_limit
        self.hardware_enabled = False

    def pan_by(self, delta: float) -> None:
        self.pan_angle += delta

    def tilt_by(self, delta: float) -> None:
        self.tilt_angle = max(-self.tilt_limit, min(self.tilt_limit, self.tilt_angle + delta))

    def set_tilt(self, angle: float) -> None:
        self.tilt_angle = max(-self.tilt_limit, min(self.tilt_limit, angle))

    def close(self) -> None:
        return


class HardwarePanTiltController:
    def __init__(self, tilt_limit: float) -> None:
        self.tilt_limit = tilt_limit
        self.pan_angle = 0.0
        self.tilt_angle = 0.0
        self.pan_motor = None
        self.tilt_servo = None
        self.hardware_enabled = False

        if DCMotorController is not None and TiltServoController is not None:
            try:
                self.pan_motor = DCMotorController(in1_pin=17, in2_pin=27, default_speed=38)
                self.tilt_servo = TiltServoController(pin=12, zero_offset=90)
                self.hardware_enabled = True
            except Exception:
                self.pan_motor = None
                self.tilt_servo = None

    def pan_by(self, delta: float) -> None:
        self.pan_angle += delta
        if self.pan_motor is not None and delta != 0:
            self.pan_motor.rotate(delta, speed=38)

    def tilt_by(self, delta: float) -> None:
        self.set_tilt(self.tilt_angle + delta)

    def set_tilt(self, angle: float) -> None:
        self.tilt_angle = max(-self.tilt_limit, min(self.tilt_limit, angle))
        if self.tilt_servo is not None:
            self.tilt_servo.set_relative_angle(self.tilt_angle)

    def close(self) -> None:
        if self.pan_motor is not None:
            self.pan_motor.close()
        if self.tilt_servo is not None:
            self.tilt_servo.close()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig()
        self.detector = DetectorEngine(self.config)
        self.video_source = VideoSource()
        self.controller = self._build_controller()
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._update_frame)

        self.current_mode = "Mode 1"
        self.camera_connected = False
        self.pipeline_running = False
        self.drone_detected = False
        self.auto_tracking_enabled = False
        self.detection_enabled = False
        self.current_frame = None
        self.current_detection: DetectionResult | None = None
        self.logs: list[dict[str, str | float | int]] = []

        self.setWindowTitle("即時無人機辨識與追蹤")
        self.resize(1500, 980)

        self._build_central_widget()
        self._build_status_bar()
        self._refresh_mode_tabs()
        self._refresh_mode_page()
        self._refresh_indicators()
        self._refresh_controller_labels()
        self._render_placeholder("尚未啟動影像來源")

    def _build_controller(self):
        hardware = HardwarePanTiltController(self.config.tilt_limit_deg)
        if hardware.hardware_enabled:
            return hardware
        return MockPanTiltController(self.config.tilt_limit_deg)

    def _build_central_widget(self) -> None:
        container = QWidget()
        container.setStyleSheet("background: #f7f7f7;")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 18, 22, 18)
        layout.setSpacing(26)
        layout.addWidget(self._build_mode_panel(), alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._build_center_stack(), stretch=1)
        layout.addWidget(self._build_status_panel(), alignment=Qt.AlignmentFlag.AlignTop)
        self.setCentralWidget(container)

    def _build_mode_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(120)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 120, 0, 0)
        layout.setSpacing(18)

        self.mode_switch = RockerSwitch()
        self.mode_switch.clicked.connect(self._set_mode)

        layout.addWidget(self.mode_switch, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        return panel

    def _build_center_stack(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self._build_mode1_page())
        self.mode_stack.addWidget(self._build_mode2_page())
        layout.addWidget(self.mode_stack)
        return wrapper

    def _build_mode1_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title = QLabel("影片路徑")
        title.setStyleSheet("font-size: 34px; font-weight: 700; color: #262626;")

        row = QHBoxLayout()
        row.setSpacing(12)

        self.mode1_path_input = QLineEdit()
        self.mode1_path_input.setPlaceholderText("請輸入影片檔案路徑")
        self.mode1_path_input.setText(str(WORKSPACE / "demo.mp4"))
        self.mode1_path_input.setFixedHeight(46)
        self.mode1_path_input.setStyleSheet(self._path_input_style())

        browse_button = QPushButton("選擇")
        browse_button.setFixedSize(110, 46)
        browse_button.setStyleSheet(self._secondary_button_style())
        browse_button.clicked.connect(self._choose_video)

        open_button = QPushButton("載入影片")
        open_button.setFixedSize(132, 46)
        open_button.setStyleSheet(self._secondary_button_style())
        open_button.clicked.connect(self._open_video_from_input)

        row.addWidget(self.mode1_path_input, stretch=1)
        row.addWidget(browse_button)
        row.addWidget(open_button)

        layout.addWidget(title)
        layout.addLayout(row)
        layout.addWidget(
            self._build_video_panel(
                [
                    ("pause", self._pause_pipeline),
                    ("play", self._start_detection_pipeline),
                    ("stop", self._stop_pipeline),
                ]
            ),
            stretch=1,
        )
        return page

    def _build_mode2_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title = QLabel("即時攝影機")
        title.setStyleSheet("font-size: 34px; font-weight: 700; color: #262626;")

        tool_row = QHBoxLayout()
        tool_row.setSpacing(14)

        connect_button = QPushButton("連接攝影機")
        detect_button = QPushButton("開始偵測")
        track_button = QPushButton("開始追蹤")
        snapshot_button = QPushButton("擷取畫面")

        connect_button.clicked.connect(self._connect_camera)
        detect_button.clicked.connect(self._start_detection_pipeline)
        track_button.clicked.connect(self._start_auto_tracking)
        snapshot_button.clicked.connect(self._save_snapshot)

        for button in (connect_button, detect_button, track_button, snapshot_button):
            button.setFixedHeight(44)
            button.setStyleSheet(self._secondary_button_style())
            tool_row.addWidget(button)
        tool_row.addStretch()

        layout.addWidget(title)
        layout.addLayout(tool_row)
        layout.addWidget(self._build_manual_control_group())
        layout.addWidget(self._build_preview_panel(), stretch=1)
        return page

    def _build_manual_control_group(self) -> QWidget:
        box = QFrame()
        box.setStyleSheet("QFrame { background: #ffffff; border: 2px solid #dbe7ff; }")

        layout = QHBoxLayout(box)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(24)

        title = QLabel("手動控制")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #1f1f1f;")

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        up_button = self._make_control_button("上", lambda: self._manual_tilt(-self.config.tilt_step_deg))
        down_button = self._make_control_button("下", lambda: self._manual_tilt(self.config.tilt_step_deg))
        left_button = self._make_control_button("左", lambda: self._manual_pan(-self.config.pan_step_deg))
        right_button = self._make_control_button("右", lambda: self._manual_pan(self.config.pan_step_deg))
        center_button = self._make_control_button("置中", self._reset_pan_tilt)

        grid.addWidget(up_button, 0, 1)
        grid.addWidget(left_button, 1, 0)
        grid.addWidget(center_button, 1, 1)
        grid.addWidget(right_button, 1, 2)
        grid.addWidget(down_button, 2, 1)

        info_layout = QVBoxLayout()
        self.pan_label = QLabel()
        self.tilt_label = QLabel()
        self.backend_label = QLabel()
        self.target_label = QLabel()
        for label in (self.pan_label, self.tilt_label, self.backend_label, self.target_label):
            label.setStyleSheet("font-size: 18px; color: #374151;")
            info_layout.addWidget(label)

        layout.addWidget(title)
        layout.addLayout(grid)
        layout.addLayout(info_layout)
        layout.addStretch()
        return box

    def _make_control_button(self, text: str, callback: Callable[[], None]) -> QPushButton:
        button = QPushButton(text)
        button.setFixedSize(76, 40)
        button.setStyleSheet(
            "QPushButton { background: #ffffff; border: 2px solid #1677ff; font-size: 18px; color: #1f1f1f; }"
            "QPushButton:hover { background: #eef6ff; }"
        )
        button.clicked.connect(callback)
        return button

    def _build_video_panel(self, controls: list[tuple[str, object]]) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet("QFrame { border: 2px solid #1677ff; background: #ffffff; }")
        panel.setFrameShape(QFrame.Shape.Box)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel.setMinimumHeight(520)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.preview_label = QLabel("影片預覽")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(0, 0)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setStyleSheet("border: none; color: #1f1f1f; font-size: 76px; font-weight: 500;")

        control_bar = QFrame()
        control_bar.setFixedHeight(90)
        control_bar.setStyleSheet(
            "QFrame { border-top: 2px solid #1677ff; border-left: none; border-right: none; border-bottom: none; background: #ffffff; }"
        )

        controls_layout = QHBoxLayout(control_bar)
        controls_layout.setContentsMargins(0, 10, 0, 10)
        controls_layout.setSpacing(16)
        controls_layout.addStretch()

        for icon_type, handler in controls:
            button = MediaButton(icon_type)
            button.clicked.connect(handler)
            controls_layout.addWidget(button)

        controls_layout.addStretch()
        layout.addWidget(self.preview_label, stretch=1)
        layout.addWidget(control_bar)
        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet("QFrame { border: 2px solid #1677ff; background: #ffffff; }")
        panel.setFrameShape(QFrame.Shape.Box)
        panel.setLineWidth(2)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel.setMinimumHeight(520)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.live_preview_label = QLabel("即時畫面")
        self.live_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live_preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.live_preview_label.setMinimumSize(0, 0)
        self.live_preview_label.setStyleSheet("border: none; color: #1f1f1f; font-size: 76px; font-weight: 500;")

        layout.addWidget(self.live_preview_label)
        return panel

    def _build_status_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(300)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 128, 0, 0)
        layout.setSpacing(32)

        camera_row, self.camera_indicator = self._build_indicator_row("攝影機連接", "#22c55e")
        running_row, self.running_indicator = self._build_indicator_row("執行中", "#2563eb")
        detect_row, self.detect_indicator = self._build_indicator_row("偵測", "#ff3b30")

        layout.addLayout(camera_row)
        layout.addLayout(running_row)
        layout.addLayout(detect_row)

        self.status_text = QLabel("等待啟動")
        self.status_text.setWordWrap(True)
        self.status_text.setStyleSheet("font-size: 18px; color: #4b5563;")
        layout.addWidget(self.status_text)

        self.center_point_label = QLabel("中心點座標: (--, --)")
        self.center_point_label.setWordWrap(True)
        self.center_point_label.setStyleSheet("font-size: 20px; color: #374151;")
        layout.addWidget(self.center_point_label)

        layout.addStretch()
        layout.addSpacing(32)

        export_button = QPushButton("Export")
        export_button.setFixedSize(150, 72)
        export_button.setStyleSheet(
            "QPushButton { background: #fff1f0; border: 2px solid #ff3b30; font-size: 34px; color: #3a2222; }"
            "QPushButton:hover { background: #ffe3e0; }"
        )
        export_button.clicked.connect(self._export_log)

        layout.addWidget(export_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(42)
        return panel

    def _build_indicator_row(self, text: str, active_color: str) -> tuple[QHBoxLayout, QLabel]:
        row = QHBoxLayout()
        row.setSpacing(16)

        dot = QLabel()
        dot.setFixedSize(42, 42)
        dot.setProperty("active_color", active_color)

        label = QLabel(text)
        label.setStyleSheet("font-size: 28px; color: #2a2a2a;")

        row.addWidget(dot)
        row.addWidget(label)
        row.addStretch()
        return row, dot

    def _path_input_style(self, border: str = "#ff3b30") -> str:
        return (
            "QLineEdit {"
            "border: none;"
            f"border-bottom: 3px solid {border};"
            "background: transparent;"
            "font-size: 20px;"
            "padding: 6px 12px;"
            "color: #1f1f1f;"
            "}"
        )

    def _secondary_button_style(self) -> str:
        return (
            "QPushButton {"
            "background: #ffffff;"
            "border: 2px solid #1677ff;"
            "font-size: 20px;"
            "padding: 8px 16px;"
            "color: #1f1f1f;"
            "}"
            "QPushButton:hover { background: #f0f7ff; }"
        )

    def _build_status_bar(self) -> None:
        status_bar = QStatusBar()
        status_bar.showMessage("系統就緒")
        self.setStatusBar(status_bar)

    def _refresh_mode_tabs(self) -> None:
        self.mode_switch.set_mode(self.current_mode)

    def _refresh_mode_page(self) -> None:
        self.mode_stack.setCurrentIndex(0 if self.current_mode == "Mode 1" else 1)

    def _refresh_indicators(self) -> None:
        self._set_indicator_state(self.camera_indicator, self.camera_connected)
        self._set_indicator_state(self.running_indicator, self.pipeline_running)
        self._set_indicator_state(self.detect_indicator, self.drone_detected)

    def _refresh_controller_labels(self) -> None:
        backend = "GPIO 硬體" if getattr(self.controller, "hardware_enabled", False) else "模擬控制"
        detector = f"{self.detector.backend_name.upper()} 偵測"
        self.pan_label.setText(f"水平角度: {self.controller.pan_angle:+.1f}°")
        self.tilt_label.setText(f"垂直角度: {self.controller.tilt_angle:+.1f}°")
        self.backend_label.setText(f"控制模式: {backend}")
        self.target_label.setText(f"辨識後端: {detector}")

        if self.current_detection is not None:
            cx, cy = self.current_detection.center
            self.center_point_label.setText(f"中心點座標: ({cx}, {cy})")
        else:
            self.center_point_label.setText("中心點座標: (--, --)")

    def _set_indicator_state(self, indicator: QLabel, active: bool) -> None:
        if active:
            color = indicator.property("active_color")
            indicator.setStyleSheet(f"border: 2px solid {color}; border-radius: 21px; background: {color};")
        else:
            indicator.setStyleSheet("border: 2px solid #8c8c8c; border-radius: 21px; background: #f5f5f5;")

    def _set_mode(self, mode: str) -> None:
        if self.current_mode != mode:
            self.frame_timer.stop()
            self.video_source.release()
            self.pipeline_running = False
            self.detection_enabled = False
            self.auto_tracking_enabled = False
            self.drone_detected = False
            self.camera_connected = False
            self.current_frame = None
            self.current_detection = None
            self._render_placeholder("尚未啟動影像來源")
        self.current_mode = mode
        self._refresh_mode_tabs()
        self._refresh_mode_page()
        self._refresh_indicators()
        self._refresh_controller_labels()
        self._set_status(f"已切換為 {mode}")

    def _set_status(self, text: str) -> None:
        self.status_text.setText(text)
        self.statusBar().showMessage(text)

    def _choose_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇影片檔",
            str(WORKSPACE),
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)",
        )
        if path:
            self.mode1_path_input.setText(path)

    def _open_video_from_input(self) -> None:
        path = self.mode1_path_input.text().strip()
        if not path:
            self._set_status("請先輸入影片路徑")
            return
        if self.video_source.open_video(path):
            self.camera_connected = True
            self.pipeline_running = True
            self.detection_enabled = True
            self.auto_tracking_enabled = False
            self._set_status(f"已載入影片: {Path(path).name}")
        else:
            self.camera_connected = False
            self.pipeline_running = False
            self.detection_enabled = False
            self.auto_tracking_enabled = False
            self._set_status("無法載入影片，請確認路徑或檔案格式")
        self._refresh_indicators()
        self._ensure_timer()

    def _connect_camera(self) -> None:
        if self.video_source.open_camera(0):
            self.camera_connected = True
            self._set_status("攝影機已連接")
        else:
            self.camera_connected = True
            self._set_status("找不到實體攝影機，已切換為模擬畫面")
        self._refresh_indicators()
        self._ensure_timer()

    def _ensure_timer(self) -> None:
        if not self.frame_timer.isActive():
            self.frame_timer.start(self.config.update_interval_ms)

    def _pause_pipeline(self) -> None:
        self.frame_timer.stop()
        self.pipeline_running = False
        self.detection_enabled = False
        self.auto_tracking_enabled = False
        self.drone_detected = False
        self._refresh_indicators()
        self._set_status("已暫停播放")

    def _start_detection_pipeline(self) -> None:
        if self.current_mode == "Mode 1" and self.video_source.mode not in {"video", "camera"}:
            self._open_video_from_input()
        elif self.current_mode == "Mode 2" and self.video_source.mode == "mock" and not self.frame_timer.isActive():
            self._connect_camera()

        self.pipeline_running = True
        self.detection_enabled = True
        self.auto_tracking_enabled = False
        self._refresh_indicators()
        self._ensure_timer()
        self._set_status("開始執行影像辨識")

    def _start_auto_tracking(self) -> None:
        if self.video_source.mode == "mock" and not self.frame_timer.isActive():
            self._connect_camera()
        self.pipeline_running = True
        self.detection_enabled = True
        self.auto_tracking_enabled = True
        self._refresh_indicators()
        self._ensure_timer()
        self._set_status("開始執行自動追蹤")

    def _stop_pipeline(self) -> None:
        self.frame_timer.stop()
        self.pipeline_running = False
        self.detection_enabled = False
        self.auto_tracking_enabled = False
        self.drone_detected = False
        self.current_detection = None
        if self.video_source.mode == "video":
            self.video_source.rewind()
            preview = self.video_source.read_first_frame()
            if preview is not None:
                self.current_frame = preview.copy()
                self._update_preview(preview)
        self._refresh_indicators()
        self._set_status("已停止播放並回到開頭")

    def _step_once(self) -> None:
        self._ensure_timer()
        self._update_frame()
        self.pipeline_running = False
        self.detection_enabled = False
        self.auto_tracking_enabled = False
        self._refresh_indicators()
        self._set_status("已前進到下一幀")

    def _manual_pan(self, delta: float) -> None:
        self.controller.pan_by(delta)
        self._log_event("manual_pan", {"delta": delta, "pan_angle": self.controller.pan_angle})
        self._refresh_controller_labels()
        self._set_status(f"水平轉動 {delta:+.1f}°")

    def _manual_tilt(self, delta: float) -> None:
        self.controller.tilt_by(delta)
        self._log_event("manual_tilt", {"delta": delta, "tilt_angle": self.controller.tilt_angle})
        self._refresh_controller_labels()
        self._set_status(f"垂直轉動 {delta:+.1f}°")

    def _reset_pan_tilt(self) -> None:
        self.controller.pan_angle = 0.0
        self.controller.set_tilt(0.0)
        self._log_event("reset_pan_tilt", {"pan_angle": 0.0, "tilt_angle": 0.0})
        self._refresh_controller_labels()
        self._set_status("雲台已回正")

    def _save_snapshot(self) -> None:
        if self.current_frame is None:
            self._set_status("目前沒有畫面可擷取")
            return
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_path = SHOT_DIR / f"{timestamp_filename()}.png"
        cv2.imwrite(str(snapshot_path), self.current_frame)
        self._log_event("snapshot", {"path": str(snapshot_path)})
        self._set_status(f"已儲存擷圖: {snapshot_path.name}")

    def _export_log(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        export_path = LOG_DIR / f"{timestamp_filename()}.csv"
        rows = self.logs or [{"timestamp": datetime.now().isoformat(timespec="seconds"), "event": "empty"}]
        fieldnames = sorted({key for row in rows for key in row.keys()})
        with export_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        self._set_status(f"已匯出記錄檔: {export_path.name}")

    def _update_frame(self) -> None:
        ok, frame = self.video_source.read()
        if not ok:
            self._set_status("無法讀取影像來源")
            return

        self.current_frame = frame.copy()
        display = frame.copy()
        height, width = display.shape[:2]
        cv2.line(display, (width // 2, 0), (width // 2, height), (255, 220, 0), 1)
        cv2.line(display, (0, height // 2), (width, height // 2), (255, 220, 0), 1)

        detection = None
        if self.detection_enabled or self.auto_tracking_enabled:
            detection = self.detector.detect(display, self.video_source.frame_index)
            self.current_detection = detection
            self.drone_detected = detection is not None
        else:
            self.current_detection = None
            self.drone_detected = False

        if detection is not None:
            self._draw_detection(display, detection)
            self._log_detection(detection)
            if self.auto_tracking_enabled:
                self._apply_auto_tracking(display.shape, detection)
        else:
            cv2.putText(display, "No target", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 80, 80), 2)

        self._update_preview(display)
        self._refresh_indicators()
        self._refresh_controller_labels()

    def _draw_detection(self, frame, detection: DetectionResult) -> None:
        x1, y1, x2, y2 = detection.bbox
        cx, cy = detection.center
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 255, 255), -1)
        cv2.putText(
            frame,
            f"{detection.label} {detection.confidence:.2f} [{detection.source}]",
            (x1, max(24, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (30, 30, 30),
            2,
        )

    def _log_detection(self, detection: DetectionResult) -> None:
        x1, y1, x2, y2 = detection.bbox
        cx, cy = detection.center
        self._log_event(
            "detection",
            {
                "frame_index": self.video_source.frame_index,
                "source_path": self.video_source.path,
                "detector_source": detection.source,
                "label": detection.label,
                "confidence": round(detection.confidence, 4),
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "center_x": cx,
                "center_y": cy,
                "bbox_width": x2 - x1,
                "bbox_height": y2 - y1,
            },
        )

    def _apply_auto_tracking(self, frame_shape: tuple[int, int, int], detection: DetectionResult) -> None:
        frame_h, frame_w = frame_shape[:2]
        cx, cy = detection.center
        error_x = (cx - frame_w / 2.0) / (frame_w / 2.0)
        error_y = (cy - frame_h / 2.0) / (frame_h / 2.0)

        if abs(error_x) > self.config.pan_deadband:
            delta_pan = max(-self.config.pan_step_deg, min(self.config.pan_step_deg, error_x * 12.0))
            self.controller.pan_by(delta_pan)

        if abs(error_y) > self.config.tilt_deadband:
            delta_tilt = max(-self.config.tilt_step_deg, min(self.config.tilt_step_deg, error_y * 10.0))
            self.controller.tilt_by(delta_tilt)

        self._log_event(
            "auto_tracking",
            {
                "error_x": round(error_x, 3),
                "error_y": round(error_y, 3),
                "pan_angle": round(self.controller.pan_angle, 2),
                "tilt_angle": round(self.controller.tilt_angle, 2),
            },
        )

    def _update_preview(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)

        for label in (self.preview_label, self.live_preview_label):
            scaled = pixmap.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            label.setPixmap(scaled)

    def _render_placeholder(self, text: str) -> None:
        for label in (self.preview_label, self.live_preview_label):
            label.setText(text)
            label.setPixmap(QPixmap())

    def _log_event(self, event: str, extra: dict[str, str | float | int]) -> None:
        row: dict[str, str | float | int] = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": event,
            "mode": self.current_mode,
        }
        row.update(extra)
        self.logs.append(row)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.frame_timer.stop()
        self.video_source.release()
        self.controller.close()
        super().closeEvent(event)
