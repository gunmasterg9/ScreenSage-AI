# Contributing to ScreenSage AI

Welcome! ScreenSage AI is an open-source project created for **Hacktoberfest 2026**. We welcome contributions from developers of all skill levels.

---

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for all participants. Please be respectful, constructive, and collaborative in all discussions and pull requests.

---

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork**:
   ```bash
   git clone https://github.com/<your-username>/ScreenSage-AI.git
   cd ScreenSage-AI
   ```
3. **Set up the Python backend**:
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Set up the React frontend**:
   ```bash
   cd ../frontend
   npm install
   ```
5. **Run local Ollama**:
   Ensure Ollama is running and download Gemma 4:
   ```bash
   ollama pull gemma4:e2b
   ```

---

## Development Workflow

### Running Backend Server
```bash
# In backend directory
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Running Frontend Dev Server
```bash
# In frontend directory
npm run dev
```
Open [http://127.0.0.1:5173](http://127.0.0.1:5173) in your browser.

---

## Running Automated Tests

Always ensure both backend and frontend tests pass before opening a Pull Request:

### Backend Tests (pytest)
```bash
python -m pytest backend/tests -v
```

### Frontend Tests (Vitest)
```bash
cd frontend
npm test
```

### Production Build Validation
```bash
cd frontend
npm run build
```

---

## Pull Request Guidelines

1. Create a feature branch with a descriptive name (`git checkout -b feature/accessible-focus-rings`).
2. Adhere to the existing code structure and design system (warm off-white, deep forest-green typography, restrained coral accents).
3. Do not commit model weights, binary blobs, `.env` files, or private screenshots.
4. Keep frontend and backend responsibilities cleanly separated.
5. Provide clear PR descriptions explaining what was changed and how to test it.
