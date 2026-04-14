import time
from gpiozero import Servo
from gpiozero.pins.lgpio import LGPIOFactory

class TiltServoController:
    def __init__(self, pin=12):
        """初始化舵機硬體設定"""
        self.factory = LGPIOFactory()
        self.servo = Servo(pin, pin_factory=self.factory, 
                           min_pulse_width=0.5/1000, 
                           max_pulse_width=2.5/1000)
        print(f"舵機 (GPIO {pin}) 初始化完成")

    def set_position(self, pos):
        """
        設定舵機位置
        pos: -1 (最小), 0 (中間), 1 (最大)
        """
        self.servo.value = pos

    def stop(self):
        """清除訊號，防止舵機發燙抖動"""
        self.servo.value = None

    def close(self):
        """釋放資源"""
        self.stop()
        print("舵機資源已安全釋放")