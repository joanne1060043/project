############################ 
# purpose: 將影片分割成圖片
# route: src/dataset/extract_frames.py
# 

import cv2
import os

VIDEO_DIR = r"assets\raw\video"
SAVE_DIR = r"assets\raw\frames"

TARGET_IMAGES = 2000  # 總共大約抓 2000 張

os.makedirs(SAVE_DIR, exist_ok=True)

video_files = sorted([
    f for f in os.listdir(VIDEO_DIR)
    if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
])

if not video_files:
    print("找不到影片")
    exit()

# 先計算兩個影片總幀數
total_frames = 0
video_infos = []

for video_file in video_files:
    video_path = os.path.join(VIDEO_DIR, video_file)
    cap = cv2.VideoCapture(video_path)

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_frames += frame_count

    video_infos.append((video_file, video_path, frame_count))
    cap.release()

# 自動計算每隔幾幀抓一張
frame_interval = max(1, total_frames // TARGET_IMAGES)

print(f"找到 {len(video_files)} 個影片")
print(f"總幀數：約 {total_frames}")
print(f"預計每 {frame_interval} 幀抓 1 張")
print(f"目標張數：約 {TARGET_IMAGES}")

img_count = 0

for video_file, video_path, frame_count in video_infos:
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"無法開啟影片：{video_file}")
        continue

    frame_id = 0

    print(f"\n開始處理：{video_file}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_id % frame_interval == 0:
            filename = f"frame_{img_count:06d}.jpg"
            save_path = os.path.join(SAVE_DIR, filename)

            cv2.imwrite(save_path, frame)
            img_count += 1

            if img_count >= TARGET_IMAGES:
                break

        frame_id += 1

    cap.release()

    if img_count >= TARGET_IMAGES:
        break

print(f"\n完成，共輸出 {img_count} 張圖片")
print(f"儲存位置：{SAVE_DIR}")