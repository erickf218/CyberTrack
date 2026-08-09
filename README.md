# CyberTrack

Sistema inteligente de gestión de inventarios para talleres, laboratorios y equipos de robótica, construido sobre visión por computadora e IA.

**Organización:** CyberLife
**Estado:** En desarrollo
**Versión actual:** v1.0-beta — Asistente

## Roadmap

| Versión | Nombre | Contenido |
|---|---|---|
| v0.1 | Foundation | Interfaz estática, sin backend ni IA ✅ |
| v0.2 | Inventory Core | Backend (FastAPI) + base de datos (SQLite) + frontend conectado ✅ |
| v0.4 | Vision | Detección de objetos con YOLO (modelo genérico) — reemplazado, ver abajo |
| v0.4.1 | Custom Vision | Identificación de piezas con Gemini (multimodal) ✅ |
| v0.5 | — | Actualización automática de inventario desde la cámara |
| v1.0-beta | Asistente | Asistente técnico con acceso al inventario real, basado en Groq ✅ |
| v1.0 | Deploy | Frontend y backend en un solo servicio, desplegable en internet (Render) ✅ (esta versión) |

## El asistente — por qué Groq y no Gemini

El asistente no necesita "ver" nada — recibe tu pregunta en texto y el
inventario actual, y responde en texto. Es puro razonamiento, sin
visión de por medio, que es justo donde **Groq** es la mejor opción:
su hardware (LPU, no GPU) está diseñado específicamente para
inferencia rápida, así que las respuestas se sienten casi instantáneas
en vez de tardar varios segundos como con la mayoría de APIs de IA.

Usa el modelo `openai/gpt-oss-120b` (el recomendado por Groq para
razonamiento general — los modelos Llama que se usaban antes en Groq
están en proceso de retiro).

Mismo patrón que con Gemini: `ai/assistant/assistant.py` es la ÚNICA
parte del proyecto que sabe que existe Groq. El backend solo conoce la
función `ask()`.

### Configurar tu API key de Groq

