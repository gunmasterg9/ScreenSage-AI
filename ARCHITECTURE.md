# ScreenSage AI — Architecture & Technical Design (Google Gemini API Integration)

**Product Tagline:** *Understand any screen. Take the next step.*

ScreenSage AI is an open-source, privacy-first desktop application that allows users to upload, drag-and-drop, or paste (`Ctrl+V`) screenshots of software interfaces, desktop dialogs, websites, and error messages, providing plain-language, actionable explanations powered by Google's hosted **`gemma-4-31b-it`** multimodal model via the Google Gemini API (official `google-genai` SDK).

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
 │  3. Dedicated AI Service (`app/services/google_gemini.py`):  │
 │     - Multilingual instructions (English, Hindi, Gujarati)   │
 │     - Google Gen AI SDK (`genai.Client`) integration         │
 │     - Strict Pydantic schema validation & coordinate guard   │
 └──────────────┬──────────────────────────────▲────────────────┘
                │ HTTPS POST to Google Gemini API
                │ Bearer GOOGLE_API_KEY
                │ Multimodal content: PIL Image + System/User Prompt
                ▼                               │
 ┌──────────────────────────────────────────────┴───────────────┐
 │                Google Gemini API Service                     │
 │  (Official Google Gen AI SDK `google-genai`)                 │
 │                                                              │
 │  Hosted Model: `gemma-4-31b-it` / `gemma-4-26b-a4b-it`       │
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
  - Centralized environment settings with Pydantic settings management for `GOOGLE_API_KEY`, `GOOGLE_GEMINI_MODEL`, and `INFERENCE_TIMEOUT_SECONDS`.
- **Image Processing & Security** (`app/image_utils.py`):
  - Pillow decompression bomb protection (`MAX_IMAGE_PIXELS = 10_000_000`).
  - MIME type and format validation (`PNG`, `JPEG`, `WEBP`).
  - EXIF metadata stripping to protect privacy.
  - Base64 encoding for in-memory session caching.
- **In-Memory Session Manager** (`app/session_manager.py`):
  - Keeps screenshot in RAM only during active sessions so users can ask multiple follow-up questions without re-uploading.
  - Thread-safe TTL expiration (1 hour) automatically purges stale image data.
  - Explicit deletion endpoint (`DELETE /api/session/{session_id}`) wipes image bytes upon request.
- **Dedicated AI Service** (`app/services/google_gemini.py`):
  - Communicates with Google's hosted Gemini API using the official `google-genai` SDK.
  - Passes in-memory PIL images directly to `client.models.generate_content()`.
  - Protects credentials: never hardcodes or exposes `GOOGLE_API_KEY` in logs or HTTP responses.
  - Handles 401 (auth), 429 (rate limits), and 503 (high demand) with graceful model fallback and clear user feedback.

---

## 3. Multimodal Request Flow with Google Gen AI SDK

Requests to Google Gemini API are managed through the official SDK:

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.GOOGLE_API_KEY)
response = client.models.generate_content(
    model="gemma-4-31b-it",
    contents=[
        pil_image,
        prompt_text,
    ],
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT_BASE,
        temperature=0.2,
        top_p=0.7,
        max_output_tokens=2048,
        response_mime_type="application/json",
    ),
)
```

---

## 4. Privacy & Security Model

- **Localhost Backend**: Backend binds to `127.0.0.1` by default.
- **Direct Model Transmission**: Image bytes and prompts are sent directly from the local backend to Google's hosted Gemini API over HTTPS; no intermediate third-party image hosts are used.
- **No Disk Persistence**: Screenshots are processed in RAM and ephemeral session cache; no raw screenshot files are saved to disk.
- **Credential Protection**: `GOOGLE_API_KEY` is loaded strictly on the backend, excluded from Git via `.gitignore`, and omitted from `/api/ai/status` responses.
- **No Autonomous Execution**: Suggestions provided in the explanation are purely advisory text for the user to review. The app never executes commands automatically.

---

## 5. Bulk Upload, Batch Analysis & Vercel Deployment Architecture

### Batch Processing Design
ScreenSage AI supports queuing and analyzing up to 10 screenshots in a single session:
- **Client Queue**: The React frontend provides a responsive thumbnail queue with individual progress, status badges, remove, retry, and cancellation controls.
- **Server Validation**: The FastAPI backend enforces server-side format (`PNG`, `JPEG`, `WEBP`), dimension, file size (10 MB/file), batch total size (30 MB max), and Pillow decompression bomb limits.
- **Bounded Concurrency**: Uses an `asyncio.Semaphore` (configurable via `BATCH_CONCURRENCY=2`) to prevent exceeding Google AI API rate limits or cluster quotas while executing in parallel.
- **Partial Failure Resilience**: If one screenshot is corrupted or exceeds limits, it is marked with an error while the remaining screenshots continue processing.
- **Synthesized Overview**: An overarching multi-screen narrative (`synthesize_batch_summary`) correlates evidence across all screens.
- **Ephemeral Lifecycle**: In-memory sessions are mapped to `batch_id` and can be purged immediately with `DELETE /api/batch-session/{batch_id}`.

### Vercel Deployment Architecture & Constraints
- **Vercel Serverless Function Limits**:
  - Request body size limit: **4.5 MB** on Hobby and Pro plans.
  - Execution duration timeout: **10 seconds** (Hobby) or **15–60 seconds** (Pro).
  - Attempting to process large multi-image batches (10–30 MB) with multimodal inference directly inside Vercel serverless functions would result in immediate `413 FUNCTION_PAYLOAD_TOO_LARGE` errors and `504` execution timeouts.
- **Recommended Production Topology**:
  - **Frontend (Vercel)**: Deployed as a high-performance static Vite Single Page Application using `frontend/vercel.json`.
  - **Backend (Dedicated FastAPI Host)**: Deployed on a persistent host (e.g. Render, Railway, Fly.io, or VPS) where body sizes up to 30 MB, execution durations up to 120s, and RAM-only session caching operate without serverless payload limits.
  - **Connection**: Set `VITE_API_BASE=https://<your-deployed-backend-url>/api` in Vercel project environment variables to route requests directly to the dedicated backend.
