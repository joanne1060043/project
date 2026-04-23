############################ 
# 測試由程式旋轉的圖片對應標籤位置是否有偏移
# route: ./src/preprocessing/test_rotate.py
# 

import cv2
import random
from pathlib import Path

# =========================
# 路徑設定
# =========================
ROOT = Path(__file__).resolve().parent.parent          # yolo/
DATASET_DIR = ROOT / "dataset"
IMAGE_DIR = DATASET_DIR / "test" / "images"
LABEL_DIR = DATASET_DIR / "test" / "labels"

OUTPUT_DIR = Path(__file__).resolve().parent / "preview_rotate"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".bmp"]

# 想抽幾張來測試
SAMPLE_COUNT = 10

# 隨機旋轉角度範圍
ROTATE_MIN = -180
ROTATE_MAX = 180


# =========================
# 基本函式
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


def yolo_to_xyxy(box, img_w, img_h):
    cls_id, x, y, w, h = box
    x1 = int((x - w / 2) * img_w)
    y1 = int((y - h / 2) * img_h)
    x2 = int((x + w / 2) * img_w)
    y2 = int((y + h / 2) * img_h)
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

    return [cls_id, xc, yc, w, h]


def draw_boxes(image, boxes, color=(0, 255, 0), thickness=2, show_label=True):
    img_h, img_w = image.shape[:2]
    out = image.copy()

    for box in boxes:
        cls_id, x1, y1, x2, y2 = yolo_to_xyxy(box, img_w, img_h)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)

        if show_label:
            cv2.putText(
                out,
                f"id:{cls_id}",
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA
            )
    return out


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


def make_side_by_side(img1, img2):
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]

    target_h = max(h1, h2)

    def resize_keep_ratio(img, target_h):
        h, w = img.shape[:2]
        scale = target_h / h
        new_w = int(w * scale)
        return cv2.resize(img, (new_w, target_h))

    img1_r = resize_keep_ratio(img1, target_h)
    img2_r = resize_keep_ratio(img2, target_h)

    return cv2.hconcat([img1_r, img2_r])


def main():
    image_files = [p for p in IMAGE_DIR.iterdir() if p.is_file() and is_image_file(p)]

    if not image_files:
        print("找不到圖片，請確認 dataset/train/images 是否存在")
        return

    sample_count = min(SAMPLE_COUNT, len(image_files))
    selected = random.sample(image_files, sample_count)

    print(f"共抽樣 {sample_count} 張圖片做旋轉標籤檢查")
    print(f"輸出資料夾：{OUTPUT_DIR}")

    for idx, img_path in enumerate(selected, start=1):
        label_path = LABEL_DIR / f"{img_path.stem}.txt"

        image = cv2.imread(str(img_path))
        if image is None:
            print(f"[失敗] 無法讀取圖片: {img_path.name}")
            continue

        boxes = read_yolo_labels(label_path)
        angle = random.uniform(ROTATE_MIN, ROTATE_MAX)

        original_drawn = draw_boxes(image, boxes, color=(0, 255, 0))
        rotated_img, rotated_boxes = rotate_image_and_boxes(image, boxes, angle)
        rotated_drawn = draw_boxes(rotated_img, rotated_boxes, color=(0, 0, 255))

        merged = make_side_by_side(original_drawn, rotated_drawn)

        cv2.putText(
            merged,
            f"Left: Original  |  Right: Rotated ({angle:.2f} deg)",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        out_path = OUTPUT_DIR / f"{img_path.stem}_check.jpg"
        cv2.imwrite(str(out_path), merged)

        print(f"[{idx}/{sample_count}] 已輸出: {out_path.name} | angle={angle:.2f}")

    print("完成，請直接打開 preview_rotate 裡面的圖片檢查框線。")


if __name__ == "__main__":
    main()