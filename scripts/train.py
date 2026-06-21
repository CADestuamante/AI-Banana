from ultralytics import YOLO
from pathlib import Path

def main():
    DATA_YAML = str(Path("data/banana.yaml").resolve())
    model = YOLO("yolov8n.pt")
    model.train(
        data=DATA_YAML,
        epochs=100,
        imgsz=640,
        batch=8,
        device=0,
        project="models",
        name="banana_yolo",
        exist_ok=True,
    )
    print("Training done! Model saved to models/banana_yolo/weights/best.pt")

if __name__ == '__main__':
    main()