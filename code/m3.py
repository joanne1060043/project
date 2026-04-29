import lgpio
import time
import sys

MOTOR_PIN = 17
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, MOTOR_PIN)

# 核心參數
SPEED = 30    # 功率百分比 (0-100)

# --- 非線性實測數據對照表 (實際角度, 對應秒數) ---
# 數據來源：
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
    # (50, 0.333),  # 90
    # (73, 0.3515), # 95
    # (76, 0.37),   # 100
    # (0, 0.2035),  # 105
    # (7, 0.222),   # 110
    # (8, 0.2405),  # 115
    # (19, 0.259),  # 120
    # (26, 0.2775), # 125
    # (35, 0.296),  # 130
    # (44, 0.3145), # 135
    # (50, 0.333),  # 140
    # (73, 0.3515), # 145
    # (76, 0.37),   # 150
    # (76, 0.37),   # 155
    # (0, 0.2035),  # 160
    # (7, 0.222),   # 165
    # (8, 0.2405),  # 170
    # (19, 0.259),  # 175
    # (26, 0.2775), # 180
]

def calculate_nonlinear_time(target_angle):
    """線性插值計算：支援 0~360 度"""
    target_angle = abs(target_angle)
    
    # 處理 0~360 度：如果超過 130 度，使用最後一段 (9秒到10秒) 的斜率外推
    # 最後一段：(130-98) = 32度 / (10-9) = 1秒 -> 每度約 0.03125 秒
    if target_angle > DATA_MAP[-1][0]:
        angle_max, time_max = DATA_MAP[-1]
        angle_prev, time_prev = DATA_MAP[-2]
        
        # 計算最後一段的斜率 (秒/度)
        slope = (time_max - time_prev) / (angle_max - angle_prev)
        # 外推公式：基礎 10 秒 + (目標角度 - 130度) * 斜率
        return time_max + (target_angle - angle_max) * slope

    # 在數據點中尋找目標區間
    for i in range(len(DATA_MAP) - 1):
        angle_low, time_low = DATA_MAP[i]
        angle_high, time_high = DATA_MAP[i+1]
        
        if angle_low <= target_angle <= angle_high:
            ratio = (target_angle - angle_low) / (angle_high - angle_low)
            return time_low + ratio * (time_high - time_low)
    return 0

print("--- RS775 角度控制系統 (0~360度擴展版) ---")
print("已載入非線性補償曲線")

try:
    while True:
        val = input("\n請輸入欲旋轉角度 (0~360): ")
        try:
            target_deg = float(val)
        except ValueError:
            print("錯誤：請輸入數字！")
            continue

        if target_deg < 0 or target_deg > 360:
            print("請輸入 0 到 360 之間的角度")
            continue
            
        if target_deg == 0:
            continue

        # 計算查表或外推後的時間
        run_sec = calculate_nonlinear_time(target_deg)
        
        print(f"指令：旋轉 {target_deg} 度 -> 運轉時間：{run_sec:.4f} 秒")

        # 啟動馬達
        lgpio.tx_pwm(h, MOTOR_PIN, 1000, SPEED)
        
        # 執行時間
        time.sleep(run_sec)
        
        # 停止供電
        lgpio.tx_pwm(h, MOTOR_PIN, 1000, 0)
        print("動作完成。")

except KeyboardInterrupt:
    print("\n[Ctrl+C] 偵測到中斷，緊急斷電")
    lgpio.tx_pwm(h, MOTOR_PIN, 1000, 0)

finally:
    lgpio.tx_pwm(h, MOTOR_PIN, 1000, 0)
    lgpio.gpiochip_close(h)
    sys.exit(0)
