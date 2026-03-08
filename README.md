# VisionCraft AI — Prompt-Guided Image & Video Editor

A full-stack Django application that lets users edit images and videos using **natural language prompts** powered by **OpenCV** computer vision models.

---

## Features

| Feature | Details |
|---|---|
| 🤖 **Prompt-Based Editing** | Type natural language: *"remove the background"*, *"detect all objects"*, *"make it vintage"* |
| 🔍 **Object Detection** | Edge + blob analysis with bounding boxes & labels |
| ✂️ **Background Removal** | GrabCut segmentation algorithm |
| 🎨 **14 AI Operations** | Enhance, Sharpen, Denoise, Cartoon, Sepia, Emboss, Edge Detect, and more |
| 🎬 **Video Support** | Frame-by-frame processing for all operations |
| 📊 **REST API** | Full JSON API for all operations |
| 🗄️ **PostgreSQL** | Full database with operation history |
| 📁 **Gallery** | Upload history, before/after comparison |

---

## Quick Start

### 1. Clone & Setup

```bash
git clone <repo>
cd visioncraft

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

For **quick start with SQLite** (no PostgreSQL needed):
```
USE_SQLITE=True
```

For **PostgreSQL**:
```bash
createdb visioncraft_db
# Fill in DB_* variables in .env
```

### 3. Initialize Database

```bash
python manage.py makemigrations editor
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run the Server

```bash
python manage.py runserver
```

Visit **http://localhost:8000**

---

## Project Structure

```
visioncraft/
├── manage.py
├── requirements.txt
├── .env.example
│
├── visioncraft/           # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── editor/                # Main app
│   ├── models.py          # MediaFile, EditOperation, DetectedObject
│   ├── views.py           # Upload, Editor, Gallery, Dashboard
│   ├── urls.py
│   └── ai_engine.py       # ⭐ Core AI processing (OpenCV)
│
├── api/                   # REST API app
│   ├── views.py           # JSON endpoints
│   └── urls.py
│
├── templates/
│   ├── base.html
│   ├── auth/login.html
│   ├── auth/register.html
│   └── editor/
│       ├── landing.html
│       ├── dashboard.html
│       ├── upload.html
│       ├── editor.html    # ⭐ Main editing interface
│       ├── gallery.html
│       └── history.html
│
└── media/                 # Uploaded & processed files
```

---

## REST API

All endpoints require authentication (session cookie).

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/stats/` | User statistics |
| GET | `/api/files/` | List all media files |
| GET | `/api/files/<id>/` | Get file details |
| DELETE | `/api/files/<id>/` | Delete file |
| GET | `/api/operations/` | List all operations |
| GET | `/api/operations/<id>/` | Get operation details |
| POST | `/api/parse-prompt/` | Parse a natural language prompt |
| GET | `/api/operations/meta/` | List available operations |

### Example: Parse Prompt

```bash
curl -X POST http://localhost:8000/api/parse-prompt/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "remove the background and make it sharp"}'
```

Response:
```json
{
  "prompt": "remove the background and make it sharp",
  "detected_operation": "remove_background",
  "parameters": {},
  "description": "Background Removal"
}
```

---

## AI Operations

| Key | Description | Algorithm |
|---|---|---|
| `detect_objects` | Object detection with bounding boxes | Edge detection + contour analysis |
| `remove_background` | Remove image background | GrabCut segmentation |
| `blur_background` | Blur background, keep subject | GrabCut + Gaussian blur |
| `enhance` | Auto-enhance image quality | CLAHE + adaptive sharpening |
| `sharpen` | Sharpen image details | Convolutional kernel |
| `denoise` | Remove noise | Non-local means denoising |
| `brightness` | Increase brightness | Additive pixel transform |
| `contrast` | Increase contrast | Multiplicative pixel transform |
| `edge_detect` | Canny edge detection | Canny algorithm |
| `cartoon` | Cartoon effect | Bilateral filter + adaptive threshold |
| `emboss` | 3D emboss effect | Emboss kernel |
| `sepia` | Vintage sepia tone | Color matrix transform |
| `grayscale` | Convert to grayscale | BGR → GRAY → BGR |

---

## Prompt Reference — All Working Prompts

Type any of these into the prompt bar in the editor. Prompts are **case-insensitive** and partial matches work too.

---

### 🔍 Object Detection
```
detect objects
detect all objects
find objects
identify objects
detect
label all objects
mark objects
annotate objects
find and label every object
detect all persons and cars
```

---

### ✂️ Background Removal
```
remove the background
remove background
cut out the background
strip the background
erase the background
no background
transparent background
cutout
```

---

### 🎨 Background Color Change
```
change background to red
make background blue
set background to black
change bg to white
turn background green
fill background with yellow
change background to orange
make background purple
set bg to pink
change background to gray
change background to cyan
background to navy
background to gold
background to blur
```
> You can also click the **color swatches** directly in the left panel without typing.

---

### 💫 Background Blur (Bokeh)
```
blur the background
blur background
soften the background
bokeh background
make background blurry
background out of focus
```

---

### ✨ Image Enhancement
```
enhance the image
improve quality
restore image
fix the photo
upscale quality
make it better
enhance and restore
```

---

### 🔪 Sharpening
```
sharpen the image
sharpen
make it crisp
add clarity
unblur this photo
```

---

### 🌀 Denoise
```
denoise the image
remove noise
clean the image
smooth out grain
denoise
```

---

### ☀️ Brightness
```
increase brightness
lighten the image
make it brighter
make it darker
dim the image
```

---

### 🔲 Contrast
```
increase contrast
make it more vivid
add contrast
make colors pop
```

---

### ⬛ Grayscale
```
convert to grayscale
make it black and white
grayscale
monochrome
desaturate
```

---

### 🎭 Artistic Effects

**Sepia / Vintage**
```
apply sepia tone
make it vintage
old photo effect
retro style
aged look
warm tone
```

**Cartoon**
```
apply cartoon effect
cartoon
make it look like anime
comic style
illustrated
```

**Edge Detection**
```
detect edges
show outlines
edge detection
sketch
drawing
wireframe
```

**Emboss**
```
apply emboss effect
emboss
3d effect
relief effect
raised effect
```

---

### 💡 Prompt Tips

| Tip | Example |
|---|---|
| Keep it simple | `"blur background"` works as well as `"can you please blur my background"` |
| Color names work | `red, blue, green, white, black, yellow, orange, purple, pink, cyan, gray, gold, navy, teal, maroon, beige, silver, lime, violet` |
| No quotes needed | Just type directly into the prompt bar |
| One operation per prompt | The parser picks the **first matching** operation |
| Use buttons for reliability | Left panel buttons always trigger the exact operation |

---

## Tech Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: PostgreSQL (psycopg2) / SQLite fallback
- **AI/CV**: OpenCV (opencv-python-headless), NumPy, Pillow
- **Frontend**: Bootstrap 5.3, Bootstrap Icons, Vanilla JS
- **Fonts**: Space Grotesk, JetBrains Mono