############################ 
# 將圖片分割成三等份：訓練、測試、驗證
# route: ./src/preprocessing/take_pictures.py
# 

import os
import random
import shutil
from pathlib import Path

# ===== 設定 =====

SOURCE_DIR = "./assets/raw"      # 原始資料夾
OUTPUT_DIR = "./assets/dataset"  # 輸出資料夾

TRAIN_RATIO = 0.7
VAL_RATIO = 0.2
TEST_RATIO = 0.1

IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".bmp"]

SEED = 42

# =================


def main():

    random.seed(SEED)

    image_dir = Path(SOURCE_DIR) / "images"
    label_dir = Path(SOURCE_DIR) / "labels"

    if not image_dir.exists():
        print("找不到 images 資料夾")
        return

    if not label_dir.exists():
        print("找不到 labels 資料夾")
        return

    # 找所有圖片
    images = []

    for ext in IMAGE_EXTS:
        images.extend(image_dir.glob(f"*{ext}"))

    images = sorted(images)

    print("圖片數量:", len(images))

    # 確認每張圖都有標註
    valid_files = []

    for img_path in images:

        label_path = label_dir / (img_path.stem + ".txt")

        if label_path.exists():
            valid_files.append(img_path.stem)
        else:
            print("缺少標註:", img_path.name)

    print("有效配對:", len(valid_files))

    # 隨機打亂
    random.shuffle(valid_files)

    total = len(valid_files)

    train_count = int(total * TRAIN_RATIO)
    val_count = int(total * VAL_RATIO)

    train_set = valid_files[:train_count]
    val_set = valid_files[train_count:train_count + val_count]
    test_set = valid_files[train_count + val_count:]

    print("\n切分結果")
    print("train:", len(train_set))
    print("val:", len(val_set))
    print("test:", len(test_set))

    # 建立資料夾
    for split in ["train", "val", "test"]:

        os.makedirs(
            Path(OUTPUT_DIR) / "images" / split,
            exist_ok=True
        )

        os.makedirs(
            Path(OUTPUT_DIR) / "labels" / split,
            exist_ok=True
        )

    # 複製
    def copy_split(file_list, split):

        for name in file_list:

            img_src = image_dir / (name + ".jpg")
            label_src = label_dir / (name + ".txt")

            # 如果不是 jpg 嘗試其他副檔名
            if not img_src.exists():
                for ext in IMAGE_EXTS:
                    alt = image_dir / (name + ext)
                    if alt.exists():
                        img_src = alt
                        break

            shutil.copy2(
                img_src,
                Path(OUTPUT_DIR) / "images" / split / img_src.name
            )

            shutil.copy2(
                label_src,
                Path(OUTPUT_DIR) / "labels" / split / label_src.name
            )

    copy_split(train_set, "train")
    copy_split(val_set, "val")
    copy_split(test_set, "test")

    print("\n完成")
    print("輸出位置:", OUTPUT_DIR)


if __name__ == "__main__":
    main()