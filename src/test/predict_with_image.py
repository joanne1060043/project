import cv2
from ultralytics import YOLO

# 載入模型
model = YOLO(r"assets/model/20260423_rtx5080_640dpi_16batch_140k_img+1k_rc_v4.pt")

# 讀取圖片
img_path = r"assets\raw\frames\frame_000714.jpg"   # ← 改成你的圖片路徑
frame = cv2.imread(img_path)

if frame is None:
    print("圖片讀取失敗")
    exit()

# （可選）亮度調整
frame = cv2.convertScaleAbs(frame, alpha=0.8, beta=-25)

# 推論
results = model(frame, conf=0.15)

# 畫框
annotated = results[0].plot()

# 顯示
cv2.imshow("YOLO Test Image", annotated)
cv2.waitKey(0)
cv2.destroyAllWindows()