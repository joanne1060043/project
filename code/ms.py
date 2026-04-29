import time
from m import DCMotorController
from s import TiltServoController

motor = DCMotorController(pin=17)
tilt = TiltServoController(pin=12)

try:
    print("純硬體測試開始...")
    while True:
        print("馬達與舵機動作中...")
        tilt.set_position(1)
        motor.rotate_30_degrees(speed=50, rotate_time=0.5)
        time.sleep(2)
        tilt.set_position(-1)
        time.sleep(2)
except KeyboardInterrupt:
    motor.close()
    tilt.close()