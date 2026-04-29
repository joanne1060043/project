# main.py
import time
import cv2
from motor import DCMotorController
from servo import TiltServoController
from camera import FaceTracker

motor = DCMotorController(pin=17)
tilt = TiltServoController(pin=12)
tracker = FaceTracker(camera_id=0)

print("---系統啟動---")

RUN_SPEED = 40    
RUN_TIME = 0.05   
WAIT_TIME = 1.5   

def update_camera(duration):
    """在等待期間持續更新畫面，防止視窗當掉"""
    start_time = time.time()
    while (time.time() - start_time) < duration:
        _, _, frame = tracker.get_face_center()
        if frame is not None:
            cv2.putText(frame, "Status: Waiting", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Live Camera", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return False
    return True

try:
    while True:
        print("--- 執行循環動作 ---")
        
        # 動作 A：舵機位置 1 & 馬達旋轉
        tilt.set_position(1)
        motor.rotate_30_degrees(speed=RUN_SPEED, rotate_time=RUN_TIME)
        if not update_camera(WAIT_TIME): break

        # 動作 B：舵機位置 -1
        tilt.set_position(-1)
        if not update_camera(WAIT_TIME): break

except KeyboardInterrupt:
    print("\n偵測到停止指令")

finally:
    tracker.close()
    motor.close()
    tilt.close()
    cv2.destroyAllWindows()
    print("資源已釋放，系統安全退出。")