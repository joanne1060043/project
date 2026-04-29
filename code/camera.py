# camera.py
import cv2

class FaceTracker:
    def __init__(self, camera_id=1):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            print("[錯誤] 無法開啟鏡頭")

    def get_face_center(self):
        """讀取畫面並回傳人臉中心點與畫面"""
        ret, frame = self.cap.read()
        if not ret:
            return None, None, None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))

        cx, cy = None, None
        for (x, y, w, h) in faces:
            cx = x + w // 2
            cy = y + h // 2
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            break # 只取第一個偵測到的目標

        return cx, cy, frame

    def close(self):
        """釋放資源"""
        if hasattr(self, 'cap'):
            self.cap.release()