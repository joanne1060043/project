# s.py
import time
from gpiozero import AngularServo
from gpiozero.pins.lgpio import LGPIOFactory

factory = LGPIOFactory()
SERVO_PIN = 12 

ZERO_OFFSET = 20  # 原點


print("--- 系統初始化中 ---")

# 1. 初始化馬達：initial_angle 會在建立物件時發出第一個訊號
servo = AngularServo(
    SERVO_PIN, 
    initial_angle=ZERO_OFFSET, 
    min_angle=0, 
    max_angle=180, 
    min_pulse_width=0.5/1000, 
    max_pulse_width=2.5/1000,
    pin_factory=factory
)

# 2. 強制歸位程序：確保馬達有足夠時間從任何位置轉回 65 度
print(f"正在執行歸位... 目標位置: {ZERO_OFFSET}度")
servo.angle = ZERO_OFFSET
time.sleep(1.5)  # 給予 1.5 秒時間讓馬達物理轉動到位
print("歸位完成，系統就緒。")

print(f"\n--- 偏移座標模式 (-90 到 90) ---")

try:
    while True:
        user_input = input(f"請輸入目標角度 (目前原點={ZERO_OFFSET})，或輸入 'q' 離開：")
        
        if user_input.lower() == 'q':
            break
            
        try:
            relative_angle = float(user_input)
            
            if -90 <= relative_angle <= 90:
                physical_angle = ZERO_OFFSET + relative_angle
                
                # 安全邊界檢查：確保不超過 0-180 範圍
                if 0 <= physical_angle <= 180:
                    print(f"移動至相對角度: {relative_angle} (物理角度: {physical_angle})")
                    servo.angle = physical_angle
                else:
                    print(f"⚠️ 警告：物理角度 {physical_angle} 超出馬達極限！")
            else:
                print("⚠️ 錯誤：請輸入 -90 到 90 之間的數字")
        except ValueError:
            print("⚠️ 錯誤：請輸入有效數字")

except KeyboardInterrupt:
    # 停止發送訊號以保護 MG996R 不發燙
    servo.angle = None 
    print("\n程式已手動停止")