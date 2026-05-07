import cv2
from ultralytics import YOLO

# 載入模型
model = YOLO(r"model\20260429_rtx5080_640dpi_24batch_140k_img+2k_rc_500epoch_v7.pt")

# 影片路徑
video_path = r"assets\raw\video\video_001.mp4"

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("無法開啟影片")
    exit()

# 取得影片資訊（可選）
fps = cap.get(cv2.CAP_PROP_FPS)
delay = int(1000 / fps) if fps > 0 else 30

while True:
    ret, frame = cap.read()
    if not ret:
        print("影片播放結束")
        break

    # ===== 可選：亮度調整 =====
    frame = cv2.convertScaleAbs(frame, alpha=0.8, beta=-25)

    # ===== YOLO 推論 =====
    results = model(frame, conf=0.15)

    # ===== 畫框 =====
    annotated = results[0].plot()

    # ===== 顯示 =====
    cv2.imshow("YOLO Video Test", annotated)

    # 按 q 離開
    if cv2.waitKey(delay) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()