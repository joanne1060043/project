# 0513
from __future__ import annotations

import csv
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import cv2
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QSlider,
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


# 產生輸出檔名，供截圖與匯出紀錄共用。
def timestamp_filename() -> str:
    now = datetime.now()
    return f"{now.year}-{now.month}-{now.day} {now.hour:02d}-{now.minute:02d}"


# 把秒數轉成介面上顯示的時間字串。
def format_seconds(total_seconds: float) -> str:
    total_seconds = max(0, int(total_seconds))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


# 左側模式切換按鈕：只負責顯示狀態與回傳 Mode 1 / Mode 2。
class RockerSwitch(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_mode = "Mode 1"
        self.setFixedSize(96, 248)
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

        body = QRectF(18, 34, self.width() - 36, self.height() - 68)
        inner = body.adjusted(7, 7, -7, -7)
        is_mode1 = self.current_mode == "Mode 1"

        body_gradient = QLinearGradient(body.topLeft(), body.bottomRight())
        body_gradient.setColorAt(0.0, QColor("#6f6f75"))
        body_gradient.setColorAt(0.5, QColor("#d6d8dc"))
        body_gradient.setColorAt(1.0, QColor("#72757c"))
        painter.setPen(QPen(QColor("#5a5c61"), 2))
        painter.setBrush(body_gradient)
        painter.drawRoundedRect(body, 28, 28)

        inner_gradient = QLinearGradient(inner.topLeft(), inner.bottomLeft())
        inner_gradient.setColorAt(0.0, QColor("#ffffff"))
        inner_gradient.setColorAt(1.0, QColor("#dfe5ea"))
        painter.setPen(QPen(QColor("#9aa1ab"), 1))
        painter.setBrush(inner_gradient)
        painter.drawRoundedRect(inner, 22, 22)

        knob_width = inner.width() - 12
        knob_height = inner.height() / 2 - 12
        knob_rect = QRectF(
            inner.left() + 6,
            inner.top() + 8 if is_mode1 else inner.center().y() + 4,
            knob_width,
            knob_height,
        )

        knob_gradient = QLinearGradient(knob_rect.topLeft(), knob_rect.bottomLeft())
        knob_gradient.setColorAt(0.0, QColor("#fbfdff"))
        knob_gradient.setColorAt(1.0, QColor("#b8c0ca"))
        painter.setPen(QPen(QColor("#7d868f"), 2))
        painter.setBrush(knob_gradient)
        painter.drawRoundedRect(knob_rect, 18, 18)

        core_rect = knob_rect.adjusted(10, 10, -10, -10)
        painter.setPen(Qt.PenStyle.NoPen)
        core_gradient = QLinearGradient(core_rect.topLeft(), core_rect.bottomLeft())
        core_gradient.setColorAt(0.0, QColor("#efffed"))
        core_gradient.setColorAt(1.0, QColor("#a8ef9d"))
        painter.setBrush(core_gradient)
        painter.drawRoundedRect(core_rect, 14, 14)

        glow = QRadialGradient(core_rect.center(), max(core_rect.width(), core_rect.height()) * 0.7)
        glow.setColorAt(0.0, QColor(165, 255, 153, 120))
        glow.setColorAt(1.0, QColor(165, 255, 153, 0))
        glow_path = QPainterPath()
        glow_path.addRoundedRect(core_rect.adjusted(-4, -4, 4, 4), 16, 16)
        painter.fillPath(glow_path, glow)

        painter.setPen(QPen(QColor("#3b3b3b"), 1))
        font = painter.font()
        font.setPointSize(16)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, self.width(), 30), Qt.AlignmentFlag.AlignCenter, "離線模式")
        painter.drawText(QRectF(0, self.height() - 30, self.width(), 30), Qt.AlignmentFlag.AlignCenter, "即時監控")


# 底部媒體控制按鈕：依 icon_type 畫出播放、暫停、快轉等圖示。
class MediaButton(QToolButton):
    def __init__(self, icon_type: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icon_type = icon_type
        self.setFixedSize(66, 66)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QToolButton { background: transparent; border: none; }")

    def set_icon_type(self, icon_type: str) -> None:
        if self.icon_type != icon_type:
            self.icon_type = icon_type
            self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(3, 3, self.width() - 6, self.height() - 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#16181c"))
        painter.drawEllipse(rect)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        self._draw_icon(painter, rect.adjusted(6, 6, -6, -6))

    def _draw_icon(self, painter: QPainter, rect: QRectF) -> None:
        x = rect.left()
        y = rect.top()
        w = rect.width()
        h = rect.height()
        cy = rect.center().y()

        if self.icon_type == "play":
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(x + 18, y + 13),
                        QPointF(x + 18, y + h - 13),
                        QPointF(x + w - 14, cy),
                    ]
                )
            )
        elif self.icon_type == "pause":
            bar_width = 7
            bar_height = h - 18
            gap = 14
            left_x = x + (w - (bar_width * 2 + gap)) / 2
            top_y = y + 9
            painter.drawRoundedRect(QRectF(left_x, top_y, bar_width, bar_height), 3, 3)
            painter.drawRoundedRect(QRectF(left_x + bar_width + gap, top_y, bar_width, bar_height), 3, 3)
        elif self.icon_type == "back10":
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(x + w * 0.42, y + h * 0.30),
                        QPointF(x + w * 0.42, y + h * 0.70),
                        QPointF(x + w * 0.18, cy),
                    ]
                )
            )
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(x + w * 0.72, y + h * 0.18),
                        QPointF(x + w * 0.72, y + h * 0.82),
                        QPointF(x + w * 0.36, cy),
                    ]
                )
            )
            return
        elif self.icon_type == "forward10":
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(x + w * 0.32, y + h * 0.30),
                        QPointF(x + w * 0.32, y + h * 0.70),
                        QPointF(x + w * 0.56, cy),
                    ]
                )
            )
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(x + w * 0.50, y + h * 0.18),
                        QPointF(x + w * 0.50, y + h * 0.82),
                        QPointF(x + w * 0.86, cy),
                    ]
                )
            )
            return
        elif self.icon_type == "stop":
            painter.drawRect(QRectF(x + 14, y + 14, w - 28, h - 28))


