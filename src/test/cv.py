############################ 
# 鏡頭測試模型
# route: ./src/test/cv.py
# 

import cv2
from ultralytics import YOLO
import numpy as np

model = YOLO(r"model\20260423_rtx5080_640dpi_16batch_140k_v3_50_last.pt")

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

    # ===== 4️⃣ 降噪（去雜訊）=====
    frame = cv2.GaussianBlur(frame, (3, 3), 0)

    # ===== 5️⃣ 銳化（提升清晰度）=====
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    frame = cv2.filter2D(frame, -1, kernel)

    # ===== 6️⃣ CLAHE（局部對比增強）=====
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l = clahe.apply(l)

    lab = cv2.merge((l,a,b))
    frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

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