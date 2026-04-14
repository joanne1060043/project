from ultralytics import YOLO

def train_drone_model():
    # 1. 載入預訓練模型 (推薦用 v11n，因為它又快又強)
    model = YOLO('yolo11n.pt') 

    # 2. 開始訓練
    results = model.train(
        data='yolo/img/data.yaml',      # 指定你的設定檔
        epochs=100,            # 訓練輪數 (視情況調整，通常 50-100 夠用)
        imgsz=640,             # 影像大小
        device='cpu',              # 如果用電腦練有顯卡設 0，若沒顯卡設 'cpu'
        project='drone_project', # 輸出的資料夾名稱
        name='v11_experiment'    # 實驗名稱
    )

if __name__ == '__main__':
    train_drone_model()