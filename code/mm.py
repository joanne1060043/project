import time
import cv2
import lgpio
import sys
from s3 import TiltServoController
from camera import FaceTracker

# ==========================================
# 1. 馬達控制類別 (保持補償邏輯)
# ==========================================
class DCMotorController:
    def __init__(self, pin=17, speed=30):
        self.pin = pin
        self.speed = speed
        self.h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self.h, self.pin)
        self.DATA_MAP = [(0, 0), (7, 0.037), (13, 0.0555), (20, 0.074), (28, 0.0925), (35, 0.111), (46.5, 0.1295), (56, 0.148), (73, 0.1665), (80, 0.185)]

    def _calculate_time(self, angle):
        angle = abs(angle)
        if angle > self.DATA_MAP[-1][0]:
            a_max, t_max = self.DATA_MAP[-1]
            a_prev, t_prev = self.DATA_MAP[-2]
            return t_max + (angle - a_max) * ((t_max - t_prev) / (a_max - a_prev))
        for i in range(len(self.DATA_MAP) - 1):
            a_l, t_l = self.DATA_MAP[i]; a_h, t_h = self.DATA_MAP[i+1]
            if a_l <= angle <= a_h: return t_l + (angle - a_l) / (a_h - a_l) * (t_h - t_l)
        return 0

    def rotate(self, angle):
        run_sec = self._calculate_time(angle)
        if run_sec <= 0: return
        print(f"馬達轉動中：{angle}度 ({run_sec:.4f}s)")
        lgpio.tx_pwm(self.h, self.pin, 1000, self.speed)
        time.sleep(run_sec) # 執行短暫轉動
        lgpio.tx_pwm(self.h, self.pin, 1000, 0)

    def close(self):
        lgpio.tx_pwm(self.h, self.pin, 1000, 0)
        lgpio.gpiochip_close(self.h)

# ==========================================
# 2. 初始化與回呼函式
# ==========================================
motor = DCMotorController(pin=17)
tilt = TiltServoController(pin=12)
camera = FaceTracker(camera_id=0)

current_angle =0# 舵機相對角度
motor_target = 0   # 馬達拉桿數值

def on_motor_change(val):
    global motor_target
    motor_target = val

# 創建視窗與拉桿
cv2.namedWindow('Live Monitor')
cv2.createTrackbar('Motor Angle', 'Live Monitor', 0, 360, on_motor_change)

print("--- 系統啟動：全時流暢控制模式 ---")
print("W/S: 調整舵機 | 滑動拉桿: 調整馬達 | Q: 退出")

# ==========================================
# 3. 核心迴圈 (無阻塞模式)
# ==========================================
try:
    last_motor_val = 0
    
    while True:
        # 1. 抓取影像
        cx, cy, frame = camera.get_face_center()
        
        if frame is not None:
            # 顯示當前狀態
            cv2.putText(frame, f"Servo: {current_angle} | Motor Target: {motor_target}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Live Monitor', frame)
        
        # 2. 鍵盤偵測 (這部分現在跟你那段程式一樣流暢了)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'): 
            break
        elif key == ord('w'):
            current_angle = min(90, current_angle + 5)
            tilt.set_relative_angle(current_angle)
            print(f"舵機上調：{current_angle}")
        elif key == ord('s'):
            current_angle = max(-90, current_angle - 5)
            tilt.set_relative_angle(current_angle)
            print(f"舵機下調：{current_angle}")

        # 3. 馬達指令偵測 (當你放開拉桿或數值變動時執行)
        # 為了避免連續觸發，可以按一下空白鍵才執行馬達轉動，或偵測數值變化
        if key == ord(' '): # 按空白鍵執行拉桿設定的角度
            if motor_target > 0:
                motor.rotate(motor_target)
                # 執行完歸零拉桿 (可選)
                cv2.setTrackbarPos('Motor Angle', 'Live Monitor', 0)
                motor_target = 0

except KeyboardInterrupt:
    pass

finally:
    motor.close()
    tilt.close()
    camera.close()
    cv2.destroyAllWindows()
    print("系統安全退出。")