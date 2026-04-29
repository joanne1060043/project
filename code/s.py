# s.py
import time
from gpiozero import Servo
from gpiozero.pins.lgpio import LGPIOFactory

factory = LGPIOFactory()
SERVO_PIN = 12 
servo = Servo(SERVO_PIN, pin_factory=factory)

print("--- 程式啟動 ---")

try:
    while True:
        # 低仰角
        print("低仰角")
        servo.min()  # 值約為 -1
        time.sleep(2)

        # 中仰角
        print("中仰角")
        servo.mid()  # 值約為 0
        time.sleep(2)

        # 高仰角
        print("高仰角")
        servo.max()  # 值約為 1
        time.sleep(2)

except KeyboardInterrupt:
    # 當按 Ctrl+C 時，清除訊號，保護舵機不發燙
    servo.value = None
    print("\n程式停止")