from ultralytics import YOLO
import torch


def train_drone_model():
    model = YOLO("yolo12m.pt")

    results = model.train(
        data='data.yaml',
        epochs=50,
        imgsz=640,
        device=0,
        batch=16,
        amp=True,
        cos_lr=True,
        close_mosaic=10,
        patience=20,
        project='drone_project',
        name='v12_experiment',
    )
    return results


if __name__ == "__main__":
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
    train_drone_model()