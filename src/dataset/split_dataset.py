############################ 
# purpose: 分割資料集
# route: src/dataset/split_dataset.py
# 


import os
import random
import shutil
from pathlib import Path

random.seed(42)

RAW_BASE_DIR = Path("assets/raw")
IMAGE_SRC = RAW_BASE_DIR / "frames"
LABEL_SRC = RAW_BASE_DIR / "labels"

BASE_DIR = Path("assets/dataset")

IMAGE_TRAIN = BASE_DIR / "images/train"
IMAGE_VAL = BASE_DIR / "images/val"
IMAGE_TEST = BASE_DIR / "images/test"

LABEL_TRAIN = BASE_DIR / "labels/train"
LABEL_VAL = BASE_DIR / "labels/val"
LABEL_TEST = BASE_DIR / "labels/test"

# 建立資料夾
for p in [
    IMAGE_TRAIN, IMAGE_VAL, IMAGE_TEST,
    LABEL_TRAIN, LABEL_VAL, LABEL_TEST
]:
    p.mkdir(parents=True, exist_ok=True)

# 讀取圖片
image_files = [
    p for p in IMAGE_SRC.iterdir()
    if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
]

random.shuffle(image_files)

# 比例設定
train_ratio = 0.7
val_ratio = 0.2
test_ratio = 0.1

total = len(image_files)
train_count = int(total * train_ratio)
val_count = int(total * val_ratio)

train_files = image_files[:train_count]
val_files = image_files[train_count:train_count + val_count]
test_files = image_files[train_count + val_count:]

def copy_pair(img_path, target_img_dir, target_label_dir):
    label_path = LABEL_SRC / f"{img_path.stem}.txt"

    shutil.copy2(img_path, target_img_dir / img_path.name)

    if label_path.exists():
        shutil.copy2(label_path, target_label_dir / label_path.name)
    else:
        print(f"⚠️ 缺少標註：{label_path.name}")

# 分配資料
for img in train_files:
    copy_pair(img, IMAGE_TRAIN, LABEL_TRAIN)

for img in val_files:
    copy_pair(img, IMAGE_VAL, LABEL_VAL)

for img in test_files:
    copy_pair(img, IMAGE_TEST, LABEL_TEST)

print(f"train: {len(train_files)}")
print(f"val: {len(val_files)}")
print(f"test: {len(test_files)}")
print("資料分割完成")