# Cómo armar el dataset de piezas de CyberTrack

> ⚠️ **Nota:** desde v0.4.1, CyberTrack usa Gemini (multimodal) para
> identificar piezas, no YOLO — no requiere el entrenamiento descrito
> aquí. Esta guía queda lista por si en el futuro quieren un modelo
> local que sí cuente piezas con precisión (YOLO es mejor que Gemini
> para eso). Ver la sección "De YOLO a Gemini" en el README principal.

Esta carpeta va a contener las fotos que usaremos para entrenar el
modelo YOLO a reconocer piezas reales de robótica (Spark MAX, llaves
Allen, motores, etc.) en vez de las 80 clases genéricas de COCO.

## 1. Qué piezas fotografiar primero

No intentes cubrir todo el taller de una vez. Arranca con **5-8 piezas**
que se usen mucho y sean fáciles de distinguir a simple vista. Por
ejemplo:

- Spark MAX
- Motor NEO Vortex
- Llave Allen (una medida específica, ej. 2.5mm)
- Batería REV
- Tornillo M4

Cuantas más piezas distintas metas desde el inicio, más tiempo toma
etiquetar y entrenar. Es mejor tener 5 piezas bien reconocidas que 20
piezas mal entrenadas.

## 2. Cuántas fotos por pieza

**Mínimo 80-100 fotos por pieza** para un resultado decente. Ley pareja:
entre más variedad, mejor generaliza el modelo. No sirve tomar 100 fotos
casi idénticas — sirve más tomar menos fotos pero bien variadas.

No son miles porque no entrenamos desde cero: `ai/training/train.py`
parte de `yolov8n.pt` ya preentrenado (transfer learning), así que el
modelo solo tiene que aprender a reconocer piezas nuevas encima de todo
lo que ya sabe sobre "qué es un objeto". Además, al exportar desde
Roboflow puedes activar **augmentación de datos**: toma tus fotos
originales y genera automáticamente variaciones (rotadas, con más/menos
brillo, espejeadas) sin que tomes una sola foto extra — con eso, 100
fotos reales por pieza terminan siendo varios cientos de ejemplos de
entrenamiento.

Varía estas cosas entre foto y foto:

| Variable | Ejemplos |
|---|---|
| Ángulo | de frente, de lado, en diagonal, desde arriba |
| Distancia | de cerca, a media distancia |
| Fondo | mesa de trabajo, piso, dentro de una caja, sobre otras piezas |
| Iluminación | luz de techo, luz de ventana, con sombra, sin sombra |
| Posición de la pieza | acostada, parada, agrupada con otras piezas, sola |
| Cámara | si puedes, usa varios celulares/cámaras distintos |

## 3. Cómo tomar las fotos

- Resolución normal de celular está bien (no hace falta cámara profesional).
- Evita que la pieza ocupe el 100% del cuadro — deja algo de fondo alrededor,
  YOLO aprende mejor con contexto.
- Si vas a detectar varias piezas en una misma foto (como el caso de uso real:
  "varias piezas sobre la mesa"), incluye también fotos con **varias piezas
  juntas**, no solo una por foto.
- Formato JPG o PNG, no importa mucho cuál.

## 4. Cómo organizar los archivos aquí

```
ai/dataset/
├── raw/                    ← fotos originales, sin editar, tal como salen de la cámara
│   ├── spark_max/
│   │   ├── IMG_0001.jpg
│   │   ├── IMG_0002.jpg
│   │   └── ...
│   ├── neo_vortex/
│   ├── llave_allen_2_5mm/
│   ├── bateria_rev/
│   └── tornillo_m4/
│
└── labeled/                 ← lo que exportes de Roboflow ya etiquetado (ver abajo)
    ├── images/
    ├── labels/
    └── data.yaml
```

La carpeta `raw/` es solo para que tú organices las fotos por pieza
antes de subirlas a etiquetar. `labeled/` es donde va a caer el
resultado ya exportado en formato YOLO — no la llenes a mano.

## 5. Etiquetado — usa Roboflow (recomendado)

[Roboflow](https://roboflow.com) es gratis para proyectos pequeños y
es la forma más rápida de etiquetar sin instalar nada:

1. Crea una cuenta gratis y un proyecto nuevo tipo "Object Detection".
2. Sube todas las fotos de `raw/` (puedes arrastrar carpetas completas).
3. Para cada foto, dibuja un rectángulo alrededor de la pieza y ponle
   el nombre de la clase (ej. `spark_max`). Roboflow tiene un modo
   rápido con teclado que acelera mucho esto.
4. Cuando termines de etiquetar todas las fotos, genera una versión del
   dataset con **Train/Valid/Test split** (Roboflow lo hace automático,
   deja los valores por default: 70/20/10 está bien).
5. Exporta en formato **"YOLOv8"** — te da un ZIP con la estructura
   `images/`, `labels/` y un archivo `data.yaml`.
6. Descomprime ese ZIP dentro de `ai/dataset/labeled/`.

Alternativa sin internet: **LabelImg** (`pip install labelImg`) hace lo
mismo pero localmente. Es más manual, Roboflow es más rápido para
empezar.

## 6. Cuando termines

Con `ai/dataset/labeled/` ya lleno, el siguiente paso es correr
`ai/training/train.py` (ver ese archivo) para entrenar el modelo.
