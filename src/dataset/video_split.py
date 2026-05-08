import subprocess
from pathlib import Path
import imageio_ffmpeg


# 取得目前這個 py 檔案所在資料夾
BASE_DIR = Path(__file__).resolve().parent

# 要分割的影片：src/dataset/videos/video_004.mp4
INPUT_VIDEO = BASE_DIR / "videos" / "video_004.mp4"

# 輸出資料夾：src/dataset/videos/split_output
OUTPUT_DIR = BASE_DIR / "videos" / "split_output"

# 檔名從 video_010.mp4 開始
START_NUMBER = 10

# 每段 60 秒
SEGMENT_SECONDS = 60


def split_video():
    if not INPUT_VIDEO.exists():
        raise FileNotFoundError(f"找不到影片：{INPUT_VIDEO}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    output_pattern = OUTPUT_DIR / "video_%03d.mp4"

    command = [
        ffmpeg_path,
        "-i", str(INPUT_VIDEO),
        "-map", "0",
        "-c", "copy",
        "-f", "segment",
        "-segment_time", str(SEGMENT_SECONDS),
        "-reset_timestamps", "1",
        "-segment_start_number", str(START_NUMBER),
        str(output_pattern)
    ]

    subprocess.run(command, check=True)

    print("影片分割完成")
    print(f"輸出位置：{OUTPUT_DIR}")
    print("檔名會從 video_010.mp4 開始")


if __name__ == "__main__":
    split_video()