# servo.py
import time
from gpiozero import Servo
from gpiozero.pins.lgpio import LGPIOFactory

class TiltServoController:
    def __init__(self, pin=12):
        try:
            self.factory = LGPIOFactory()
            # 設定 MG996R 脈衝寬度 (0.5ms ~ 2.5ms) 以獲得最大 180 度轉角
            self.servo = Servo(
                pin, 
                pin_factory=self.factory,
                min_pulse_width=0.5/1000, 
                max_pulse_width=2.5/1000
            )
            print(f"[系統訊息] 舵機 (GPIO {pin}) 初始化成功")
        except Exception as e:
            print(f"[錯誤] 舵機初始化失敗: {e}")

    def set_position(self, pos):
        """
        設定舵機位置
        pos 範圍: -1.0 (最小), 0.0 (中間), 1.0 (最大)
        """
        try:
            # 限制輸入值範圍，避免程式報錯
            pos = max(-1.0, min(1.0, pos))
            self.servo.value = pos
        except Exception as e:
            print(f"[錯誤] 舵機動作執行失敗: {e}")

    def stop(self):
        """
        停止舵機受力 (按下 S 鍵或程式停止時呼叫)
        將值設為 None 會停止發送 PWM 訊號，保護舵機不發燙
        """
        if hasattr(self, 'servo'):
            self.servo.value = None
            print("[系統訊息] 舵機已停止供電 (放鬆狀態)")

    def close(self):
        """
        釋放硬體資源
        """
        self.stop()
        print("[系統訊息] 舵機硬體資源已釋放")