from ultralytics import YOLO

# 1. 載入 YOLOv11 預訓練模型 (n 為 nano 版，適合快速訓練)
model = YOLO("yolo11n.pt") 

if __name__ == '__main__':
    # 2. 開始訓練
    results = model.train(
        data="data.yaml",   # 指定數據集配置文件
        epochs=100,         # 訓練 100 輪
        imgsz=640,          # 圖片縮放大小
        device=0,           # 如果你有 NVIDIA 顯卡請用 0，沒有則改用 'cpu'
        workers=0           # 在 Windows 上建議先設為 0 避免多線程報錯
    )