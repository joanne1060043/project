import time
import cv2
from s3 import TiltServoController
from camera import FaceTracker

# 1. 初始化硬體 (僅保留舵機與鏡頭)
tilt = TiltServoController(pin=12)
camera = FaceTracker(camera_id=1) # 若沒畫面請嘗試改為 0

# 2. 設定計時變數
last_action_time = time.time()
interval = 2.0  # 動作間隔 2 秒
state = 1       # 狀態標記

print("--- 系統啟動：僅執行鏡頭與舵機 ---")
print("提示：在影像視窗按 'q' 或終端機按 'Ctrl + C' 停止")


current_angle = 0  # 初始相對角度

try:
    while True:
        cx, cy, frame = camera.get_face_center()
        if frame is not None:
            cv2.putText(frame, f"Current Angle: {current_angle}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Live Monitor', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'): break
        
        # 按 'w' 增加 5 度
        elif key == ord('w'):
            current_angle = min(90, current_angle + 5)
            tilt.set_relative_angle(current_angle)
            print(f"手動調整：{current_angle} 度")
            
        # 按 's' 減少 5 度
        elif key == ord('s'):
            current_angle = max(-90, current_angle - 5)
            tilt.set_relative_angle(current_angle)
            print(f"手動調整：{current_angle} 度")

except KeyboardInterrupt:
    print("\n偵測到 Ctrl + C，啟動安全關閉程序...")

finally:
    # 僅釋放舵機與鏡頭資源
    tilt.close()
    camera.close()
    cv2.destroyAllWindows()
    print("硬體資源已釋放，系統已安全退出。")