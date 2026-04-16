from ultralytics import YOLO

def main():
    model = YOLO("yolo11n.pt")

    model.train(
        data="Drone-detection.v1i.yolov8/data.yaml",  # 修正這裡
        epochs=50,
        imgsz=640,
        batch=16,
        device=0,
        workers=0
    )

if __name__ == "__main__":
    main()