1. Ve a [console.groq.com/keys](https://console.groq.com/keys)
2. Inicia sesión (con Google, GitHub, o email) y crea una API key —
   gratis, sin tarjeta
3. Copia la key
4. En `backend/.env` (el mismo archivo donde ya pusiste tu key de
   Gemini), agrega una línea nueva:
   ```
   GROQ_API_KEY=tu-key-real-aqui
   ```
5. Reinicia el backend (`Ctrl+C` y vuelve a correr `uvicorn app.main:app --reload`)

**Tip de seguridad:** nunca pegues tu API key en un chat, screenshot,
o cualquier lugar que no sea directamente tu archivo `.env`. Si alguna
vez lo haces por accidente, revócala y genera una nueva — son gratis
e instantáneas.

## De YOLO a Gemini — por qué cambiamos

La v0.4 original usaba YOLO, que necesitaba que entrenáramos el modelo
con cientos de fotos propias de cada pieza para que reconociera algo
más específico que las 80 clases genéricas de COCO. Para esta beta,
decidimos usar **Gemini** (modelo multimodal de Google) en su lugar:
ya reconoce piezas de robótica sin entrenamiento porque las vio
durante su propio entrenamiento general.

**El trade-off, para que quede claro:**
- ✅ Cero fotos, cero entrenamiento, funciona desde el primer día
- ✅ Capa gratuita generosa (sin tarjeta)
- ⚠️ **No cuenta cuántas piezas hay** — identifica el tipo, la cantidad
  la escribes tú a mano al agregarla al inventario
- ⚠️ **No da la posición exacta** de la pieza en la foto (por eso ya no
  se dibujan cajas sobre la imagen, solo aparece la lista de resultados
  debajo)
- ⚠️ Necesita internet (YOLO corría 100% local)

Si más adelante quieren precisión de conteo real (por ejemplo, "detecta
automáticamente que hay 18 tornillos"), YOLO sigue siendo la
herramienta correcta para eso — dejamos `ai/dataset/README.md` y
`ai/training/train.py` intactos por si quieren retomar ese camino.
Como `ai/inference/detector.py` es la única parte del proyecto que
sabe qué proveedor de IA se está usando, cambiar de vuelta (o incluso
tener los dos y dejar que el usuario elija) no requiere tocar el
backend ni el frontend.

### Configurar tu API key de Gemini

1. Ve a [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   y genera una API key gratis (no pide tarjeta).
2. Dentro de `backend/`, copia `.env.example` a `.env`:
   ```bash
   cd backend
   cp .env.example .env
   ```
3. Abre `.env` y pega tu key:
   ```
   GEMINI_API_KEY=tu-api-key-real-aqui
   ```
4. Guarda. El backend la lee automáticamente al arrancar — no hay que
   tocar ningún archivo de Python. `.env` nunca se sube a git.

Sin esa key, todo el resto del proyecto (inventario, agregar/eliminar
piezas) sigue funcionando normal — solo `/api/detect` va a fallar, y
con un mensaje claro explicando qué falta, no un error confuso.

## Cómo correr el proyecto en tu Mac (desarrollo local)

**Ya no necesitas dos terminales.** El backend ahora sirve también el
frontend — un solo servidor para todo.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # y pega tu GEMINI_API_KEY y GROQ_API_KEY ahí (ver arriba)
uvicorn app.main:app --reload
```

Y abre **`http://127.0.0.1:8000`** en el navegador — ahí está todo: la
página, el inventario, la detección, el asistente. `cybertrack.db` se
crea solo la primera vez, con piezas de ejemplo. Documentación de la
API en `http://127.0.0.1:8000/docs`.

Ya no hace falta `python3 -m http.server`, ni preocuparte por
`file://` en Safari — todo se sirve desde el mismo origen.

## Cómo desplegarlo en internet (Render)

Esto pone tu proyecto en una URL pública real, sin necesitar tu Mac
prendida ni una terminal corriendo. Usamos [Render](https://render.com)
porque tiene una capa gratuita y funciona bien con FastAPI.

**Importante — qué SÍ y qué NO hace este despliegue:**
- ✅ El backend (FastAPI, Gemini, Groq) y el frontend quedan en una
  sola URL pública, accesible desde cualquier lado.
- ⚠️ En la capa gratuita de Render, el disco es "efímero" — cada vez
  que el servicio se reinicia o se vuelve a desplegar, `cybertrack.db`
  se borra y regresa a las piezas de ejemplo. Para un demo o portafolio
  esto normalmente no importa; si más adelante necesitas que el
  inventario persista de verdad entre reinicios, hay que cambiar a una
  base de datos administrada (Render ofrece Postgres gratis) — es un
  cambio aparte, avísame cuando llegues a necesitarlo.
- ⚠️ **GitHub por sí solo no sirve para esto.** GitHub Pages solo aloja
  archivos estáticos (HTML/CSS/JS) — nunca puede correr Python. Tu
  repositorio de GitHub es donde vive el código; Render es quien
  realmente lo *ejecuta*. Son dos cosas distintas y complementarias.

### Pasos

**1. Sube el proyecto a GitHub** (si no lo has hecho ya)
```bash
cd ~/Documents/CyberTrack
git init
git add .
git commit -m "CyberTrack v1.0-beta"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/CyberTrack.git
git push -u origin main
```
Tu `.gitignore` ya excluye `venv/`, `.env` y `cybertrack.db` — tus API
keys reales nunca se suben.

**2. Crea una cuenta en [render.com](https://render.com)** (gratis, puedes
entrar con tu cuenta de GitHub directamente)

**3. New → Web Service**, y conecta tu repositorio de GitHub

**4. Render debería detectar el archivo `render.yaml`** que ya está en
la raíz del proyecto y configurar todo solo (build command, start
command). Si no lo detecta automáticamente, configura a mano:
- **Build command:** `cd backend && pip install -r requirements.txt`
- **Start command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**5. Antes de darle "Create Web Service", agrega tus variables de entorno**
(sección "Environment"):
```
GEMINI_API_KEY=tu-api-key-real
GROQ_API_KEY=tu-api-key-real
```
(Igual que en tu `.env` local, pero configuradas aquí en vez de en un
archivo — Render nunca lee tu `.env`, que ni siquiera se subió a
GitHub.)

**6. Dale "Create Web Service"** y espera unos minutos — Render te va a
dar una URL pública tipo `https://cybertrack.onrender.com`. Esa es tu
página, ya con todo funcionando: inventario, detección con Gemini, y
el asistente con Groq.

**Nota sobre la capa gratuita:** Render "duerme" el servicio después de
un rato sin uso, y la primera visita después de eso tarda unos 30-50
segundos en despertar — es normal, no es que esté roto.

### Endpoints disponibles

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/inventory` | Lista todas las piezas |
| POST | `/api/inventory` | Crea una pieza nueva |
| PATCH | `/api/inventory/{id}` | Actualiza una pieza (ej. cantidad) |
| DELETE | `/api/inventory/{id}` | Elimina una pieza |
| POST | `/api/detect` | Sube una foto (JPG/PNG/WEBP) y devuelve las piezas identificadas por Gemini (sin cantidades, sin coordenadas) |
| POST | `/api/assistant/ask` | Pregunta al asistente (Groq) — lee el inventario real de la base de datos y responde qué piezas sirven, cuáles faltan |
| GET | `/api/health` | Verifica que la API está viva |

## Estructura del proyecto

```
CyberTrack/
├── frontend/     → interfaz (HTML/CSS/JS)
├── backend/      → API en Python + FastAPI (aún vacío, llega en v0.2)
├── ai/           → modelos de visión y datasets (llega en v0.4)
├── docs/         → documentación técnica y decisiones de diseño
└── tests/        → pruebas automatizadas
```

## Decisiones de arquitectura

- **FastAPI** en vez de Flask: más rápido, mejor documentación automática, se integra bien con IA.
- **SQLite** al inicio (gratis, un solo archivo, cero configuración), con posible migración a **PostgreSQL** más adelante si el proyecto crece a varios talleres a la vez.
- **HTML/CSS/JS puro** en el frontend antes que un framework, para entender bien el sistema antes de añadir complejidad.
- **Gemini** (multimodal) para identificar piezas — sin entrenamiento, capa gratuita. Cambiado desde YOLO; ver la sección "De YOLO a Gemini" arriba para el porqué y el trade-off.

## Principios del proyecto

1. Calidad antes que velocidad.
2. Todo tiene una razón de existir.
3. Modularidad — ningún archivo debe cargar con toda la lógica.
4. Escalabilidad — pensado para más de un taller.
5. Profesionalismo — que se vea como producto, no como tarea.
