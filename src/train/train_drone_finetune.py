############################ 
# purpose: 將已經整理好的資料集進行訓練
# route: src/test/video.py
# 

from ultralytics import YOLO

def main():

    # 母模型
    BASE_MODEL = "assets/model/20260429_rtx5080_640dpi_24batch_140k_img+2k_rc_500epoch_v7.pt"

    # 第一階段：適應樣本


    model = YOLO(BASE_MODEL)

    model.train(
        data="config/data.yaml",
        epochs=100,
        imgsz=960,
        batch=16,
        lr0=0.001,
        freeze=10,
        device=0,
        name="stage1_adapt"
    )

    # 第二階段：全面微調

    # model2 = YOLO("runs/detect/stage1_adapt-3/weights/best.pt")

    # model2.train(
    #     data="config/data.yaml",
    #     epochs=100,
    #     imgsz=640,
    #     batch=24,
    #     lr0=0.001,
    #     freeze=0,
    #     device=0,
    #     name="stage2_finetune"
    # )

# .....
if __name__ == "__main__":
    main()