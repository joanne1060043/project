from __future__ import annotations
import math
import platform
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np

# 專案路徑與預設模型設定。
CODE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CODE_DIR.parent
PREFERRED_MODEL_NAME = "20260511_rtx5080_640dpi_24batch_140k_img+2k_rc+1k_2rc_v8.pt"


# 先找指定模型，再退回最新權重，最後才使用備援模型名稱。
def resolve_default_model_path() -> str:
    model_dir = PROJECT_ROOT / "model"
    if model_dir.exists():
        preferred_model = model_dir / PREFERRED_MODEL_NAME
        if preferred_model.exists():
            return str(preferred_model)
        model_candidates = sorted(model_dir.glob("*.pt"), key=lambda path: path.stat().st_mtime, reverse=True)
        if model_candidates:
            return str(model_candidates[0])

    root_candidates = sorted(PROJECT_ROOT.glob("*.pt"), key=lambda path: path.stat().st_mtime, reverse=True)
    if root_candidates:
        return str(root_candidates[0])

    return str(PROJECT_ROOT / "yolo11n.pt")


try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover
    YOLO = None


# 單一偵測框的標準資料格式，供 UI 與記錄匯出共用。
@dataclass
class DetectionResult:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    center: tuple[int, int]
    source: str


# 偵測、追蹤與影片播放會共用的主要設定。
@dataclass
class AppConfig:
    model_path: str = resolve_default_model_path()
    target_label: str = "drone"
    video_confidence: float = 0.35
    camera_confidence: float = 0.50
    camera_confirmation_frames: int = 1
    pan_deadband: float = 0.10
    tilt_deadband: float = 0.08
    pan_step_deg: float = 6.0
    tilt_step_deg: float = 4.0
    tilt_limit_deg: float = 55.0
    update_interval_ms: int = 33


