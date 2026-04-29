import cv2

# 印出 OpenCV 版本
print(f"OpenCV 版本: {cv2.__version__}")

# 測試開啟攝影機 (如果電腦有攝影機)
cap = cv2.VideoCapture(1)
if cap.isOpened():
    print("攝影機連線成功！")
    cap.release()
else:
    print("無法開啟攝影機。")