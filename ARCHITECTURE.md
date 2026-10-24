# ScreenSage AI — Architecture & Technical Design (NVIDIA Gemma 4 Integration)

**Product Tagline:** *Understand any screen. Take the next step.*

ScreenSage AI is an open-source, privacy-first desktop application that allows users to upload, drag-and-drop, or paste (`Ctrl+V`) screenshots of software interfaces, desktop dialogs, websites, and error messages, providing plain-language, actionable explanations powered by NVIDIA's hosted **`google/gemma-4-31b-it`** model.

---

## 1. System Overview

```
 ┌──────────────────────────────────────────────────────────────┐
 │                     User Web Browser                         │
 │  (React 18 + Vite + TypeScript + Tailwind CSS UI Layer)      │
 └──────────────┬──────────────────────────────▲────────────────┘
                │ HTTP POST /api/analyze-screenshot
                │ Multipart Form (Image + Question + Language)
                ▼                               │
 ┌──────────────────────────────────────────────┴───────────────┐
 │                   FastAPI Backend Server                     │
 │  (Bound to localhost: 127.0.0.1:8000 by default)             │
 │                                                              │
 │  1. Image Validation & Sanitization (Pillow):               │
 │     - Format verification (PNG, JPEG, WEBP)                  │
 │     - Decompression bomb guard (Image.MAX_IMAGE_PIXELS)      │
 │     - Dimension scaling and EXIF stripping                   │
 │                                                              │
 │  2. Ephemeral In-Memory Session Cache:                       │
 │     - TTL-based memory cache (never writes images to disk)   │
 │     - Multi-turn follow-up question context retention       │
 │     - Explicit deletion endpoint (/api/session/{id})         │
 │                                                              │
 │  3. Dedicated AI Service (`services/nvidia_gemma.py`):       │
 │     - Multilingual instructions (English, Hindi, Gujarati)   │
 │     - Prepares standard OpenAI-compatible multimodal payload │
 │     - Strict Pydantic schema validation & coordinate guard   │
 └──────────────┬──────────────────────────────▲────────────────┘
                │ HTTPS POST /v1/chat/completions
                │ Bearer NVIDIA_API_KEY
                │ Data URL: data:image/png;base64,...
                ▼                               │
 ┌──────────────────────────────────────────────┴───────────────┐
 │               NVIDIA NIM Hosted API Service                  │
 │  (https://integrate.api.nvidia.com/v1)                       │
 │                                                              │
 │  Hosted Model: `google/gemma-4-31b-it`                       │
 │  - High-speed cloud inference without local model downloads  │
 │  - Multimodal perception (OCR, UI structure, error traces)   │
 └──────────────────────────────────────────────────────────────┘
```

---

## 2. Component Separation & Responsibilities

### Frontend (`/frontend`)
- **UI Architecture**: Component-driven architecture built with React, Vite, TypeScript, and Tailwind CSS.
- **Multilingual Support**: Supports English (`en`), Hindi (`hi`), and Gujarati (`gu`) explanation generations.
- **Image Preview & Visual Overlays** (`ImagePreviewWithOverlays.tsx`):
  - Renders the screenshot in a responsive canvas.
  - Draws an interactive overlay layer using normalized percentages (`ymin`, `xmin`, `ymax`, `xmax`).
  - Supports bidirectional hover-synchronization: hovering over a bounding box highlights the corresponding element card, and hovering over a card highlights its box on the image.
  - Safely falls back to numbered explanation cards when the model's coordinates are unverified or missing.
- **Drag & Drop + Clipboard Listener** (`ImageUploader.tsx`):
  - Supports file selection, drag-and-drop, and listening for global `paste` (`Ctrl+V`) events.
- **Inquiry Management** (`QuestionInput.tsx`, `SuggestedQuestions.tsx`):
  - Provides suggested question chips, language toggles, and an accessible custom query input with keyboard shortcuts (`Enter`).
- **Structured Explanation Display** (`ExplanationViewer.tsx`):
  - Visual hierarchy distinguishing:
    1. Direct answer to the user's specific inquiry.
    2. High-level screen summary.
    3. Visible UI elements with purpose and extracted text.
    4. Key element purpose takeaways.
    5. Verbatim visible text extracted from screen.
    6. Actionable next steps.
    7. Transparent uncertainties and missing visual context.

### Backend (`/backend`)
- **FastAPI Application** (`app/main.py`):
  - Exposes REST endpoints (`/api/health`, `/api/ai/status`, `/api/analyze-screenshot`, `/api/generate-text`, `/api/follow-up`, `/api/session/{id}`).
- **Configuration** (`app/config.py`):
  - Centralized environment settings with Pydantic settings management for `NVIDIA_API_KEY`, `NVIDIA_MODEL`, and `NVIDIA_BASE_URL`.
- **Image Processing & Security** (`app/image_utils.py`):
  - Pillow decompression bomb protection (`MAX_IMAGE_PIXELS = 10_000_000`).
  - MIME type and format validation (`PNG`, `JPEG`, `WEBP`).
  - EXIF metadata stripping to protect privacy.
  - Base64 encoding for the data URL payload.
- **In-Memory Session Manager** (`app/session_manager.py`):
  - Keeps screenshot in RAM only during active sessions so users can ask multiple follow-up questions without re-uploading.
  - Thread-safe TTL expiration (1 hour) automatically purges stale image data.
  - Explicit deletion endpoint (`DELETE /api/session/{session_id}`) wipes image bytes upon request.
- **Dedicated AI Service** (`app/services/nvidia_gemma.py`):
  - Sends requests to `https://integrate.api.nvidia.com/v1/chat/completions`.
  - Formats image inputs as base64 data URLs in the official `image_url` structure.
  - Protects credentials: never hardcodes or exposes `NVIDIA_API_KEY` in logs or HTTP responses.
  - Handles 401 (auth), 429 (rate limits), 502/503 (upstream), and 504 (timeout) with clear user feedback.

---

## 3. Multimodal Request Format for NVIDIA API

Requests to `https://integrate.api.nvidia.com/v1/chat/completions` follow the official OpenAI-compatible multimodal content standard:

```json
{
  "model": "google/gemma-4-31b-it",
  "messages": [
    {
      "role": "system",
      "content": "You are ScreenSage AI..."
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Please analyze this screenshot and answer: What does this error mean?"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
          }
        }
      ]
    }
  ],
  "temperature": 0.2,
  "top_p": 0.7,
  "max_tokens": 1500
}
```

---

## 4. Privacy & Security Model

- **Localhost Backend**: Backend binds to `127.0.0.1` by default.
- **Direct Model Transmission**: Image bytes are sent directly from the local backend to NVIDIA's endpoint over HTTPS; no intermediate third-party image hosts are used.
- **No Disk Persistence**: Screenshots are processed in RAM and ephemeral session cache; no raw screenshot files are saved to disk.
- **Credential Protection**: `NVIDIA_API_KEY` is loaded strictly on the backend, excluded from Git via `.gitignore`, and omitted from `/api/ai/status` responses.
- **No Autonomous Execution**: Suggestions provided in the explanation are purely advisory text for the user to review. The app never executes commands automatically.
