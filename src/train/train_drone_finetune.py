from ultralytics import YOLO

def main():
    BASE_MODEL = "assets/model/20260423_rtx5080_640dpi_16batch_140k_v3_50.pt"

    # =========================
    # 第一階段：適應攝像頭
    # =========================
    model = YOLO(BASE_MODEL)

    model.train(
        data="config/data.yaml",
        epochs=500,
        imgsz=640,
        batch=24,
        lr0=0.0005,
        freeze=10,
        device=0,
        name="stage1_adapt"
    )

    # =========================
    # 第二階段：全面微調
    # =========================

    # model2 = YOLO("runs/detect/stage1_adapt/weights/best.pt")

    # model2.train(
    #     data="src/dataset/dataset.yaml",
    #     epochs=40,
    #     imgsz=640,
    #     batch=16,
    #     lr0=0.0005,
    #     freeze=0,
    #     device=0,
    #     name="stage2_finetune"
    # )

# .....
if __name__ == "__main__":
    main()