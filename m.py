import lgpio
import time

class DCMotorController:
    def __init__(self, pin=17):
        """初始化馬達硬體腳位"""
        self.pin = pin
        self.h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self.h, self.pin)
        print(f"DC 馬達 (GPIO {self.pin}) 初始化完成")

    def rotate_30_degrees(self, speed=30, rotate_time=0.1):
        """執行一次 30 度的旋轉動作"""
        lgpio.tx_pwm(self.h, self.pin, 1000, speed)
        time.sleep(rotate_time)
        lgpio.tx_pwm(self.h, self.pin, 1000, 0)

    def stop(self):
        """強制停止供電"""
        lgpio.tx_pwm(self.h, self.pin, 1000, 0)

    def close(self):
        """釋放硬體資源"""
        self.stop()
        lgpio.gpiochip_close(self.h)
        print("DC 馬達資源已安全釋放")