# YOLO 偵測引擎，負責載入模型並回傳整理好的 DetectionResult。
class DetectorEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.model = None
        self.backend_name = "mock"
        self._load_model()

    # 載入模型；失敗時保留 mock 狀態，避免整個 UI 啟動失敗。
    def _load_model(self) -> None:
        model_path = Path(self.config.model_path)
        if YOLO is None or not model_path.exists():
            self.backend_name = "mock"
            return

        try:
            self.model = YOLO(str(model_path))
            self.backend_name = "yolo"
        except Exception:
            self.model = None
            self.backend_name = "mock"

    # 只取最佳的一個偵測結果，提供舊流程或單目標追蹤使用。
    def detect(self, frame: np.ndarray, frame_index: int, min_confidence: float | None = None) -> DetectionResult | None:
        detections = self.detect_all(frame, frame_index, min_confidence=min_confidence)
        return detections[0] if detections else None

    # 回傳目前畫面中的所有有效偵測框。
    def detect_all(self, frame: np.ndarray, frame_index: int, min_confidence: float | None = None) -> list[DetectionResult]:
        if self.model is not None:
            return self._detect_with_yolo_all(frame, min_confidence=min_confidence)
        return []

    # 執行 YOLO 推論，並只保留符合目標類別與信心門檻的結果。
    def _detect_with_yolo_all(self, frame: np.ndarray, min_confidence: float | None = None) -> list[DetectionResult]:
        try:
            results = self.model(frame, verbose=False)
            result = results[0]
        except Exception:
            return []

        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        names = result.names
        detections: list[tuple[float, DetectionResult]] = []
        confidence_threshold = self.config.video_confidence if min_confidence is None else min_confidence

        for box in boxes:
            conf = float(box.conf[0])
            if conf < confidence_threshold:
                continue

            cls_id = int(box.cls[0])
            label_name = names.get(cls_id, cls_id) if isinstance(names, dict) else names[cls_id]
            label = str(label_name).lower()
            if self.config.target_label and self.config.target_label.lower() not in label:
                continue

            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            area = max(0, x2 - x1) * max(0, y2 - y1)
            score = area * conf
            detections.append(
                (
                    score,
                    DetectionResult(
                        label=label,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center=((x1 + x2) // 2, (y1 + y2) // 2),
                        source="YOLO",
                    ),
                )
            )

        detections.sort(key=lambda item: item[0], reverse=True)
        return [detection for _, detection in detections]

    # 備援假資料，主要用於沒有真實影像來源時的畫面展示。
    def _detect_with_mock(self, frame: np.ndarray, frame_index: int) -> DetectionResult:
        height, width = frame.shape[:2]
        box_w = max(96, width // 7)
        box_h = max(72, height // 8)
        x_center = int(width * 0.5 + math.sin(frame_index / 18.0) * width * 0.22)
        y_center = int(height * 0.5 + math.cos(frame_index / 24.0) * height * 0.18)
        x1 = max(0, x_center - box_w // 2)
        y1 = max(0, y_center - box_h // 2)
        x2 = min(width - 1, x1 + box_w)
        y2 = min(height - 1, y1 + box_h)
        return DetectionResult(
            label=self.config.target_label or "drone",
            confidence=0.82,
            bbox=(x1, y1, x2, y2),
            center=((x1 + x2) // 2, (y1 + y2) // 2),
            source="Mock",
        )


# 影像來源管理器，統一處理攝影機、影片與 mock 畫面。
class VideoSource:
    def __init__(self) -> None:
        self.cap: cv2.VideoCapture | None = None
        self.mode = "mock"
        self.frame_index = 0
        self.path = ""
        self.camera_backend = "unknown"

    def _camera_candidates(self, preferred_camera_id: int) -> list[tuple[int, int | None, str]]:
        system = platform.system().lower()
        camera_ids: list[int] = []
        for candidate in (preferred_camera_id, 0, 1):
            if candidate not in camera_ids:
                camera_ids.append(candidate)

        backends: list[tuple[int | None, str]]
        if system == "windows":
            backends = [
                (cv2.CAP_DSHOW, "DirectShow"),
                (cv2.CAP_MSMF, "MSMF"),
                (None, "OpenCV default"),
            ]
        elif system == "linux":
            backends = [
                (cv2.CAP_V4L2, "V4L2"),
                (None, "OpenCV default"),
            ]
        else:
            backends = [(None, "OpenCV default")]

        return [(camera_id, backend, backend_name) for camera_id in camera_ids for backend, backend_name in backends]

    # 連接攝影機；目前固定偏向外接攝影機的索引與 DSHOW 後端。
    def open_camera(self, camera_id: int = 0) -> bool:
        self.release()
        for candidate_id, backend, backend_name in self._camera_candidates(camera_id):
            cap = cv2.VideoCapture(candidate_id) if backend is None else cv2.VideoCapture(candidate_id, backend)
            if not cap.isOpened():
                cap.release()
                continue

            self.cap = cap
            self.mode = "camera"
            self.path = str(candidate_id)
            self.frame_index = 0
            self.camera_backend = backend_name
            return True

        self.mode = "mock"
        self.camera_backend = "unavailable"
        return False

    # 開啟本地影片檔，供 Mode 1 播放與辨識。
    def open_video(self, path: str) -> bool:
        self.release()
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            self.mode = "mock"
            return False
        self.cap = cap
        self.mode = "video"
        self.path = path
        self.frame_index = 0
        return True

    # 將影片播放位置重設回第一幀。
    def rewind(self) -> None:
        if self.cap is not None and self.mode == "video":
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_index = 0

    # 取得影片 fps；非影片模式時回傳 0。
    def get_fps(self) -> float:
        if self.cap is None or self.mode != "video":
            return 0.0
        fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        return fps if fps > 0 else 0.0

    # 取得影片總幀數。
    def get_frame_count(self) -> int:
        if self.cap is None or self.mode != "video":
            return 0
        total = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return max(0, total)

    # 取得目前播放到哪一幀。
    def get_current_frame(self) -> int:
        if self.cap is None or self.mode != "video":
            return 0
        current = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        return max(0, current)

    # 直接跳到指定幀，供拖曳進度條與停止後回到起點使用。
    def seek_to_frame(self, frame_index: int) -> bool:
        if self.cap is None or self.mode != "video":
            return False
        total = self.get_frame_count()
        if total > 0:
            frame_index = max(0, min(frame_index, total - 1))
        else:
            frame_index = max(0, frame_index)
        ok = self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        if ok:
            self.frame_index = frame_index
        return bool(ok)

    # 依秒數做前後快轉。
    def seek_by_seconds(self, delta_seconds: float) -> bool:
        fps = self.get_fps()
        if fps <= 0:
            return False
        current = self.get_current_frame()
        delta_frames = int(round(delta_seconds * fps))
        return self.seek_to_frame(current + delta_frames)

    # 讀取影片第一幀，通常用在停止播放後顯示初始畫面。
    def read_first_frame(self) -> np.ndarray | None:
        if self.cap is None or self.mode != "video":
            return None
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = self.cap.read()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.frame_index = 0
        if ok:
            return frame
        return None

    # 讀取下一幀；影片播完時會回到開頭，沒有來源時改用 mock 畫面。
    def read(self) -> tuple[bool, np.ndarray]:
        if self.cap is not None:
            ok, frame = self.cap.read()
            if ok:
                self.frame_index += 1
                return True, frame
            if self.mode == "video":
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
                if ok:
                    self.frame_index += 1
                    return True, frame
            self.release()

        self.mode = "mock"
        self.frame_index += 1
        return True, self._generate_mock_frame()

    # 產生簡單的 mock 預覽畫面，方便沒有實體來源時測 UI。
    def _generate_mock_frame(self) -> np.ndarray:
        width, height = 1280, 720
        frame = np.full((height, width, 3), 240, dtype=np.uint8)
        for x in range(0, width, 80):
            cv2.line(frame, (x, 0), (x, height), (225, 225, 225), 1)
        for y in range(0, height, 80):
            cv2.line(frame, (0, y), (width, y), (225, 225, 225), 1)

        x = int(width * 0.5 + math.sin(self.frame_index / 18.0) * width * 0.22)
        y = int(height * 0.5 + math.cos(self.frame_index / 24.0) * height * 0.18)
        size = 34
        pts = np.array([[x, y - size], [x + size, y], [x, y + size], [x - size, y]], np.int32)
        cv2.fillConvexPoly(frame, pts, (55, 55, 55))
        cv2.putText(frame, "Mock Live Feed", (34, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (40, 40, 40), 2)
        return frame

    # 釋放目前的 OpenCV capture 資源。
    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
