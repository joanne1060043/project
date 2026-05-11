import cv2
import os
from pathlib import Path
import numpy as np

# =========================
# 基本設定
# =========================

# 6分鐘影片路徑
VIDEO_PATH = Path("src/dataset/videos/video_6min.mp4")

# 存到原本16分鐘影片的資料夾
OUTPUT_DIR = Path("src/dataset/frames/video_16min_2m30s_to_3m00s")

# 擷取時間：1分00秒 到 2分10秒
START_TIME_SEC = 1 * 60 + 0
END_TIME_SEC = 2 * 60 + 10

# 擷取張數
TARGET_FRAME_COUNT = 500

# 從第501張開始命名
START_IMAGE_INDEX = 501

IMAGE_PREFIX = "drone"
IMAGE_EXT = ".jpg"
JPG_QUALITY = 95


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cap = cv2.VideoCapture(str(VIDEO_PATH))

    if not cap.isOpened():
        print(f"❌ 無法開啟影片：{VIDEO_PATH}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps

    print("========== 影片資訊 ==========")
    print(f"影片路徑：{VIDEO_PATH}")
    print(f"FPS：{fps}")
    print(f"總幀數：{total_frames}")
    print(f"影片長度：約 {video_duration:.2f} 秒")
    print("==============================")

    start_frame = int(START_TIME_SEC * fps)
    end_frame = int(END_TIME_SEC * fps)

    if start_frame >= total_frames:
        print("❌ 起始時間超過影片長度")
        cap.release()
        return

    if end_frame > total_frames:
        end_frame = total_frames

    available_frames = end_frame - start_frame

    if available_frames <= 0:
        print("❌ 擷取區間錯誤")
        cap.release()
        return

    print(f"擷取區間：{START_TIME_SEC} 秒 到 {END_TIME_SEC} 秒")
    print(f"對應幀數：{start_frame} 到 {end_frame}")
    print(f"區間內總幀數：約 {available_frames} 張")

    if available_frames < TARGET_FRAME_COUNT:
        selected_frames = list(range(start_frame, end_frame))
        print(f"⚠️ 區間內不足 {TARGET_FRAME_COUNT} 張，將擷取全部 {len(selected_frames)} 張")
    else:
        selected_frames = np.linspace(
            start_frame,
            end_frame - 1,
            TARGET_FRAME_COUNT,
            dtype=int
        )
        selected_frames = sorted(set(selected_frames))

    saved_count = 0

    for frame_index in selected_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = cap.read()

        if not ret:
            print(f"⚠️ 第 {frame_index} 幀讀取失敗，跳過")
            continue

        image_number = START_IMAGE_INDEX + saved_count
        image_name = f"{IMAGE_PREFIX}_{image_number:04d}{IMAGE_EXT}"
        save_path = OUTPUT_DIR / image_name

        # 避免覆蓋原本圖片
        if save_path.exists():
            print(f"⚠️ 檔案已存在，跳過：{save_path}")
            saved_count += 1
            continue

        cv2.imwrite(
            str(save_path),
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY]
        )

        saved_count += 1

        if saved_count % 50 == 0:
            print(f"已處理 {saved_count} 張...")

    cap.release()

    print("========== 完成 ==========")
    print(f"已處理：{saved_count} 張圖片")
    print(f"輸出資料夾：{OUTPUT_DIR}")
    print(f"檔名範圍：約 drone_{START_IMAGE_INDEX:04d}.jpg 到 drone_{START_IMAGE_INDEX + saved_count - 1:04d}.jpg")
    print("==========================")


if __name__ == "__main__":
    main()