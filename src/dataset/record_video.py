import cv2
import os
import re

# 儲存影片的資料夾：src/dataset/videos
SAVE_DIR = os.path.join(os.path.dirname(__file__), "videos")
os.makedirs(SAVE_DIR, exist_ok=True)


def get_next_video_name():
    files = os.listdir(SAVE_DIR)

    nums = []
    for f in files:
        match = re.match(r"video_(\d+)\.mp4", f)
        if match:
            nums.append(int(match.group(1)))

    next_num = max(nums) + 1 if nums else 1
    return os.path.join(SAVE_DIR, f"video_{next_num:03d}.mp4")


cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("無法開啟攝影機")
    exit()

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

recording = False
out = None

print("按 s 開始錄影")
print("按 e 結束錄影並存檔")
print("按 q 離開程式")

while True:
    ret, frame = cap.read()
    frame = cv2.convertScaleAbs(frame, alpha=0.8, beta=-50)
    if not ret:
        print("無法讀取攝影機畫面")
        break

    if recording:
        out.write(frame)
        cv2.putText(
            frame,
            "REC",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

    cv2.imshow("Record Video", frame)

    key = cv2.waitKey(1) & 0xFF

    # 按 s 開始錄影
    if key == ord("s") and not recording:
        filename = get_next_video_name()

        fps = 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
        recording = True

        print(f"開始錄影：{filename}")

    # 按 e 結束錄影
    elif key == ord("e") and recording:
        recording = False
        out.release()
        out = None

        print("錄影結束，已存檔")

    # 按 q 離開
    elif key == ord("q"):
        break

if recording and out is not None:
    out.release()

cap.release()
cv2.destroyAllWindows()