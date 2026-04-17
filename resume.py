from ultralytics import YOLO

model = YOLO("yolo11n.pt")
model.train(resume=True)