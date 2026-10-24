# ScreenSage AI 🌿

> **Understand any screen. Take the next step.**

ScreenSage AI helps people make sense of confusing software interfaces, desktop dialogs, complex system settings, and cryptic error messages. Upload, drag-and-drop, or paste (`Ctrl+V`) a screenshot, ask questions about it, and receive accurate, actionable explanations powered by NVIDIA's hosted **`google/gemma-4-31b-it`** model through the NVIDIA API.

---

## ✨ Key Features

- **Evidence-Grounded Explanations**: Gemma 4 is prompted strictly on visible screenshot evidence to eliminate visual hallucinations and clarify ambiguous controls.
- **Hosted NVIDIA Inference**: Powered by NVIDIA's hosted `google/gemma-4-31b-it` — instant setup with zero local model weights to download.
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
  - Screenshots are processed in RAM and ephemeral session cache only — images are never permanently written to disk.
  - Image bytes are sent directly over HTTPS to NVIDIA's endpoint; no third-party image hosts are used.
  - Immediate memory purge using the "Clear" button.
  - Decompression bomb protection and EXIF metadata stripping.

---

## 🛠️ Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **Backend**: Python 3.12+, FastAPI, Pydantic v2, Pillow, HTTPX.
- **AI Model Engine**: NVIDIA NIM Hosted `google/gemma-4-31b-it`.
- **Testing**: `pytest` & `pytest-asyncio` for backend, `Vitest` & `React Testing Library` for frontend.

---

## 🤖 NVIDIA Gemma 4 API Configuration

ScreenSage AI connects to NVIDIA's official hosted endpoint:
- **Model**: `google/gemma-4-31b-it`
- **Base URL**: `https://integrate.api.nvidia.com/v1`
- **Chat Endpoint**: `https://integrate.api.nvidia.com/v1/chat/completions`

### Getting Your NVIDIA API Key
1. Visit the [NVIDIA API Catalog](https://build.nvidia.com).
2. Sign in and locate `google/gemma-4-31b-it`.
3. Generate an API Key (starts with `nvapi-...`).

### Setting Up Environment Variables
Create a `.env` file in the project root or inside `backend/`:

```dotenv
NVIDIA_API_KEY=nvapi-your_actual_key_here
NVIDIA_MODEL=google/gemma-4-31b-it
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
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
Copy `.env.example` to `.env` and paste your `NVIDIA_API_KEY`:
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
Run the full test suite with mocked NVIDIA responses:

**Backend (pytest):**
```powershell
python -m pytest backend/tests -v
```
*(Runs 29 unit and integration tests covering image sanitization, coordinate normalization, schema enforcement, 401 auth errors, 429 rate limits, and 504 timeouts).*

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

### 2. Live NVIDIA API Verification (Requires API Key)

When `NVIDIA_API_KEY` is present in your `.env` or environment:

#### Test A: Text API Check
Verify text reasoning by querying:
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/generate-text `
  -H "Content-Type: application/json" `
  -d '{"prompt": "What is 17 * 23? Return only the numeric answer."}'
```
Expected output:
```json
{
  "answer": "391",
  "model": "google/gemma-4-31b-it",
  "duration_seconds": 0.82
}
```

#### Test B: Live Multimodal Screenshot API Check
```powershell
python -m pytest backend/tests/test_real_nvidia.py -v -s
```
*(Executes real multimodal inference against a test screenshot and prints the model's visual grounding and response).*

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

- **HTTP 401 Unauthorized**: The `NVIDIA_API_KEY` provided is invalid or expired. Check that the key starts with `nvapi-` and has active credits.
- **HTTP 429 Too Many Requests**: You have exceeded the NVIDIA NIM rate limit. Wait a few moments before sending another request.
- **HTTP 503 Service Unavailable**: `NVIDIA_API_KEY` is missing from the environment or `.env` file.
- **HTTP 504 Gateway Timeout**: The inference took longer than 60 seconds. Try uploading a smaller or lower-resolution screenshot.
- **Notice on Offline Operation**: Because this integration uses NVIDIA's hosted endpoint (`https://integrate.api.nvidia.com`), an active internet connection is required to send screenshots and prompts to NVIDIA for inference.

---

## 📄 License

This project is licensed under the **[Apache-2.0 License](LICENSE)**.
Google Gemma 4 weights are subject to the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
