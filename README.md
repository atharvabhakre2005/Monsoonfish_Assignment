# Logo Processing & Email Delivery Service

A backend service that accepts a logo/image upload, runs **3 computer-vision transformations** (silhouette, edge/border, grayscale) using OpenCV, and **automatically emails** the results — all triggered by a single API call.

---

## Architecture

```
┌──────────────┐       POST /process        ┌────────────────────────┐
│   Frontend   │  ───────────────────────▶  │   FastAPI Backend      │
│  (HTML + JS) │                            │                        │
└──────────────┘                            │  ┌──────────────────┐  │
                                            │  │  Validators      │  │
                                            │  │  (type/size)     │  │
                                            │  └────────┬─────────┘  │
                                            │           ▼            │
                                            │  ┌──────────────────┐  │
                                            │  │ Image Processor  │  │
                                            │  │ (OpenCV/NumPy)   │  │
                                            │  └────────┬─────────┘  │
                                            │           ▼            │
                                            │  ┌──────────────────┐  │
                                            │  │  Email Service   │  │
                                            │  │  (SMTP/TLS)      │  │
                                            │  └──────────────────┘  │
                                            └────────────────────────┘
```

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Env-based configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── image_processor.py  # CV transformations (OpenCV + Pillow)
│   │   └── email_service.py    # SMTP email delivery
│   └── utils/
│       ├── __init__.py
│       └── validators.py       # Upload validation
├── static/
│   └── index.html              # Minimal frontend
├── outputs/                    # Generated images (gitignored)
├── uploads/                    # Temp uploads (gitignored)
├── .env.example                # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Clone & install

```bash
git clone <repo-url>
cd Monsoonfish

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS / Linux
```

Edit `.env` with your email credentials:

```env
RECIPIENT_EMAIL=recipient@example.com
SENDER_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

> **Gmail users**: You need an [App Password](https://support.google.com/accounts/answer/185833), not your regular password. Enable 2-Step Verification first, then generate an App Password under Security → App Passwords.

### 3. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open in browser

Navigate to **http://localhost:8000** — upload an image and hit "Upload & Process".

---

## API Reference

### `POST /process`

Upload an image for processing and automatic email delivery.

**Request**: `multipart/form-data` with a `file` field.

**Constraints**:
- Accepted formats: `.png`, `.jpg`, `.jpeg`
- Max file size: 5 MB

**Success Response** (`200 OK`):

```json
{
  "request_id": "a1b2c3d4e5f6",
  "silhouette": "generated",
  "border": "generated",
  "grayscale": "generated",
  "email_status": "sent",
  "downloads": {
    "silhouette": "/outputs/a1b2c3d4e5f6/silhouette.png",
    "border": "/outputs/a1b2c3d4e5f6/border.png",
    "grayscale": "/outputs/a1b2c3d4e5f6/grayscale.png"
  }
}
```

**Error Responses**:

| Status | Condition |
|--------|-----------|
| `400`  | Missing / empty upload |
| `413`  | File exceeds 5 MB |
| `415`  | Unsupported file type |
| `422`  | Image decoding / processing failure |
| `500`  | Unexpected server error |

### `GET /outputs/{request_id}/{filename}`

Download a specific generated output file.

---

## CV Processing — Implementation Details

### Silhouette (`silhouette.png`)
1. Extract foreground mask via alpha channel (for PNGs with transparency) or Otsu thresholding (for JPEGs).
2. Apply morphological closing to fill small holes.
3. Find external contours and flood-fill them to create a solid shape.
4. Output: solid black shape on a transparent background.

### Edge / Border (`border.png`)
1. Extract the same foreground mask as above.
2. Run Canny edge detection on both the mask (outer boundary) and the grayscale image content (internal strokes).
3. Combine the two edge maps and apply light dilation for visibility.
4. Output: white edges on a transparent background.

### Grayscale (`grayscale.png`)
1. Convert BGR channels to a single luminance channel.
2. If the source has an alpha channel, preserve it in the output.
3. Output: grayscale image maintaining original transparency.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RECIPIENT_EMAIL` | ✅ | — | Email address to receive processed outputs |
| `SENDER_EMAIL` | ✅ | — | "From" email address (must match SMTP credentials) |
| `SMTP_PASSWORD` | ✅ | — | SMTP password or app-specific password |
| `SMTP_HOST` | ❌ | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | ❌ | `587` | SMTP server port (TLS) |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework / API |
| `uvicorn` | ASGI server |
| `python-multipart` | File upload parsing |
| `opencv-python-headless` | Computer vision (silhouette, edge detection) |
| `Pillow` | Image saving with clean PNG metadata |
| `numpy` | Array operations for image data |
| `python-dotenv` | Load `.env` configuration |
| `jinja2` | Template engine (FastAPI dependency) |