# 軟體模擬版雲台控制器：本機沒有硬體時用來維持相同行為介面。
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


# 硬體版雲台控制器：有接馬達與伺服器時走這個流程。
class HardwarePanTiltController:
    def __init__(self, tilt_limit: float) -> None:
        self.tilt_limit = tilt_limit
        self.pan_angle = 0.0
        self.tilt_angle = 0.0
        self.pan_motor = None
        self.tilt_servo = None
        self.hardware_enabled = False
        self.last_error = ""

        if DCMotorController is not None and TiltServoController is not None:
            try:
                self.pan_motor = DCMotorController(in1_pin=17, in2_pin=27, default_speed=38)
                self.tilt_servo = TiltServoController(pin=12, zero_offset=90)
                pan_ready = getattr(self.pan_motor, "h", None) is not None
                tilt_ready = getattr(self.tilt_servo, "servo", None) is not None
                self.hardware_enabled = pan_ready and tilt_ready
                if not self.hardware_enabled:
                    self.last_error = "GPIO motor/servo initialization incomplete"
                    if self.pan_motor is not None:
                        self.pan_motor.close()
                    if self.tilt_servo is not None:
                        self.tilt_servo.close()
                    self.pan_motor = None
                    self.tilt_servo = None
            except Exception as exc:
                self.last_error = str(exc)
                self.pan_motor = None
                self.tilt_servo = None
        else:
            self.last_error = "GPIO motor/servo modules are not available"

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


