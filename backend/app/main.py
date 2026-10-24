"""FastAPI application entrypoint for ScreenSage AI.
Upgraded with NVIDIA-hosted google/gemma-4-31b-it multimodal integration.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.schemas import (
    HealthResponse,
    AIStatusResponse,
    AnalysisResponse,
    FollowUpRequest,
    FollowUpResponse,
    ImageMetadata,
    TextPromptRequest,
    TextPromptResponse,
)
from backend.app.image_utils import validate_and_process_image
from backend.app.session_manager import session_manager
from backend.app.services.nvidia_gemma import nvidia_service

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Understand any screen. Take the next step. Powered by NVIDIA google/gemma-4-31b-it.",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Check backend health and NVIDIA Gemma 4 configuration status.
    """
    has_key = nvidia_service.is_configured()
    status_label = "ok" if has_key else "warning"
    msg = (
        f"Ready: NVIDIA {settings.NVIDIA_MODEL} is configured and active."
        if has_key
        else "NVIDIA API key not set. Set NVIDIA_API_KEY in the backend .env file to enable inference."
    )

    return HealthResponse(
        status=status_label,
        nvidia_configured=has_key,
        model=settings.NVIDIA_MODEL,
        tagline=settings.PRODUCT_TAGLINE,
        message=msg,
    )


@app.get("/api/ai/status", response_model=AIStatusResponse)
async def ai_status():
    """
    Retrieve AI configuration status without exposing credentials.
    """
    return AIStatusResponse(
        configured=nvidia_service.is_configured(),
        model=settings.NVIDIA_MODEL,
        provider="NVIDIA",
        has_key=nvidia_service.is_configured(),
        tagline=settings.PRODUCT_TAGLINE,
        endpoint=nvidia_service.endpoint,
    )


@app.post("/api/analyze-screenshot", response_model=AnalysisResponse)
async def analyze_screenshot(
    image: UploadFile = File(..., description="Screenshot file (PNG, JPG, or WEBP)"),
    question: str = Form(default="What is this screen showing?", description="User's inquiry about the screenshot"),
    language: str = Form(default="en", description="Explanation language ('en', 'hi', 'gu')"),
):
    """
    Analyze an uploaded screenshot using NVIDIA-hosted google/gemma-4-31b-it.
    Validates image, prepares multimodal payload, and returns structured grounded explanation.
    """
    if not question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A question about the screenshot is required.",
        )

    # 1. Read file bytes safely
    try:
        file_bytes = await image.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded image: {str(e)}",
        )

    # 2. Validate, sanitize, and encode image
    b64_image, metadata = validate_and_process_image(
        file_bytes=file_bytes,
        content_type=image.content_type or "image/png"
    )

    # Determine correct MIME type for data URL
    format_lower = metadata.get("format", "png").lower()
    mime_type = "image/jpeg" if format_lower in ("jpg", "jpeg") else (
        "image/webp" if format_lower == "webp" else "image/png"
    )

    # 3. Create ephemeral in-memory session (never permanently written to disk)
    session_id = session_manager.create_session(image_b64=b64_image, metadata=metadata)
    session = session_manager.get_session(session_id)

    # 4. Perform NVIDIA Gemma 4 Multimodal Inference
    explanation, used_tag, duration = await nvidia_service.analyze_screenshot(
        image_b64=b64_image,
        question=question,
        language=language,
        mime_type=mime_type,
    )

    # 5. Record session context for follow-up questions
    if session:
        session.last_explanation = explanation
        session.add_message("user", question)
        session.add_message("assistant", explanation.answer_to_user_question)

    return AnalysisResponse(
        session_id=session_id,
        question=question,
        language=language,
        explanation=explanation,
        model_tag=used_tag,
        inference_duration_seconds=duration,
        timestamp=datetime.now(timezone.utc).isoformat(),
        image_metadata=ImageMetadata(**metadata),
    )


# Alias /api/analyze to /api/analyze-screenshot for seamless backward compatibility
@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_alias(
    image: UploadFile = File(..., description="Screenshot file (PNG, JPG, or WEBP)"),
    question: str = Form(default="What is this screen showing?"),
    language: str = Form(default="en"),
):
    return await analyze_screenshot(image=image, question=question, language=language)


@app.post("/api/generate-text", response_model=TextPromptResponse)
async def generate_text_endpoint(req: TextPromptRequest):
    """
    Test endpoint for text-only queries with google/gemma-4-31b-it.
    """
    answer, model_name, duration = await nvidia_service.generate_text(req.prompt)
    return TextPromptResponse(
        answer=answer,
        model=model_name,
        duration_seconds=duration,
    )


@app.post("/api/follow-up", response_model=FollowUpResponse)
async def follow_up_question(request: FollowUpRequest):
    """
    Ask follow-up questions about the same screenshot without re-uploading.
    Grounds answer in the retained in-memory session image.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Follow-up question cannot be empty.",
        )

    session = session_manager.get_session(request.session_id)
    if not session or not session.image_b64:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session has expired or screenshot was cleared. Please upload the screenshot again.",
        )

    summary = session.last_explanation.screen_summary if session.last_explanation else "Previous screenshot."
    original_q = session.conversation_history[0]["content"] if session.conversation_history else "Initial question."
    original_a = session.conversation_history[1]["content"] if len(session.conversation_history) > 1 else ""

    format_lower = session.metadata.get("format", "png").lower()
    mime_type = "image/jpeg" if format_lower in ("jpg", "jpeg") else (
        "image/webp" if format_lower == "webp" else "image/png"
    )

    follow_up_resp, used_tag, duration = await nvidia_service.follow_up_chat(
        image_b64=session.image_b64,
        question=request.question,
        summary=summary,
        original_question=original_q,
        original_answer=original_a,
        language=request.language or "en",
        mime_type=mime_type,
    )

    follow_up_resp.session_id = request.session_id
    follow_up_resp.model_tag = used_tag
    follow_up_resp.inference_duration_seconds = duration

    # Update session history
    session.add_message("user", request.question)
    session.add_message("assistant", follow_up_resp.answer)

    return follow_up_resp


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """
    Privacy endpoint: Explicitly purge session screenshot and context from server memory.
    """
    deleted = session_manager.delete_session(session_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"session_id": session_id, "cleared": deleted, "message": "Session screenshot cleared from memory."},
    )
