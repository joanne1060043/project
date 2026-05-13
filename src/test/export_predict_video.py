############################ 
# purpose: 匯出模型預測影片
# route: src/test/export_predict_video.py
# 

import cv2
import torch
from ultralytics import YOLO

# 載入模型
model = YOLO(r"assets/model/20260511_rtx5080_640dpi_24batch_140k_img+2k_rc+1k_2rc_v8.pt")

# 嘗試使用 GPU
device = 0 if torch.cuda.is_available() else "cpu"
print("使用裝置：", "GPU CUDA" if device == 0 else "CPU")

# 影片路徑
video_path = "assets/raw/video/video_002.mp4"
output_path = "assets/raw/video/video_002_predicted_v8.mp4"

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("無法開啟影片")
    exit()

# 取得影片資訊
fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

if fps <= 0:
    fps = 30

# 建立輸出影片
out = cv2.VideoWriter(
    output_path,
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (w, h)
)

if not out.isOpened():
    print("無法建立輸出影片")
    cap.release()
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("影片處理完成")
        break

    # ===== 可選：亮度調整 =====
    frame = cv2.convertScaleAbs(frame, alpha=0.8, beta=-25)

    # ===== YOLO 推論，使用 GPU / CPU =====
    results = model(frame, conf=0.15, device=device)

    # ===== 畫框 =====
    annotated = results[0].plot()

    # ===== 寫入輸出影片 =====
    out.write(annotated)

    # ===== 可選：即時預覽 =====
    cv2.imshow("YOLO Video Test", annotated)

    # 按 q 提前結束
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
out.release()
cv2.destroyAllWindows()

print("輸出完成：", output_path)