# 主視窗：整合 UI、播放控制、偵測、追蹤、截圖與匯出功能。
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        # 核心模組與共享狀態都在這裡初始化，後面所有功能都會共用這些欄位。
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
        self.current_detections: list[DetectionResult] = []
        self.pending_detection: DetectionResult | None = None
        self.detection_streak = 0
        self.last_tracking_command_at = 0.0
        self.current_frame_size: tuple[int, int] | None = None
        self.progress_dragging = False
        self.video_clock_started_at: float | None = None
        self.video_clock_anchor_frame = 0
        self.play_pause_button: MediaButton | None = None
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
        self._reset_progress_ui()
        self._refresh_play_pause_button()

    # 依硬體可用性選擇真實控制器或模擬控制器。
    def _build_controller(self):
        hardware = HardwarePanTiltController(self.config.tilt_limit_deg)
        if hardware.hardware_enabled:
            return hardware
        if hardware.last_error:
            print(f"[Controller] falling back to mock control: {hardware.last_error}")
        return MockPanTiltController(self.config.tilt_limit_deg)

    # 建立整個主視窗三欄版面：左側模式、中間工作區、右側狀態卡片。
    def _build_central_widget(self) -> None:
        container = QWidget()
        container.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            " stop:0 #eef5fb, stop:0.55 #f7f9fc, stop:1 #e8edf4);"
        )

        layout = QHBoxLayout(container)
        layout.setContentsMargins(18, 18, 24, 18) # 左、上、右、下 邊距
        layout.setSpacing(22) # 元件與元件之間的間隔
        layout.addWidget(self._build_mode_panel(), alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._build_center_stack(), stretch=1)
        layout.addWidget(self._build_status_column(), alignment=Qt.AlignmentFlag.AlignTop)
        self.setCentralWidget(container)

    # 左側模式切換區，只放模式開關本體。
    def _build_mode_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(110)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 90, 0, 0)
        layout.setSpacing(14)

        self.mode_switch = RockerSwitch()
        self.mode_switch.clicked.connect(self._set_mode)

        layout.addWidget(self.mode_switch, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        return panel

    # 中央工作區用堆疊頁切換 Mode 1 / Mode 2。
    def _build_center_stack(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self._build_mode1_page())
        self.mode_stack.addWidget(self._build_mode2_page())
        layout.addWidget(self.mode_stack)
        return wrapper

    # 右側狀態卡片外層容器，用來控制整張卡片的垂直位置。
    def _build_status_column(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setFixedWidth(300)

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 168, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_status_panel())
        layout.addStretch()
        return wrapper

    # Mode 1：影片檔案路徑、載入按鈕、預覽與播放控制。
    def _build_mode1_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("Video Path")
        title.setStyleSheet(self._title_style())

        row = QHBoxLayout()
        row.setSpacing(12)

        self.mode1_path_input = QLineEdit()
        self.mode1_path_input.setPlaceholderText("請輸入影片檔案路徑")
        self.mode1_path_input.setText(str(WORKSPACE / "demo.mp4"))
        self.mode1_path_input.setFixedHeight(42)
        self.mode1_path_input.setStyleSheet(self._path_input_style())
        self._apply_shadow(self.mode1_path_input, blur=18, dy=3, color=QColor(72, 89, 110, 55))

        browse_button = QPushButton("Select Video")
        browse_button.setFixedHeight(42)
        browse_button.setStyleSheet(self._secondary_button_style())
        browse_button.clicked.connect(self._choose_video)
        self._apply_shadow(browse_button, blur=18, dy=3, color=QColor(29, 84, 145, 55))
        self._fit_button_width(browse_button, extra_padding=40, min_width=150)

        open_button = QPushButton("Load the video")
        open_button.setFixedHeight(42)
        open_button.setStyleSheet(self._secondary_button_style())
        open_button.clicked.connect(self._open_video_from_input)
        self._apply_shadow(open_button, blur=18, dy=3, color=QColor(29, 84, 145, 55))
        self._fit_button_width(open_button, extra_padding=40, min_width=150)

        row.addWidget(self.mode1_path_input, stretch=1)
        row.addWidget(browse_button)
        row.addWidget(open_button)

        layout.addWidget(title)
        layout.addLayout(row)
        layout.addWidget(
            self._build_video_panel(
                [
                    ("back10", self._rewind_10_seconds),
                    ("toggle_play", self._toggle_playback),
                    ("forward10", self._forward_10_seconds),
                    ("stop", self._stop_pipeline),
                ]
            ),
            stretch=1,
        )
        return page

    # Mode 2：即時攝影機模式與其工具列。
    def _build_mode2_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("即時攝影機")
        title.setStyleSheet(self._title_style())

        tool_row = QHBoxLayout()
        tool_row.setSpacing(14)

        connect_button = QPushButton("連接攝影機")
        track_button = QPushButton("開始追蹤")
        snapshot_button = QPushButton("擷取畫面")

        connect_button.clicked.connect(self._connect_camera)
        track_button.clicked.connect(self._start_auto_tracking)
        snapshot_button.clicked.connect(self._save_snapshot)

        for button in (connect_button, track_button, snapshot_button):
            button.setFixedHeight(44)
            button.setStyleSheet(self._secondary_button_style())
            tool_row.addWidget(button)
            self._apply_shadow(button, blur=16, dy=3, color=QColor(29, 84, 145, 50))
            self._fit_button_width(button, extra_padding=34, min_width=130)
        tool_row.addStretch()

        layout.addWidget(title)
        layout.addLayout(tool_row)
        layout.addWidget(self._build_manual_control_group())
        layout.addWidget(self._build_preview_panel(), stretch=1)
        return page

    # 手動控制區：提供雲台上下左右與置中。
    def _build_manual_control_group(self) -> QWidget:
        box = QFrame()
        box.setStyleSheet(self._soft_panel_style("#c9dffd", "#f7fbff"))
        self._apply_shadow(box, blur=24, dy=6, color=QColor(73, 94, 120, 45))

        layout = QHBoxLayout(box)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(24)

        title = QLabel("手動控制")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #284266;")

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
            label.setStyleSheet("font-size: 18px; color: #45617f;")
            info_layout.addWidget(label)

        layout.addWidget(title)
        layout.addLayout(grid)
        layout.addLayout(info_layout)
        layout.addStretch()
        return box

    # 共用的小型藍色控制按鈕。
    def _make_control_button(self, text: str, callback: Callable[[], None]) -> QPushButton:
        button = QPushButton(text)
        button.setFixedSize(78, 42)
        button.setStyleSheet(self._secondary_button_style())
        button.clicked.connect(callback)
        self._apply_shadow(button, blur=14, dy=2, color=QColor(29, 84, 145, 40))
        return button

    # 依按鈕文字長度設定最小寬度，避免不同語系或較長文字被切掉。
    def _fit_button_width(self, button: QPushButton, extra_padding: int = 36, min_width: int = 0) -> None:
        text_width = button.fontMetrics().horizontalAdvance(button.text())
        button.setMinimumWidth(max(min_width, text_width + extra_padding))

    # Mode 1 影片區：外框、預覽畫面、進度條、底部控制列都在這裡組裝。
    def _build_video_panel(self, controls: list[tuple[str, object]]) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(self._hero_panel_style())
        panel.setFrameShape(QFrame.Shape.Box)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel.setMinimumHeight(520)
        self._apply_shadow(panel, blur=28, dy=8, color=QColor(76, 102, 140, 55))

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        preview_shell = QFrame()
        preview_shell.setStyleSheet(self._screen_shell_style())
        preview_layout = QVBoxLayout(preview_shell)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(0)

        self.preview_label = QLabel("影片預覽")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(0, 0)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setStyleSheet(self._screen_label_style())
        preview_layout.addWidget(self.preview_label)

        progress_bar = QFrame()
        progress_bar.setFixedHeight(54)
        progress_bar.setStyleSheet(self._progress_tray_style())

        progress_layout = QHBoxLayout(progress_bar)
        progress_layout.setContentsMargins(18, 10, 18, 6)
        progress_layout.setSpacing(14)

        self.progress_time_label = QLabel("00:00 / 00:00")
        self.progress_time_label.setStyleSheet("border: none; color: #334c6d; font-size: 16px; font-weight: 600;")

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setStyleSheet(
            "QSlider { border: none; }"
            "QSlider::groove:horizontal { height: 10px; background: #d8e5f7; border-radius: 5px; }"
            "QSlider::sub-page:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5ca7e8, stop:1 #2b7fca); border-radius: 5px; }"
            "QSlider::handle:horizontal { width: 18px; margin: -5px 0; border-radius: 9px; background: #ffffff; border: 3px solid #3d93db; }"
        )
        self.progress_slider.sliderPressed.connect(self._on_progress_pressed)
        self.progress_slider.sliderReleased.connect(self._on_progress_released)

        progress_layout.addWidget(self.progress_slider, stretch=1)
        progress_layout.addWidget(self.progress_time_label)

        control_bar = QFrame()
        control_bar.setFixedHeight(82)
        control_bar.setStyleSheet("QFrame { border: none; background: transparent; }")

        controls_layout = QHBoxLayout(control_bar)
        controls_layout.setContentsMargins(0, 10, 0, 10)
        controls_layout.setSpacing(16)
        controls_layout.addStretch()

        for icon_type, handler in controls:
            button = MediaButton("play" if icon_type == "toggle_play" else icon_type)
            if icon_type == "toggle_play":
                self.play_pause_button = button
            button.clicked.connect(handler)
            controls_layout.addWidget(button)

        controls_layout.addStretch()
        layout.addWidget(preview_shell, stretch=1)
        layout.addWidget(progress_bar)
        layout.addWidget(control_bar)
        return panel

    # Mode 2 即時畫面區：沿用同樣的畫面框風格，但不含播放控制。
    def _build_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(self._hero_panel_style())
        panel.setFrameShape(QFrame.Shape.Box)
        panel.setLineWidth(2)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel.setMinimumHeight(520)
        self._apply_shadow(panel, blur=28, dy=8, color=QColor(76, 102, 140, 55))

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        preview_shell = QFrame()
        preview_shell.setStyleSheet(self._screen_shell_style())
        preview_layout = QVBoxLayout(preview_shell)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(0)

        self.live_preview_label = QLabel("即時畫面")
        self.live_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live_preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.live_preview_label.setMinimumSize(0, 0)
        self.live_preview_label.setStyleSheet(self._screen_label_style())

        preview_layout.addWidget(self.live_preview_label)
        layout.addWidget(preview_shell)
        return panel

    # 右側狀態卡片：燈號、狀態訊息、中心點座標與匯出按鈕。
    def _build_status_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(300)
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        panel.setStyleSheet(self._soft_panel_style("#d9e3f0", "rgba(255, 255, 255, 0.72)"))
        self._apply_shadow(panel, blur=24, dy=6, color=QColor(76, 102, 140, 45))

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 28, 20, 24)
        layout.setSpacing(22)

        camera_row, self.camera_indicator = self._build_indicator_row("Camera connection", "#22c55e")
        running_row, self.running_indicator = self._build_indicator_row("In action", "#2563eb")
        detect_row, self.detect_indicator = self._build_indicator_row("Detection", "#ff3b30")

        layout.addLayout(camera_row)
        layout.addLayout(running_row)
        layout.addLayout(detect_row)

        self.status_text = QLabel("等待啟動")
        self.status_text.setWordWrap(True)
        self.status_text.setStyleSheet("font-size: 19px; color: #465a72;")
        layout.addWidget(self.status_text)

        self.center_point_label = QLabel("中心點座標: (--, --)")
        self.center_point_label.setWordWrap(True)
        self.center_point_label.setStyleSheet("font-size: 21px; color: #2f435a;")
        layout.addWidget(self.center_point_label)

        self.center_offset_label = QLabel("相對中心偏移: dx -- px, dy -- px")
        self.center_offset_label.setWordWrap(True)
        self.center_offset_label.setStyleSheet("font-size: 18px; color: #5a6e84;")
        layout.addWidget(self.center_offset_label)

        layout.addSpacing(18)

        export_button = QPushButton("Export")
        export_button.setFixedSize(202, 76)
        export_button.setStyleSheet(
            "QPushButton {"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff9a1a, stop:1 #ff7b00);"
            "border: 1px solid #e87400;"
            "border-radius: 12px;"
            "font-size: 24px;"
            "font-weight: 700;"
            "color: white;"
            "padding-bottom: 2px;"
            "}"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffad36, stop:1 #ff8c14); }"
        )
        export_button.clicked.connect(self._export_log)
        self._apply_shadow(export_button, blur=22, dy=6, color=QColor(255, 136, 0, 85))

        layout.addWidget(export_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)
        return panel

    # 狀態燈一列的共用組裝方式。
    def _build_indicator_row(self, text: str, active_color: str) -> tuple[QHBoxLayout, QLabel]:
        row = QHBoxLayout()
        row.setSpacing(14)

        dot = QLabel()
        dot.setFixedSize(34, 34)
        dot.setProperty("active_color", active_color)

        label = QLabel(text)
        label.setStyleSheet("font-size: 22px; color: #30465d;")

        row.addWidget(dot)
        row.addWidget(label)
        row.addStretch()
        return row, dot

    # 路徑輸入框樣式。
    def _path_input_style(self, border: str = "#ff3b30") -> str:
        return (
            "QLineEdit {"
            f"border: 1px solid {border};"
            "border-radius: 9px;"
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #70767e, stop:1 #5d636b);"
            "font-size: 18px;"
            "padding: 6px 12px;"
            "color: #f8fafc;"
            "selection-background-color: #8bbef0;"
            "}"
        )

    # 一般功能按鈕樣式。
    def _secondary_button_style(self) -> str:
        return (
            "QPushButton {"
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2e91db, stop:1 #1f67b5);"
            "border: 1px solid #1d5da1;"
            "border-radius: 9px;"
            "font-size: 20px;"
            "font-weight: 600;"
            "padding: 7px 16px;"
            "color: white;"
            "}"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43a4ec, stop:1 #2877c6); }"
            "QPushButton:pressed { background: #1b5ea6; }"
        )

    # 頁面標題樣式。
    def _title_style(self) -> str:
        return "font-size: 31px; font-weight: 800; color: #23364b; letter-spacing: 1px;"

    # 柔和卡片外觀，主要用在右側資訊面板。
    def _soft_panel_style(self, border_color: str, background: str) -> str:
        return (
            "QFrame {"
            f"background: {background};"
            f"border: 1px solid {border_color};"
            "border-radius: 16px;"
            "}"
        )

    # 主預覽區外框樣式。
    def _hero_panel_style(self) -> str:
        return (
            "QFrame {"
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #cfe4f8, stop:0.12 #bdd9f4, stop:0.13 #d7e8f9, stop:1 #d9e8f8);"
            "border: 1px solid #9fc3e7;"
            "border-radius: 18px;"
            "}"
        )

    # 內層白色畫布外框。
    def _screen_shell_style(self) -> str:
        return (
            "QFrame {"
            "background: #fdfefe;"
            "border: 1px solid #78aee2;"
            "border-radius: 14px;"
            "}"
        )

    # 畫面本體 QLabel 的背景與文字樣式。
    def _screen_label_style(self) -> str:
        return (
            "border: none;"
            "border-radius: 10px;"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #edf5fd);"
            "color: #5b6d82;"
            "font-size: 72px;"
            "font-weight: 500;"
        )

    # 進度條托盤外觀。
    def _progress_tray_style(self) -> str:
        return (
            "QFrame {"
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #dfeefe, stop:1 #d2e5f8);"
            "border: 1px solid #b4d0ec;"
            "border-radius: 12px;"
            "}"
        )

    # 套用陰影效果，讓卡片與按鈕更有層次。
    def _apply_shadow(self, widget: QWidget, blur: int, dy: int, color: QColor) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, dy)
        shadow.setColor(color)
        widget.setGraphicsEffect(shadow)

    # 底部狀態列建立與初始樣式。
    def _build_status_bar(self) -> None:
        status_bar = QStatusBar()
        status_bar.setStyleSheet(
            "QStatusBar { background: rgba(255, 255, 255, 0.88); color: #49627f; border-top: 1px solid #d7e3f0; }"
        )
        status_bar.showMessage("系統就緒")
        self.setStatusBar(status_bar)

    # 依目前模式刷新左側切換鈕。
    def _refresh_mode_tabs(self) -> None:
        self.mode_switch.set_mode(self.current_mode)

    # 切換中央堆疊頁內容。
    def _refresh_mode_page(self) -> None:
        self.mode_stack.setCurrentIndex(0 if self.current_mode == "Mode 1" else 1)

    # 更新右側三顆狀態燈。
    def _refresh_indicators(self) -> None:
        self._set_indicator_state(self.camera_indicator, self.camera_connected)
        self._set_indicator_state(self.running_indicator, self.pipeline_running)
        self._set_indicator_state(self.detect_indicator, self.drone_detected)

    # 播放 / 暫停共用鍵的圖示切換。
    def _refresh_play_pause_button(self) -> None:
        if self.play_pause_button is None:
            return
        self.play_pause_button.set_icon_type("pause" if self.pipeline_running else "play")

    # 刷新右側控制資訊與多目標中心點座標。
    def _refresh_controller_labels(self) -> None:
        backend = "GPIO 硬體" if getattr(self.controller, "hardware_enabled", False) else "模擬控制"
        detector = f"{self.detector.backend_name.upper()} 偵測"
        self.pan_label.setText(f"水平角度: {self.controller.pan_angle:+.1f}°")
        self.tilt_label.setText(f"垂直角度: {self.controller.tilt_angle:+.1f}°")
        self.backend_label.setText(f"控制模式: {backend}")
        self.target_label.setText(f"辨識後端: {detector}")

        if self.current_detections:
            point_lines = ["中心點座標:"]
            offset_lines = ["相對中心偏移:"]
            for index, detection in enumerate(self.current_detections, start=1):
                cx, cy = detection.center
                point_lines.append(f"{index}. ({cx}, {cy})")
                if self.current_frame_size is not None:
                    frame_w, frame_h = self.current_frame_size
                    dx = cx - (frame_w // 2)
                    dy = cy - (frame_h // 2)
                    offset_lines.append(f"{index}. dx {dx:+d} px, dy {dy:+d} px")
                else:
                    offset_lines.append(f"{index}. dx -- px, dy -- px")
            self.center_point_label.setText("\n".join(point_lines))
            self.center_offset_label.setText("\n".join(offset_lines))
        else:
            self.center_point_label.setText("中心點座標:\n--")
            self.center_offset_label.setText("相對中心偏移:\ndx -- px, dy -- px")

    # 將狀態燈設成亮 / 滅對應的樣式。
    def _set_indicator_state(self, indicator: QLabel, active: bool) -> None:
        if active:
            color = indicator.property("active_color")
            indicator.setStyleSheet(
                "border: 1px solid rgba(40, 50, 65, 0.35);"
                "border-radius: 17px;"
                f"background: qradialgradient(cx:0.45, cy:0.4, radius:0.9, stop:0 rgba(255,255,255,0.95), stop:0.22 {color}, stop:0.68 {color}, stop:1 rgba(20,20,20,0.3));"
            )
        else:
            indicator.setStyleSheet(
                "border: 1px solid rgba(67, 77, 89, 0.28);"
                "border-radius: 17px;"
                "background: qradialgradient(cx:0.45, cy:0.4, radius:0.9, stop:0 #fbfdff, stop:0.38 #e4ebf2, stop:1 #b6c0cb);"
            )

    # 切換 Mode 時，重設不應被另一個模式沿用的狀態與畫面。
    def _set_mode(self, mode: str) -> None:
        if self.current_mode != mode:
            self.frame_timer.stop()
            self.video_source.release()
            self._clear_video_clock()
            self.pipeline_running = False
            self.detection_enabled = False
            self.auto_tracking_enabled = False
            self.drone_detected = False
            self.camera_connected = False
            self.current_frame = None
            self.current_frame_size = None
            self.current_detection = None
            self.current_detections = []
            self.pending_detection = None
            self.detection_streak = 0
            self._render_placeholder("尚未啟動影像來源")
            self._reset_progress_ui()
        self.current_mode = mode
        self._refresh_mode_tabs()
        self._refresh_mode_page()
        self._refresh_indicators()
        self._refresh_play_pause_button()
        self._refresh_controller_labels()
        self._set_status(f"已切換為 {mode}")

    # 同步右側狀態文字與底部狀態列訊息。
    def _set_status(self, text: str) -> None:
        self.status_text.setText(text)
        self.statusBar().showMessage(text)

    # 底部播放鍵：在播放與暫停之間切換。
    def _toggle_playback(self) -> None:
        if self.pipeline_running:
            self._pause_pipeline()
        else:
            self._start_detection_pipeline()

    # 開啟檔案選擇器，讓使用者挑影片。
    def _choose_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇影片檔",
            str(WORKSPACE),
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)",
        )
        if path:
            self.mode1_path_input.setText(path)

    # 根據輸入框路徑載入影片並啟動 Mode 1。
    def _open_video_from_input(self) -> None:
        path = self.mode1_path_input.text().strip()
        if not path:
            self._set_status("????????")
            return
        if self.video_source.open_video(path):
            self._resume_video_clock()
            self.camera_connected = True
            self.pipeline_running = True
            self.detection_enabled = True
            self.auto_tracking_enabled = False
            self._refresh_progress_ui()
            self._set_status(f"{Path(path).name}")
        else:
            self._clear_video_clock()
            self.camera_connected = False
            self.pipeline_running = False
            self.detection_enabled = False
            self.auto_tracking_enabled = False
            self._reset_progress_ui()
            self._set_status("?????????????????")
        self._refresh_indicators()
        self._ensure_timer()
        self._refresh_play_pause_button()

    # 連接攝影機，失敗時保留模擬畫面作為 fallback。
    def _connect_camera(self) -> None:
        self._clear_video_clock()
        if self.video_source.open_camera():
            self.camera_connected = True
            self.pipeline_running = True
            self.detection_enabled = True
            self.auto_tracking_enabled = False
            self._set_status(
                f"已連接攝影機（Camera {self.video_source.path}, {self.video_source.camera_backend}），並自動開始偵測"
            )
        else:
            self.camera_connected = False
            self.pipeline_running = False
            self.detection_enabled = False
            self.auto_tracking_enabled = False
            self._set_status("無法連接攝影機，已嘗試 camera 0 / 1 與可用後端")
        self._refresh_indicators()
        self._ensure_timer()
        self._refresh_play_pause_button()

    # 確保逐幀更新計時器已經啟動。
    def _ensure_timer(self) -> None:
        if not self.frame_timer.isActive():
            self.frame_timer.start(self.config.update_interval_ms)

    # 清掉影片播放時鐘，避免舊時間基準繼續影響進度條。
    def _clear_video_clock(self) -> None:
        self.video_clock_started_at = None
        self.video_clock_anchor_frame = 0

    # 暫停時計住目前幀位置，之後播放才能從正確位置續播。
    def _pause_video_clock(self) -> None:
        if self.video_source.mode == "video":
            self.video_clock_anchor_frame = self.video_source.get_current_frame()
        self.video_clock_started_at = None

    # 從目前幀重新啟動影片時間基準。
    def _resume_video_clock(self) -> None:
        if self.video_source.mode != "video":
            self._clear_video_clock()
            return
        self.video_clock_anchor_frame = self.video_source.get_current_frame()
        self.video_clock_started_at = time.monotonic()

    # 依真實經過時間追上影片位置，必要時直接跳幀。
    def _sync_video_position_to_clock(self) -> None:
        if self.video_source.mode != "video" or self.video_clock_started_at is None:
            return

        fps = self.video_source.get_fps()
        if fps <= 0:
            return

        total_frames = self.video_source.get_frame_count()
        elapsed = time.monotonic() - self.video_clock_started_at
        target_frame = self.video_clock_anchor_frame + int(elapsed * fps)
        if total_frames > 0:
            target_frame = max(0, min(target_frame, total_frames - 1))
        else:
            target_frame = max(0, target_frame)

        current_frame = self.video_source.get_current_frame()
        if abs(current_frame - target_frame) > 1:
            self.video_source.seek_to_frame(target_frame)

    # 沒有影片時，把進度條重設為初始狀態。
    def _reset_progress_ui(self) -> None:
        self.progress_slider.setEnabled(self.video_source.mode == "video")
        self.progress_slider.setValue(0)
        self.progress_time_label.setText("00:00 / 00:00")

    # 依目前影片位置刷新進度條與時間字樣。
    def _refresh_progress_ui(self) -> None:
        if self.video_source.mode != "video":
            self._reset_progress_ui()
            return

        total_frames = self.video_source.get_frame_count()
        fps = self.video_source.get_fps()
        current_frame = self.video_source.get_current_frame()
        if self.video_clock_started_at is not None and fps > 0:
            elapsed = time.monotonic() - self.video_clock_started_at
            current_frame = self.video_clock_anchor_frame + int(elapsed * fps)
            if total_frames > 0:
                current_frame = max(0, min(current_frame, total_frames - 1))
            else:
                current_frame = max(0, current_frame)
        total_seconds = total_frames / fps if fps > 0 and total_frames > 0 else 0.0
        current_seconds = current_frame / fps if fps > 0 else 0.0

        self.progress_slider.setEnabled(total_frames > 0)
        if total_frames > 0 and not self.progress_dragging:
            slider_value = int((current_frame / max(1, total_frames - 1)) * 1000)
            self.progress_slider.setValue(max(0, min(1000, slider_value)))

        self.progress_time_label.setText(
            f"{format_seconds(current_seconds)} / {format_seconds(total_seconds)}"
        )

    # 使用者開始拖曳進度條時，先記錄正在手動操作。
    def _on_progress_pressed(self) -> None:
        self.progress_dragging = True

    # 拖曳放開後，將影片跳到對應幀位置。
    def _on_progress_released(self) -> None:
        self.progress_dragging = False
        if self.video_source.mode != "video":
            self._reset_progress_ui()
            return

        total_frames = self.video_source.get_frame_count()
        if total_frames <= 0:
            self._reset_progress_ui()
            return

        ratio = self.progress_slider.value() / 1000.0
        target_frame = int(round(ratio * max(0, total_frames - 1)))
        if self.video_source.seek_to_frame(target_frame):
            self.video_clock_anchor_frame = self.video_source.get_current_frame()
            if self.frame_timer.isActive():
                self.video_clock_started_at = time.monotonic()
            else:
                self.video_clock_started_at = None
            if not self.frame_timer.isActive():
                ok, frame = self.video_source.read()
                if ok:
                    self.current_frame = frame.copy()
                    self._update_preview(frame)
        self._refresh_progress_ui()

    # 影片倒轉 10 秒。
    def _rewind_10_seconds(self) -> None:
        if self.video_source.mode != "video":
            return
        if self.video_source.seek_by_seconds(-10.0):
            self.video_clock_anchor_frame = self.video_source.get_current_frame()
            if self.frame_timer.isActive():
                self.video_clock_started_at = time.monotonic()
            else:
                self.video_clock_started_at = None
                ok, frame = self.video_source.read()
                if ok:
                    self.current_frame = frame.copy()
                    self._update_preview(frame)
        self._refresh_progress_ui()

    # 影片快轉 10 秒。
    def _forward_10_seconds(self) -> None:
        if self.video_source.mode != "video":
            return
        if self.video_source.seek_by_seconds(10.0):
            self.video_clock_anchor_frame = self.video_source.get_current_frame()
            if self.frame_timer.isActive():
                self.video_clock_started_at = time.monotonic()
            else:
                self.video_clock_started_at = None
                ok, frame = self.video_source.read()
                if ok:
                    self.current_frame = frame.copy()
                    self._update_preview(frame)
        self._refresh_progress_ui()

    # 暫停播放，同時關閉偵測與追蹤狀態。
    def _pause_pipeline(self) -> None:
        self._pause_video_clock()
        self.frame_timer.stop()
        self.pipeline_running = False
        self.detection_enabled = False
        self.auto_tracking_enabled = False
        self.drone_detected = False
        self.current_detection = None
        self.current_detections = []
        self.pending_detection = None
        self.detection_streak = 0
        self._refresh_indicators()
        self._refresh_play_pause_button()
        self._set_status("Suspended")
        self._refresh_progress_ui()

    # 啟動一般辨識流程。
    def _start_detection_pipeline(self) -> None:
        if self.current_mode == "Mode 1" and self.video_source.mode not in {"video", "camera"}:
            self._open_video_from_input()
        elif self.current_mode == "Mode 2" and self.video_source.mode == "mock" and not self.frame_timer.isActive():
            self._connect_camera()

        if self.video_source.mode == "video":
            self._resume_video_clock()
        else:
            self._clear_video_clock()
        self.pipeline_running = True
        self.detection_enabled = True
        self.auto_tracking_enabled = False
        self._refresh_indicators()
        self._refresh_play_pause_button()
        self._ensure_timer()
        self._set_status("開始執行影像辨識")

    # 啟動自動追蹤流程。
    def _start_auto_tracking(self) -> None:
        if self.current_mode == "Mode 2" and self.video_source.mode != "camera":
            self._connect_camera()
            if self.video_source.mode != "camera":
                self.auto_tracking_enabled = False
                self._refresh_indicators()
                self._set_status("無法啟動追蹤：請先連接攝影機")
                return

        self._clear_video_clock()
        self.last_tracking_command_at = 0.0
        self.pipeline_running = True
        self.detection_enabled = True
        self.auto_tracking_enabled = True
        self._refresh_indicators()
        self._refresh_play_pause_button()
        self._ensure_timer()
        self._set_status("開始執行自動追蹤，偵測到無人機後會自動置中")

    # 停止播放並回到初始畫面。
    def _stop_pipeline(self) -> None:
        self._pause_video_clock()
        self.frame_timer.stop()
        self.pipeline_running = False
        self.detection_enabled = False
        self.auto_tracking_enabled = False
        self.drone_detected = False
        self.current_detection = None
        self.current_detections = []
        self.pending_detection = None
        self.detection_streak = 0
        if self.video_source.mode == "video":
            self.video_source.rewind()
            self.video_clock_anchor_frame = 0
            self.video_clock_started_at = None
            preview = self.video_source.read_first_frame()
            if preview is not None:
                self.current_frame = preview.copy()
                self._update_preview(preview)
        self._refresh_indicators()
        self._refresh_play_pause_button()
        self._set_status("??????????")
        self._refresh_progress_ui()

    # 單步前進一幀，方便除錯或慢速檢查結果。
    def _step_once(self) -> None:
        if self.video_source.mode == "video":
            self._resume_video_clock()
        self._ensure_timer()
        self._update_frame()
        self._pause_video_clock()
        self.pipeline_running = False
        self.detection_enabled = False
        self.auto_tracking_enabled = False
        self._refresh_indicators()
        self._refresh_play_pause_button()
        self._set_status("已前進到下一幀")

    # 手動水平轉動雲台。
    def _manual_pan(self, delta: float) -> None:
        self.controller.pan_by(delta)
        self._log_event("manual_pan", {"delta": delta, "pan_angle": self.controller.pan_angle})
        self._refresh_controller_labels()
        self._set_status(f"水平轉動 {delta:+.1f}°")

    # 手動垂直轉動雲台。
    def _manual_tilt(self, delta: float) -> None:
        self.controller.tilt_by(delta)
        self._log_event("manual_tilt", {"delta": delta, "tilt_angle": self.controller.tilt_angle})
        self._refresh_controller_labels()
        self._set_status(f"垂直轉動 {delta:+.1f}°")

    # 將雲台角度重設回中心。
    def _reset_pan_tilt(self) -> None:
        current_pan = self.controller.pan_angle
        if current_pan != 0:
            self.controller.pan_by(-current_pan)
        self.controller.set_tilt(0.0)
        self._log_event("reset_pan_tilt", {"pan_angle": 0.0, "tilt_angle": 0.0})
        self._refresh_controller_labels()
        self._set_status("雲台已回正")

    # 把目前畫面存成截圖。
    def _save_snapshot(self) -> None:
        if self.current_frame is None:
            self._set_status("目前沒有畫面可擷取")
            return
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_path = SHOT_DIR / f"{timestamp_filename()}.png"
        cv2.imwrite(str(snapshot_path), self.current_frame)
        self._log_event("snapshot", {"path": str(snapshot_path)})
        self._set_status(f"已儲存擷圖: {snapshot_path.name}")

    # 將累積事件匯出成 CSV。
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

    # 每一幀的主流程：讀畫面、跑偵測、畫框、更新 UI。
    def _update_frame(self) -> None:
        self._sync_video_position_to_clock()
        ok, frame = self.video_source.read()
        if not ok:
            self._set_status("無法讀取影像來源")
            return

        self.current_frame = frame.copy()
        display = frame.copy()
        height, width = display.shape[:2]
        self.current_frame_size = (width, height)
        cv2.line(display, (width // 2, 0), (width // 2, height), (255, 220, 0), 1)
        cv2.line(display, (0, height // 2), (width, height // 2), (255, 220, 0), 1)

        detections: list[DetectionResult] = []
        if self.detection_enabled or self.auto_tracking_enabled:
            min_confidence = (
                self.config.camera_confidence
                if self.video_source.mode == "camera"
                else self.config.video_confidence
            )
            raw_detections = self.detector.detect_all(
                display,
                self.video_source.frame_index,
                min_confidence=min_confidence,
            )
            if self.video_source.mode == "camera":
                primary_detection = self._confirm_detection(raw_detections[0] if raw_detections else None, display.shape[:2])
                detections = [primary_detection] if primary_detection is not None else []
            else:
                detections = raw_detections
            self.current_detections = sorted(detections, key=lambda item: item.center[0])
            self.current_detection = self._select_primary_detection(detections)
            self.drone_detected = bool(detections)
        else:
            self.current_detection = None
            self.current_detections = []
            self.drone_detected = False
            self.pending_detection = None
            self.detection_streak = 0

        if self.current_detections:
            for detection in self.current_detections:
                self._draw_detection(display, detection)
                self._log_detection(detection)
            if self.auto_tracking_enabled and self.current_detection is not None:
                self._apply_auto_tracking(display.shape, self.current_detection)
        else:
            cv2.putText(display, "No target", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 80, 80), 2)

        self._update_preview(display)
        self._refresh_progress_ui()
        self._refresh_indicators()
        self._refresh_controller_labels()

    # 多目標時挑出一台主目標，供自動追蹤沿用。
    def _select_primary_detection(self, detections: list[DetectionResult]) -> DetectionResult | None:
        if not detections:
            return None

        def detection_score(item: DetectionResult) -> float:
            x1, y1, x2, y2 = item.bbox
            return max(0, x2 - x1) * max(0, y2 - y1) * item.confidence

        return max(detections, key=detection_score)

    # 攝影機模式下做連續幀確認，降低單幀誤判。
    def _confirm_detection(
        self,
        detection: DetectionResult | None,
        frame_shape: tuple[int, int],
    ) -> DetectionResult | None:
        if detection is None:
            self.pending_detection = None
            self.detection_streak = 0
            return None

        required_frames = (
            self.config.camera_confirmation_frames
            if self.video_source.mode == "camera"
            else 1
        )
        if required_frames <= 1:
            self.pending_detection = detection
            self.detection_streak = 1
            return detection

        frame_h, frame_w = frame_shape
        tolerance = max(40, int(min(frame_h, frame_w) * 0.08))

        if self.pending_detection is None:
            self.pending_detection = detection
            self.detection_streak = 1
            return None

        prev_cx, prev_cy = self.pending_detection.center
        cx, cy = detection.center
        stable_label = self.pending_detection.label == detection.label
        stable_position = abs(prev_cx - cx) <= tolerance and abs(prev_cy - cy) <= tolerance

        if stable_label and stable_position:
            self.detection_streak += 1
        else:
            self.pending_detection = detection
            self.detection_streak = 1
            return None

        self.pending_detection = detection
        if self.detection_streak >= required_frames:
            return detection
        return None

    # 將單筆偵測結果畫到畫面上。
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

    # 將單筆偵測結果寫進記錄列表，供後續匯出使用。
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

    # 用主目標中心點與畫面中心的偏差，驅動雲台自動追蹤。
    def _apply_auto_tracking(self, frame_shape: tuple[int, int, int], detection: DetectionResult) -> None:
        now = time.monotonic()
        if now - self.last_tracking_command_at < self.config.tracking_command_interval_s:
            return

        frame_h, frame_w = frame_shape[:2]
        cx, cy = detection.center
        error_x = (cx - frame_w / 2.0) / (frame_w / 2.0)
        error_y = (cy - frame_h / 2.0) / (frame_h / 2.0)
        delta_pan = 0.0
        delta_tilt = 0.0

        if abs(error_x) > self.config.pan_deadband:
            pan_magnitude = min(
                self.config.pan_step_deg,
                max(self.config.pan_min_step_deg, abs(error_x) * self.config.pan_tracking_gain),
            )
            delta_pan = math.copysign(pan_magnitude, error_x) * self.config.pan_tracking_direction

        if abs(error_y) > self.config.tilt_deadband:
            tilt_magnitude = min(
                self.config.tilt_step_deg,
                max(self.config.tilt_min_step_deg, abs(error_y) * self.config.tilt_tracking_gain),
            )
            delta_tilt = math.copysign(tilt_magnitude, error_y) * self.config.tilt_tracking_direction

        if delta_pan == 0.0 and delta_tilt == 0.0:
            return

        if delta_pan != 0.0:
            self.controller.pan_by(delta_pan)
        if delta_tilt != 0.0:
            self.controller.tilt_by(delta_tilt)
        self.last_tracking_command_at = time.monotonic()

        self._log_event(
            "auto_tracking",
            {
                "error_x": round(error_x, 3),
                "error_y": round(error_y, 3),
                "delta_pan": round(delta_pan, 2),
                "delta_tilt": round(delta_tilt, 2),
                "pan_angle": round(self.controller.pan_angle, 2),
                "tilt_angle": round(self.controller.tilt_angle, 2),
            },
        )

    # 將 OpenCV 畫面更新到兩個預覽 QLabel。
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

    # 在沒有影像時顯示提示文字。
    def _render_placeholder(self, text: str) -> None:
        for label in (self.preview_label, self.live_preview_label):
            label.setText(text)
            label.setPixmap(QPixmap())

    # 累積一般事件紀錄，之後一起匯出。
    def _log_event(self, event: str, extra: dict[str, str | float | int]) -> None:
        row: dict[str, str | float | int] = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": event,
            "mode": self.current_mode,
        }
        row.update(extra)
        self.logs.append(row)

    # 關閉視窗時，統一釋放計時器、影像來源與控制器資源。
    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.frame_timer.stop()
        self._clear_video_clock()
        self.video_source.release()
        self.controller.close()
        super().closeEvent(event)
