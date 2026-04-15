import cv2
from ultralytics import YOLO

# 載入模型
model = YOLO("test/best.pt")

# 開啟攝影機
cap = cv2.VideoCapture(1)

while True:
    ret, frame = cap.read()

    if not ret:
        print("無法讀取影像，請檢查攝像頭")
        break

    # YOLO 預測
    results = model(
        frame,
        conf=0.5
    )

    r = results[0]

    # ===== 印出座標 =====
    if r.boxes is not None:
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()   # 左上右下座標
            conf = box.conf[0].item()               # 信心值
            cls = int(box.cls[0].item())            # 類別id
            name = r.names[cls]                     # 類別名稱

            print(
                f"{name} | conf={conf:.2f} | "
                f"x1={int(x1)}, y1={int(y1)}, x2={int(x2)}, y2={int(y2)}"
            )

    # 畫框
    annotated_frame = r.plot()

    # 顯示畫面
    cv2.imshow("YOLO Camera", annotated_frame)

    # 按 q 離開
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()