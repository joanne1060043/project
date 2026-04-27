import os
from ultralytics import YOLO

# 路徑設定
MODEL_PATH = r"assets/model/20260423_rtx5080_640dpi_16batch_140k_img+1k_rc_v4.pt"
IMAGE_DIR = "assets/raw/frames"
LABEL_DIR = "assets/raw/labels"

# 信心值門檻，越高越保守
CONF_THRESHOLD = 0.1

os.makedirs(LABEL_DIR, exist_ok=True)

model = YOLO(MODEL_PATH)

image_files = [
    f for f in os.listdir(IMAGE_DIR)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]

for img_name in image_files:
    img_path = os.path.join(IMAGE_DIR, img_name)

    label_name = os.path.splitext(img_name)[0] + ".txt"
    label_path = os.path.join(LABEL_DIR, label_name)

    # 如果已經有人工標註，就跳過，避免覆蓋
    if os.path.exists(label_path):
        print(f"跳過已存在標註：{label_name}")
        continue

    results = model.predict(
        source=img_path,
        conf=CONF_THRESHOLD,
        save=False,
        verbose=False
    )
    boxes = results[0].boxes

    with open(label_path, "w", encoding="utf-8") as f:
        for box in boxes:
            cls_id = int(box.cls[0])
            x_center, y_center, width, height = box.xywhn[0]

            f.write(
                f"{cls_id} "
                f"{x_center:.6f} "
                f"{y_center:.6f} "
                f"{width:.6f} "
                f"{height:.6f}\n"
            )

    print(f"完成：{img_name} → {label_name}")

print("全部自動標註完成")