# m.py
import lgpio
import time

MOTOR_PIN = 17
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, MOTOR_PIN)


SPEED = 30          # 功率百分比 (0-100)
ROTATE_TIME = 0.1   # 旋轉時間
INTERVAL = 2     # 間隔時間

# print("--- 系統啟動：間歇旋轉測試 (30度/2秒) ---")
print(f"減速比為 6:1，目標角度：30度")
print("提示：想停止請在終端機按 Ctrl + C")

try:
    while True:
        print("動作：旋轉 30 度")
        # 啟動馬達
        lgpio.tx_pwm(h, MOTOR_PIN, 1000, SPEED)
        time.sleep(ROTATE_TIME)
        
        # 停止供電
        lgpio.tx_pwm(h, MOTOR_PIN, 5000, 0)
        # print(f"狀態：停止並等待 {INTERVAL} 秒...")
        
        # 等待下一次循環
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\n偵測到停止指令，正在切斷馬達供電...")
    # 確保按下 Ctrl+C 後立刻斷電
    lgpio.tx_pwm(h, MOTOR_PIN, 1000, 0)

finally:
    # 徹底釋放硬體資源
    lgpio.gpiochip_close(h)
    print("硬體資源已安全釋放")