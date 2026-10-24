import {
  HealthResponse,
  AIStatusResponse,
  AnalysisResponse,
  FollowUpResponse,
  SupportedLanguage,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/+$/, '') || '/api';

export async function checkHealth(): Promise<HealthResponse> {
  const resp = await fetch(`${API_BASE}/health`);
  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Health check failed with status ${resp.status}`);
  }
  return resp.json();
}

export async function checkAIStatus(): Promise<AIStatusResponse> {
  const resp = await fetch(`${API_BASE}/ai/status`);
  if (!resp.ok) {
    throw new Error(`Failed to check AI status: ${resp.status}`);
  }
  return resp.json();
}

export async function analyzeScreenshot(
  imageFile: File,
  question: string,
  language: SupportedLanguage = 'en'
): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('question', question);
  formData.append('language', language);

  const resp = await fetch(`${API_BASE}/analyze-screenshot`, {
    method: 'POST',
    body: formData,
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Analysis failed with status ${resp.status}`);
  }

  return resp.json();
}

export async function askFollowUp(
  sessionId: string,
  question: string,
  language: SupportedLanguage = 'en'
): Promise<FollowUpResponse> {
  const resp = await fetch(`${API_BASE}/follow-up`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      question,
      language,
    }),
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Follow-up request failed with status ${resp.status}`);
  }

  return resp.json();
}

export async function clearSession(sessionId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/session/${sessionId}`, {
      method: 'DELETE',
    });
  } catch (err) {
    console.error('Error clearing session:', err);
  }
}

export async function generateText(prompt: string): Promise<{ answer: string; model: string; duration_seconds: number }> {
  const resp = await fetch(`${API_BASE}/generate-text`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ prompt }),
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(errorData.detail || `Text prompt failed with status ${resp.status}`);
  }

  return resp.json();
}
