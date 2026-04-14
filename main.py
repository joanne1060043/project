import time
from m import DCMotorController  
from s import TiltServoController 

motor = DCMotorController(pin=17)
tilt = TiltServoController(pin=12)

print("系統啟動")
# print("目前架構：主程式讀取 m.py 與 s.py")
print("提示：按 Ctrl + C 停止")

try:
    while True:
        # 動作 1：低仰角 + 水平轉動 30 度
        print("\n[執行] 舵機：低仰角 / 馬達：旋轉 30 度")
        tilt.set_position(-1)  # 呼叫 s.py 中的方法
        motor.rotate_30_degrees(speed=30, rotate_time=0.1) # 呼叫 m.py 中的方法
        time.sleep(2)

        # 動作 2：中仰角 + 水平轉動 30 度
        print("[執行] 舵機：中仰角 / 馬達：旋轉 30 度")
        tilt.set_position(0)
        motor.rotate_30_degrees(speed=30, rotate_time=0.1)
        time.sleep(2)

        # 動作 3：高仰角 + 水平轉動 30 度
        print("[執行] 舵機：高仰角 / 馬達：旋轉 30 度")
        tilt.set_position(1)
        motor.rotate_30_degrees(speed=30, rotate_time=0.1)
        time.sleep(2)

except KeyboardInterrupt:
    print("\n偵測到停止指令 (Ctrl+C)")

finally:
    # 同時安全關閉兩個設備
    motor.close()
    tilt.close()
    print("所有設備已停止供電，程式安全結束")