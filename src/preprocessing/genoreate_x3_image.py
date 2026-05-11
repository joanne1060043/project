############################ 
# purpose: 預生成旋轉、曝光、昏暗、模糊、雜訊等圖片，生成後將會有 8倍量圖片
# route: src/preprocessing/x3.py
# 

import os
import cv2
import random
from pathlib import Path

# 基本設定
ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "assets" / "dataset"

# 建議先只處理 train
SPLITS = ["train"]

IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".bmp"]

# 隨機旋轉角度範圍
ROTATE_MIN = -60
ROTATE_MAX = 60

# 每張圖是否做這些增強
ENABLE_GRAY = True
ENABLE_BLUR = True
ENABLE_EXPOSURE = True
ENABLE_ROTATE = True

# 模糊核大小（奇數）
BLUR_KERNEL = 5

# 曝光設定
EXPOSURE_SETTINGS = [
    ("bright", 1.1, 25),
    ("dark", 0.9, -25),
]


# =========================
# 工具函式
# =========================
def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def read_yolo_labels(label_path: Path):
    boxes = []
    if not label_path.exists():
        return boxes

    with open(label_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            cls_id = int(float(parts[0]))
            x, y, w, h = map(float, parts[1:])
            boxes.append([cls_id, x, y, w, h])
    return boxes


def write_yolo_labels(label_path: Path, boxes):
    with open(label_path, "w", encoding="utf-8") as f:
        for cls_id, x, y, w, h in boxes:
            f.write(f"{cls_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")


def yolo_to_xyxy(box, img_w, img_h):
    cls_id, x, y, w, h = box
    x1 = (x - w / 2) * img_w
    y1 = (y - h / 2) * img_h
    x2 = (x + w / 2) * img_w
    y2 = (y + h / 2) * img_h
    return cls_id, x1, y1, x2, y2


def xyxy_to_yolo(cls_id, x1, y1, x2, y2, img_w, img_h):
    x1 = max(0, min(x1, img_w - 1))
    y1 = max(0, min(y1, img_h - 1))
    x2 = max(0, min(x2, img_w - 1))
    y2 = max(0, min(y2, img_h - 1))

    bw = x2 - x1
    bh = y2 - y1
    if bw <= 1 or bh <= 1:
        return None

    xc = (x1 + x2) / 2 / img_w
    yc = (y1 + y2) / 2 / img_h
    w = bw / img_w
    h = bh / img_h

    if w <= 0 or h <= 0:
        return None

    return [cls_id, xc, yc, w, h]


def make_gray(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def make_blur(image, ksize=5):
    return cv2.GaussianBlur(image, (ksize, ksize), 0)


def adjust_exposure(image, alpha=1.0, beta=0):
    return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)


def rotate_image_and_boxes(image, boxes, angle_deg):
    h, w = image.shape[:2]
    cx, cy = w / 2, h / 2

    M = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)

    cos_val = abs(M[0, 0])
    sin_val = abs(M[0, 1])

    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))

    M[0, 2] += (new_w / 2) - cx
    M[1, 2] += (new_h / 2) - cy

    rotated = cv2.warpAffine(
        image,
        M,
        (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(114, 114, 114)
    )

    new_boxes = []

    for box in boxes:
        cls_id, x1, y1, x2, y2 = yolo_to_xyxy(box, w, h)

        corners = [
            [x1, y1],
            [x2, y1],
            [x2, y2],
            [x1, y2]
        ]

        transformed = []
        for x, y in corners:
            new_x = M[0, 0] * x + M[0, 1] * y + M[0, 2]
            new_y = M[1, 0] * x + M[1, 1] * y + M[1, 2]
            transformed.append([new_x, new_y])

        xs = [p[0] for p in transformed]
        ys = [p[1] for p in transformed]

        nx1, ny1 = min(xs), min(ys)
        nx2, ny2 = max(xs), max(ys)

        converted = xyxy_to_yolo(cls_id, nx1, ny1, nx2, ny2, new_w, new_h)
        if converted is not None:
            new_boxes.append(converted)

    return rotated, new_boxes


def save_augmented(image, boxes, image_out_path: Path, label_out_path: Path):
    cv2.imwrite(str(image_out_path), image)
    write_yolo_labels(label_out_path, boxes)


def print_progress(current, total, split_name, file_name):
    percent = (current / total) * 100 if total > 0 else 100
    print(f"[{split_name}] 進度: {current}/{total} ({percent:.2f}%) - {file_name}")


# =========================
# 主流程
# =========================
def process_split(split_name):
    img_dir = DATASET_DIR / split_name / "images"
    lbl_dir = DATASET_DIR / split_name / "labels"

    if not img_dir.exists() or not lbl_dir.exists():
        print(f"[跳過] {split_name} 不存在")
        return

    image_files = [p for p in img_dir.iterdir() if p.is_file() and is_image_file(p)]
    total = len(image_files)

    print(f"\n=== 開始處理 {split_name}，共 {total} 張 ===")

    for idx, img_path in enumerate(image_files, start=1):
        print_progress(idx, total, split_name, img_path.name)

        label_path = lbl_dir / f"{img_path.stem}.txt"
        image = cv2.imread(str(img_path))

        if image is None:
            print(f"[失敗] 無法讀取圖片: {img_path}")
            continue

        boxes = read_yolo_labels(label_path)

        # 1. 灰階
        if ENABLE_GRAY:
            gray_img = make_gray(image)
            gray_img_path = img_dir / f"{img_path.stem}_gray{img_path.suffix}"
            gray_lbl_path = lbl_dir / f"{img_path.stem}_gray.txt"
            save_augmented(gray_img, boxes, gray_img_path, gray_lbl_path)

        # 2. 模糊
        if ENABLE_BLUR:
            blur_img = make_blur(image, BLUR_KERNEL)
            blur_img_path = img_dir / f"{img_path.stem}_blur{img_path.suffix}"
            blur_lbl_path = lbl_dir / f"{img_path.stem}_blur.txt"
            save_augmented(blur_img, boxes, blur_img_path, blur_lbl_path)

        # 3. 曝光
        if ENABLE_EXPOSURE:
            for exp_name, alpha, beta in EXPOSURE_SETTINGS:
                exp_img = adjust_exposure(image, alpha=alpha, beta=beta)
                exp_img_path = img_dir / f"{img_path.stem}_{exp_name}{img_path.suffix}"
                exp_lbl_path = lbl_dir / f"{img_path.stem}_{exp_name}.txt"
                save_augmented(exp_img, boxes, exp_img_path, exp_lbl_path)

        # 4. 隨機旋轉
        if ENABLE_ROTATE:
            angle = random.uniform(ROTATE_MIN, ROTATE_MAX)
            rot_img, rot_boxes = rotate_image_and_boxes(image, boxes, angle)

            angle_tag = f"{angle:.1f}".replace("-", "m").replace(".", "p")
            rot_img_path = img_dir / f"{img_path.stem}_rot_{angle_tag}{img_path.suffix}"
            rot_lbl_path = lbl_dir / f"{img_path.stem}_rot_{angle_tag}.txt"
            save_augmented(rot_img, rot_boxes, rot_img_path, rot_lbl_path)

    print(f"=== {split_name} 處理完成 ===")


def main():
    print(f"資料集根目錄: {DATASET_DIR}")
    for split in SPLITS:
        process_split(split)
    print("\n全部處理完成。")


if __name__ == "__main__":
    main()