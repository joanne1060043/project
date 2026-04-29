# s3.py
import time
from gpiozero import AngularServo
from gpiozero.pins.lgpio import LGPIOFactory

class TiltServoController:
    def __init__(self, pin=12, zero_offset=20):
        """
        初始化舵機
        zero_offset: 你的原點角度 (20度)
        """
        self.factory = LGPIOFactory()
        self.zero_offset = zero_offset
        
        # 初始化馬達
        self.servo = AngularServo(
            pin, 
            initial_angle=self.zero_offset, 
            min_angle=0, 
            max_angle=180, 
            min_pulse_width=0.5/1000, 
            max_pulse_width=2.5/1000,
            pin_factory=self.factory
        )
        print(f"[系統訊息] 舵機初始化完成，原點設定為 {self.zero_offset} 度")

    def set_relative_angle(self, relative_angle):
        """
        輸入相對角度 (-90 到 90)，轉換為物理角度並移動
        """
        try:
            # 物理角度 = 原點 + 相對偏移
            physical_angle = self.zero_offset + relative_angle
            
            # 安全邊界檢查：確保不超過 0-180 範圍
            if 0 <= physical_angle <= 180:
                self.servo.angle = physical_angle
                # print(f"移動至物理角度: {physical_angle}") # 偵錯用
            else:
                print(f"⚠️ 警告：物理角度 {physical_angle} 超出馬達極限！")
        except Exception as e:
            print(f"⚠️ 舵機移動失敗: {e}")

    def stop(self):
        """停止發送訊號，防止 MG996R 發燙"""
        if hasattr(self, 'servo'):
            self.servo.angle = None
            print("[系統訊息] 舵機已放鬆 (無訊號狀態)")

    def close(self):
        """釋放硬體資源"""
        self.stop()