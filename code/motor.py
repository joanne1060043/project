# motor.py
import lgpio

class DCMotorController:
    def __init__(self, pin=17):
        self.pin = pin
        self.frequency = 1000  # PWM 頻率 1kHz
        
        try:
            self.h = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self.h, self.pin)
            print(f"[系統訊息] 馬達已就緒 (GPIO {self.pin})")
        except Exception as e:
            print(f"[錯誤] 無法初始化馬達硬體: {e}")

    def run(self, speed=30):
        """
        持續輸出 PWM 訊號讓馬達轉動 (非阻塞)
        :param speed: 功率百分比 (0-100)
        """
        try:
            lgpio.tx_pwm(self.h, self.pin, self.frequency, speed)
        except Exception as e:
            print(f"[警告] 馬達運轉失敗: {e}")

    def stop(self):
        """
        停止供電 (將 PWM 佔空比設為 0)
        """
        try:
            lgpio.tx_pwm(self.h, self.pin, self.frequency, 0)
        except:
            pass

    def rotate_30_degrees(self, speed=50, rotate_time=0.1):
        """
        單次觸發型旋轉 (保留原本主程式可能呼叫的舊方法)
        注意：此方法會產生微小阻塞
        """
        self.run(speed)
        import time
        time.sleep(rotate_time)
        self.stop()

    def close(self):
        """
        徹底釋放 GPIO 資源 (程式結束前必須呼叫)
        """
        self.stop()
        try:
            lgpio.gpiochip_close(self.h)
            print("[系統訊息] 馬達資源已安全釋放")
        except:
            pass