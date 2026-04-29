# c.py
import cv2

# 1. 載入人臉追蹤模型 (OpenCV 內建)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# 2. 開啟鏡頭
# 如果你有內建鏡頭 + 外接鏡頭，通常內建是 0，外接是 1 (或是 2)
# 如果只有外接鏡頭，請試試看 0 或 1
cap = cv2.VideoCapture(1) 

print("正在啟動鏡頭... 按下 'q' 鍵可結束程式")

while True:
    # 讀取每一幀畫面
    ret, frame = cap.read()
    if not ret:
        print("無法取得畫面，請檢查鏡頭連接")
        break

    # 轉為灰階 (辨識模型在灰階下跑得比較快且準)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 偵測人臉
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # 在偵測到的人臉周圍畫框
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(frame, 'Face', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    # 顯示結果視窗
    cv2.imshow('Face Detection - Press Q to Quit', frame)

    # 按下 'q' 鍵離開迴圈
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 釋放資源
cap.release()
cv2.destroyAllWindows()