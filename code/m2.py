import lgpio
import time
import sys

# 硬體設定
MOTOR_PIN = 17
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, MOTOR_PIN)

# 核心參數
SPEED = 30           # 功率百分比 (0-100)
SEC_PER_DEGREE = 0.0037 

print("--- RS775 角度控制系統 (極速版) ---")
print(f"當前參數：1度 = {SEC_PER_DEGREE} 秒")
print("提示：輸入角度（如 90）進行轉動，按 Ctrl + C 安全退出")

try:
    while True:
        val = input("\n請輸入欲旋轉角度 (0~360): ")
        try:
            target_deg = float(val)
        except ValueError:
            print("錯誤：請輸入數字！")
            continue

        if target_deg == 0:
            continue

        # 計算運轉時間 (目標角度 * 0.002)
        run_sec = abs(target_deg) * SEC_PER_DEGREE
        
        print(f"指令：旋轉 {target_deg} 度 -> 運轉時間：{run_sec:.4f} 秒")

        # 啟動馬達
        lgpio.tx_pwm(h, MOTOR_PIN, 1000, SPEED)
        
        # 執行計算出的微小時間
        time.sleep(run_sec)
        
        # 立即停止供電
        lgpio.tx_pwm(h, MOTOR_PIN, 1000, 0)
        print("到達預定位置。")

except KeyboardInterrupt:
    print("\n[Ctrl+C] 偵測到中斷，正在切斷馬達電源...")
    lgpio.tx_pwm(h, MOTOR_PIN, 1000, 0)

finally:
    # 確保釋放硬體資源
    lgpio.tx_pwm(h, MOTOR_PIN, 1000, 0)
    lgpio.gpiochip_close(h)
    print("硬體資源已安全釋放，程式結束。")
    sys.exit(0)