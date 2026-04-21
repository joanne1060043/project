from ultralytics import YOLO

def train_drone_model():
    # 1. 載入預訓練模型 (推薦用 v11n，因為它又快又強)
    model = YOLO('yolo11n.pt')  # 使用較小的預訓練模型來加速訓練

    # 2. 開始訓練
    results = model.train(
        data='data.yaml',        # 指定你的設定檔
        epochs=20,               # 訓練輪數 (可根據需求調整)
        imgsz=960,               # 影像大小
        device='0',              # 使用第一個 GPU
        project='drone_project', # 輸出的資料夾名稱
        name='v11_experiment',   # 實驗名稱
        batch=32,                # GPU 每次看張
        resume=True              # 如果已經中斷過，可以選擇恢復訓練
    )

if __name__ == '__main__':
    train_drone_model()