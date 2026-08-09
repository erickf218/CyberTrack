"""
Entrena un modelo YOLO con las piezas reales del taller.

CUÁNDO USAR ESTE SCRIPT:
Solo después de que ai/dataset/labeled/ ya tenga las fotos etiquetadas
y exportadas desde Roboflow (o LabelImg), con esta estructura:

    ai/dataset/labeled/
    ├── data.yaml
    ├── images/
    │   ├── train/
    │   ├── valid/
    │   └── test/
    └── labels/
        ├── train/
        ├── valid/
        └── test/

Si esa carpeta no existe todavía, no corras esto — primero completa
los pasos de ai/dataset/README.md.

CÓMO CORRERLO:
    cd ai/training
    python train.py

Esto parte del modelo yolov8n preentrenado (no desde cero — así
aprovecha todo lo que YOLO ya sabe sobre "qué es un objeto" y solo
aprende a reconocer las piezas nuevas, lo que necesita muchos menos
datos y tiempo que entrenar de cero).

QUÉ HACE AL TERMINAR:
Guarda el modelo entrenado en runs/detect/train/weights/best.pt.
Para usarlo en CyberTrack, cópialo a ai/models/ (ej. como
"cybertrack_v1.pt") y actualiza MODEL_PATH en
ai/inference/detector.py para que apunte ahí. Ese es el único cambio
que necesita el resto del proyecto.
"""
from pathlib import Path
from ultralytics import YOLO

DATASET_DIR = Path(__file__).resolve().parents[1] / "dataset" / "labeled"
DATA_YAML = DATASET_DIR / "data.yaml"

# Hiperparámetros de entrenamiento. Estos valores son un punto de
# partida razonable para un dataset chico (unas cientos de fotos);
# no hace falta tocarlos para el primer intento.
EPOCHS = 100          # cuántas veces el modelo ve el dataset completo
IMAGE_SIZE = 640       # tamaño al que se redimensionan las fotos para entrenar
BATCH_SIZE = 16        # cuántas fotos procesa a la vez (bájalo si tu compu es lenta)
BASE_MODEL = "yolov8n.pt"  # partimos del mismo modelo nano que ya usa el proyecto


def main():
    if not DATA_YAML.exists():
        raise FileNotFoundError(
            f"No encontré {DATA_YAML}.\n"
            "Antes de entrenar, exporta tu dataset etiquetado desde Roboflow "
            "(formato YOLOv8) y descomprímelo en ai/dataset/labeled/.\n"
            "Ver ai/dataset/README.md para la guía completa."
        )

    model = YOLO(BASE_MODEL)

    model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH_SIZE,
        name="cybertrack_parts",
    )

    print("\n✅ Entrenamiento terminado.")
    print("Modelo guardado en: runs/detect/cybertrack_parts/weights/best.pt")
    print("\nSiguiente paso:")
    print("  1. Copia ese archivo a ai/models/ (ej. cybertrack_v1.pt)")
    print("  2. Actualiza MODEL_PATH en ai/inference/detector.py para que apunte ahí")


if __name__ == "__main__":
    main()
