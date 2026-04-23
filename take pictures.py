import cv2
import numpy as np
import os
import json

# 檢查並讀取 JSON 檔案
json_file = './clip/id.json'
if os.path.exists(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)
else:
    data = {"id": 0}  # 如果沒有檔案，則從 ID = 0 開始

# 創建資料夾以儲存截圖
if not os.path.exists('./clip'):
    os.makedirs('./clip')

# 開啟攝影機
cap = cv2.VideoCapture(2, cv2.CAP_DSHOW)

# 設定攝影機解析度
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# 記錄截圖編號
screenshot_counter = data["id"]

while True:
    # 讀取影像幀
    ret, frame = cap.read()

    # ===== 3️⃣ 軟體防過曝（壓亮度）=====
    frame = cv2.convertScaleAbs(frame, alpha=0.8, beta=-50)
    
    # 如果攝影機開啟成功
    if not ret:
        break
    
    # 等待鍵盤事件
    key = cv2.waitKey(1) & 0xFF

    # 當按下 'C' 鍵時，截取並保存影像
    if key == ord('c'):
        screenshot_name = f"./clip/screenshot_{screenshot_counter}.png"
        cv2.imwrite(screenshot_name, frame)
        print(f"Screenshot saved as {screenshot_name}")
        screenshot_counter += 1  # 增加截圖編號
        
        # 更新 JSON 檔案中的 ID
        data["id"] = screenshot_counter
        with open(json_file, 'w') as f:
            json.dump(data, f)

    # 按 'q' 鍵退出
    elif key == ord('q'):
        break

    # 在影像上顯示截圖數量
    text = f"Screenshot count: {screenshot_counter}"
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # 顯示當前影像
    cv2.imshow('Press C to Capture', frame)

# 釋放攝影機並關閉視窗
cap.release()
cv2.destroyAllWindows()