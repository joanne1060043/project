from __future__ import annotations
import math
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np

CODE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CODE_DIR.parent


def resolve_default_model_path() -> str:
    model_dir = PROJECT_ROOT / "model"
    if model_dir.exists():
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

@dataclass
class DetectionResult:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    center: tuple[int, int]
    source: str


@dataclass
class AppConfig:
    model_path: str = resolve_default_model_path()
    target_label: str = "drone"
    confidence: float = 0.35
    pan_deadband: float = 0.10
    tilt_deadband: float = 0.08
    pan_step_deg: float = 6.0
    tilt_step_deg: float = 4.0
    tilt_limit_deg: float = 55.0
    update_interval_ms: int = 33

class DetectorEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.model = None
        self.backend_name = "mock"
        self._load_model()

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

    def detect(self, frame: np.ndarray, frame_index: int) -> DetectionResult | None:
        if self.model is not None:
            return self._detect_with_yolo(frame)
        return None

    def _detect_with_yolo(self, frame: np.ndarray) -> DetectionResult | None:
        try:
            results = self.model(frame, verbose=False)
            result = results[0]
        except Exception:
            return None

        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return None

        names = result.names
        best: DetectionResult | None = None
        best_score = -1.0

        for box in boxes:
            conf = float(box.conf[0])
            if conf < self.config.confidence:
                continue

            cls_id = int(box.cls[0])
            label_name = names.get(cls_id, cls_id) if isinstance(names, dict) else names[cls_id]
            label = str(label_name).lower()
            if self.config.target_label and self.config.target_label.lower() not in label:
                continue

            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            area = max(0, x2 - x1) * max(0, y2 - y1)
            score = area * conf
            if score > best_score:
                best_score = score
                best = DetectionResult(
                    label=label,
                    confidence=conf,
                    bbox=(x1, y1, x2, y2),
                    center=((x1 + x2) // 2, (y1 + y2) // 2),
                    source="YOLO",
                )

        return best

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

class VideoSource:
    def __init__(self) -> None:
        self.cap: cv2.VideoCapture | None = None
        self.mode = "mock"
        self.frame_index = 0
        self.path = ""

    def open_camera(self, camera_id: int = 0) -> bool:
        self.release()
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            self.mode = "mock"
            return False
        self.cap = cap
        self.mode = "camera"
        self.path = str(camera_id)
        self.frame_index = 0
        return True

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

    def rewind(self) -> None:
        if self.cap is not None and self.mode == "video":
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_index = 0

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

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
