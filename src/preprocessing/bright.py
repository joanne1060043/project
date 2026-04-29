import cv2
import numpy as np
from tqdm import tqdm

input_path = r"assets\raw\video\video_001.mp4"
output_path = r"assets\raw\video\output_clear_001.mp4"

cap = cv2.VideoCapture(input_path)

# 取得影片資訊
fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # ⭐ 總幀數

out = cv2.VideoWriter(
    output_path,
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (w, h)
)

# CLAHE
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

# ⭐ 建立進度條
pbar = tqdm(total=total_frames, desc="處理進度", unit="frame")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # ===== 1️⃣ 降噪 =====
    denoise = cv2.fastNlMeansDenoisingColored(frame, None, 5, 5, 7, 21)

    # ===== 2️⃣ CLAHE =====
    lab = cv2.cvtColor(denoise, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    l = clahe.apply(l)

    lab = cv2.merge((l, a, b))
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # ===== 3️⃣ 銳化 =====
    kernel = np.array([
        [0, -1, 0],
        [-1, 5.5, -1],
        [0, -1, 0]
    ])

    sharp = cv2.filter2D(enhanced, -1, kernel)

    out.write(sharp)

    # ⭐ 更新進度條
    pbar.update(1)

cap.release()
out.release()
pbar.close()

print("完成 ✅")