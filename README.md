# ScreenSage AI 🌿

> **Understand any screen. Take the next step.**

ScreenSage AI helps people make sense of confusing software interfaces, desktop dialogs, complex system settings, and cryptic error messages. Upload, drag-and-drop, or paste (`Ctrl+V`) a screenshot, ask questions about it, and receive accurate, actionable explanations powered by Google's hosted **`gemma-4-31b-it`** multimodal model through the Google Gemini API (official `google-genai` SDK).

---

## ✨ Key Features

- **Evidence-Grounded Explanations**: Gemma 4 is prompted strictly on visible screenshot evidence to eliminate visual hallucinations and clarify ambiguous controls.
- **Hosted Google Gen AI Inference**: Powered by Google's hosted Gemini API (`google-genai` SDK) — instant setup with zero local model weights to download.
- **Multilingual Understanding**: Generate explanations in **English**, **Hindi (हिन्दी)**, or **Gujarati (ગુજરાતી)** at the click of a button.
- **Structured Analysis**:
  - 📋 **Screen Summary**: Plain-language overview of what application or website is shown.
  - 💬 **Direct Answer**: Clear, actionable answer to the user's specific inquiry.
  - 🔍 **Visible UI Elements**: Catalog of buttons, menus, inputs, and error banners with their likely purpose.
  - 🎯 **Visual Highlighting**: Bounding-box overlays drawn over grounded image coordinates with bidirectional hover synchronization.
  - 📌 **Verbatim Visible Text**: Extracted error codes and labels directly from the screen.
  - 🚀 **Suggested Next Steps**: Actionable guidance on what to click or check next.
  - ⚠️ **Transparent Uncertainties**: Explicit notice of buttons or settings that are obscured or absent.
- **Multi-Turn Follow-Up Questions**: Continue asking questions about the active screenshot in an ephemeral session without having to re-upload.
- **Privacy & Security by Design**:
  - Backend runs on `127.0.0.1` (localhost).
  - Screenshots are processed in RAM and ephemeral session cache only (1-hour TTL) — images are never permanently written to disk.
  - Transparent disclosure: Selected screenshots and prompts are sent to Google's hosted Gemini API for inference.
  - Immediate memory purge using the "Clear" button.
  - Decompression bomb protection and EXIF metadata stripping.

---

## 🛠️ Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **Backend**: Python 3.12+, FastAPI, Pydantic v2, Pillow, HTTPX, `google-genai`.
- **AI Model Engine**: Google Gemini API (`gemma-4-31b-it` / `gemma-4-26b-a4b-it`).
- **Testing**: `pytest` & `pytest-asyncio` for backend, `Vitest` & `React Testing Library` for frontend.

---

## 🤖 Google Gemini API Configuration

ScreenSage AI connects via the official `google-genai` Python SDK:
- **Default Model**: `gemma-4-31b-it` (with auto-fallback to `gemma-4-26b-a4b-it`)
- **SDK**: `google-genai`

### Getting Your Google Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Create or select a Google Cloud project.
3. Generate an API Key.

### Setting Up Environment Variables
Create a `.env` file in the project root or inside `backend/`:

```dotenv
GOOGLE_API_KEY=your_actual_google_api_key_here
GOOGLE_GEMINI_MODEL=gemma-4-31b-it
INFERENCE_TIMEOUT_SECONDS=120.0
```

> [!IMPORTANT]
> Never commit your `.env` file or API keys to Git. `.env` is already configured in `.gitignore`.

---

## 🚀 Quick Start Guide (Windows)

### 1. Clone the Repository
```powershell
git clone https://github.com/<your-username>/ScreenSage-AI.git
cd "ScreenSage AI"
```

### 2. Configure Environment
Copy `.env.example` to `.env` and paste your `GOOGLE_API_KEY`:
```powershell
Copy-Item .env.example .env
```

### 3. Backend Setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API is now running at `http://127.0.0.1:8000`.

### 4. Frontend Setup
In a new terminal window:
```powershell
cd frontend
npm install
npm run dev
```
Open **[http://127.0.0.1:5173](http://127.0.0.1:5173)** in your browser!

---

## 🧪 Testing and Verification

### 1. Automated Mocked Test Suite
Run the full test suite with mocked Google Gen AI responses:

**Backend (pytest):**
```powershell
python -m pytest backend/tests -v -k "not test_real"
```
*(Runs 27 unit and integration tests covering image sanitization, coordinate normalization, schema enforcement, 401 auth errors, 429 rate limits, and service handling).*

**Frontend (Vitest + React Testing Library):**
```powershell
cd frontend
npm test
```
*(Runs 6 component tests covering the header, tagline, question inputs, language selectors, and explanation cards).*

**Production Build Validation:**
```powershell
cd frontend
npm run build
```

---

### 2. Live Google Gemini API Verification (Requires API Key)

When `GOOGLE_API_KEY` is present in your `.env` or environment:

```powershell
python -m pytest backend/tests/test_real_google.py -v -s
```
*(Executes real text inference arithmetic check and multimodal screenshot analysis against the Google Gemini API, verifying visual grounding and coordinate extraction).*

---

## 🌐 API Specification

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Returns backend health, model name, and tagline. |
| `GET` | `/api/ai/status` | Reports configuration status without exposing secret keys. |
| `POST` | `/api/analyze-screenshot` | Multipart form accepting `image`, `question`, and `language` ('en', 'hi', 'gu'). Returns structured explanation. |
| `POST` | `/api/generate-text` | Accepts `{ "prompt": string }` for text reasoning verification. |
| `POST` | `/api/follow-up` | Accepts `{ "session_id": string, "question": string, "language": string }` for multi-turn questions. |
| `DELETE` | `/api/session/{id}` | Privacy endpoint: Immediately purges cached screenshot data from memory. |

---

## ⚠️ Troubleshooting & Common Errors

- **HTTP 401 Unauthorized**: The `GOOGLE_API_KEY` provided is invalid or expired. Verify your key in Google AI Studio.
- **HTTP 429 Too Many Requests**: You have exceeded the Google API rate limit or quota. Wait a few moments before sending another request.
- **HTTP 503 Service Unavailable / High Demand**: The Google AI model cluster is experiencing temporary load. ScreenSage AI will automatically retry on available model fallbacks.
- **Notice on Hosted Operation**: Selected screenshots and prompts are sent over secure HTTPS to Google's hosted Gemini API for inference. An active internet connection is required.

---

## 📄 License

This project is licensed under the **[Apache-2.0 License](LICENSE)**.
Google Gemma 4 weights are subject to the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
