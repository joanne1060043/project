############################ 
# purpose: 用鏡頭預覽模型成效
# route: src/test/cv.py
# 

import cv2
from ultralytics import YOLO
import numpy as np

# 模型路徑
model = YOLO(r"assets/model/20260423_rtx5080_640dpi_16batch_140k_img+1k_rc_v4.pt")

# 設定攝像頭
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

# 設定攝影機解析度
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# 建立可縮放視窗
cv2.namedWindow("YOLO Camera", cv2.WINDOW_NORMAL)

# 最大化視窗
cv2.setWindowProperty(
    "YOLO Camera",
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_NORMAL
)

# 設定初始大小（可調整）
cv2.resizeWindow("YOLO Camera", 1600, 900)

while True:
    ret, frame = cap.read()
    
    # ===== 3️⃣ 軟體防過曝（壓亮度）=====
    frame = cv2.convertScaleAbs(frame, alpha=0.8, beta=-25)

    if not ret:
        print("無法讀取影像")
        break

    results = model(
        frame, conf=0.15
    )
    r = results[0]

    annotated_frame = r.plot()

    cv2.imshow("YOLO Camera", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()