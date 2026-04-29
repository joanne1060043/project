import lgpio
import time
import sys

# --- 腳位設定 ---
IN1_PIN = 17
IN2_PIN = 27

# 開啟 GPIO 晶片
h = lgpio.gpiochip_open(0)

# 設定輸出引腳
lgpio.gpio_claim_output(h, IN1_PIN)
lgpio.gpio_claim_output(h, IN2_PIN)

# --- 核心參數 ---
# 你可以在這裡調整轉速百分比 (0 到 100)
# 注意：轉速改變後，原本的角度補償時間(DATA_MAP)需要重新校正
SPEED = 30  

# --- 非線性實測數據對照表 (範例數據) ---
DATA_MAP = [
    (0, 0),         # 0度
    (1, 0.037),     # 5
    (8, 0.037),     # 10
    (9.5, 0.0555),   # 15
    (15.5, 0.074),    # 20
    (21.5, 0.0925),   # 25
    (25, 0.111),    # 30
    (38, 0.1295), # 35
    (43, 0.148),    # 40
    (48, 0.1665),   # 45
    (60, 0.185),    # 50
    (70, 0.2035),  # 55
    (55, 0.222),   # 60
    (86, 0.2405),  # 65
    (95, 0.259),  # 70
    (97, 0.2775), # 75
    (110, 0.296),  # 80
    (118, 0.3145), # 85
]

def calculate_time(target_angle):
    """根據目標角度換算運轉秒數"""
    angle = abs(target_angle)
    if angle > DATA_MAP[-1][0]:
        a_max, t_max = DATA_MAP[-1]
        a_prev, t_prev = DATA_MAP[-2]
        slope = (t_max - t_prev) / (a_max - a_prev)
        return t_max + (angle - a_max) * slope
    
    for i in range(len(DATA_MAP) - 1):
        a_low, t_low = DATA_MAP[i]
        a_high, t_high = DATA_MAP[i+1]
        if a_low <= angle <= a_high:
            ratio = (angle - a_low) / (a_high - a_low)
            return t_low + ratio * (t_high - t_low)
    return 0

def motor_move(angle, target_speed):
    """執行馬達轉動，支援正反轉與調速"""
    run_sec = calculate_time(angle)
    
    if angle > 0:
        print(f"指令：正轉 {angle} 度，轉速：{target_speed}%，時間：{run_sec:.4f} 秒")
        # IN1 輸出 PWM，IN2 保持 0
        lgpio.tx_pwm(h, IN1_PIN, 1000, target_speed)
        lgpio.gpio_write(h, IN2_PIN, 0)
    elif angle < 0:
        print(f"指令：反轉 {abs(angle)} 度，轉速：{target_speed}%，時間：{run_sec:.4f} 秒")
        # IN1 保持 0，IN2 輸出 PWM
        lgpio.gpio_write(h, IN1_PIN, 0)
        lgpio.tx_pwm(h, IN2_PIN, 1000, target_speed)
    else:
        return

    time.sleep(run_sec)
    
    # 停止供電 (PWM 設為 0)
    lgpio.tx_pwm(h, IN1_PIN, 1000, 0)
    lgpio.tx_pwm(h, IN2_PIN, 1000, 0)
    print("停止。")

try:
    print(f"--- RS775 調速控制系統 (目前轉速: {SPEED}%) ---")
    
    while True:
        val = input("\n輸入角度")
        
        if val.lower() == 's':
            new_speed = input("請輸入新轉速 (0-100): ")
            SPEED = float(new_speed)
            print(f"轉速已更新為: {SPEED}%")
            continue

        try:
            target = float(val)
            motor_move(target, SPEED)
        except ValueError:
            print("請輸入有效數字。")

except KeyboardInterrupt:
    print("\n[Ctrl+C] 停止中...")

finally:
    # 安全斷電
    lgpio.tx_pwm(h, IN1_PIN, 1000, 0)
    lgpio.tx_pwm(h, IN2_PIN, 1000, 0)
    lgpio.gpiochip_close(h)
    sys.exit(0)