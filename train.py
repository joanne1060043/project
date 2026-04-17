from ultralytics import YOLO

def main():
    model = YOLO("yolo11n.pt")

    model.train(
        data="Drone-detectionn.v1i.yolov8/data.yaml",  # 修正這裡
        epochs=50,
        imgsz=640,
        resume=True
    )

if __name__ == "__main__":
    main()