############################
# USB 攝影機 Raspberry Pi 5 版本
# route: ./src/test/cv.py

import cv2
from ultralytics import YOLO
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = ROOT_DIR / "model" / "20260429_rtx5080_640dpi_24batch_140k_img+2k_rc_500epoch_v7.pt"

model = YOLO(str(MODEL_PATH))

# Linux / Raspberry Pi 用 V4L2，不要用 CAP_DSHOW
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

if not cap.isOpened():
    raise RuntimeError("無法開啟攝影機，請確認 USB 攝影機是否為 /dev/video0")

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

cv2.namedWindow("YOLO Camera", cv2.WINDOW_NORMAL)
cv2.resizeWindow("YOLO Camera", 1280, 720)

try:
    while True:
        ret, frame = cap.read()

        if not ret:
            print("無法讀取影像")
            break

        # 軟體防過曝
        frame = cv2.convertScaleAbs(frame, alpha=0.8, beta=-25)

        results = model(
            frame,
            conf=0.15,
            imgsz=640,
            verbose=False
        )

        annotated_frame = results[0].plot()

        cv2.imshow("YOLO Camera", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()