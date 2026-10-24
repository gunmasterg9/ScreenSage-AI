"""FastAPI application entrypoint for ScreenSage AI.
Powered by Google Gemini API / Gemma 4 multimodal integration using official google-genai SDK.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
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
    BatchItemResult,
    BatchAnalysisResponse,
    BatchSessionDeleteResponse,
)
from backend.app.image_utils import validate_and_process_image
from backend.app.session_manager import session_manager
from backend.app.services.google_gemini import google_service

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Understand any screen. Take the next step. Powered by Google Gemini / Gemma 4.",
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
    Check backend health and Google Gemini API configuration status.
    """
    has_key = google_service.is_configured()
    status_label = "ok" if has_key else "warning"
    msg = (
        f"Ready: Google {settings.GOOGLE_GEMINI_MODEL} is configured and active."
        if has_key
        else "Google API key not set. Set GOOGLE_API_KEY in the backend .env file to enable inference."
    )

    return HealthResponse(
        status=status_label,
        google_configured=has_key,
        nvidia_configured=has_key,
        model=settings.GOOGLE_GEMINI_MODEL,
        tagline=settings.PRODUCT_TAGLINE,
        message=msg,
    )


@app.get("/api/ai/status", response_model=AIStatusResponse)
async def ai_status():
    """
    Retrieve AI configuration status without exposing credentials.
    """
    has_key = google_service.is_configured()
    return AIStatusResponse(
        configured=has_key,
        model=settings.GOOGLE_GEMINI_MODEL,
        provider="Google Gemini API",
        has_key=has_key,
        tagline=settings.PRODUCT_TAGLINE,
        endpoint="Google Gen AI API (google-genai)",
        privacy_disclosure=(
            "Privacy notice: Selected screenshots and questions are processed securely via Google's hosted Gemini API. "
            "Screenshots remain in-memory only on this server for the duration of your session (1 hour TTL) "
            "or until you explicitly click Clear."
        ),
        max_upload_size_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        max_batch_images=settings.MAX_BATCH_IMAGES,
        max_batch_total_size_bytes=settings.MAX_BATCH_TOTAL_SIZE_BYTES,
    )


@app.post("/api/analyze-screenshot", response_model=AnalysisResponse)
async def analyze_screenshot(
    image: UploadFile = File(..., description="Screenshot file (PNG, JPG, or WEBP)"),
    question: str = Form(default="What is this screen showing?", description="User's inquiry about the screenshot"),
    language: str = Form(default="en", description="Explanation language ('en', 'hi', 'gu')"),
):
    """
    Analyze an uploaded screenshot using Google Gemini / Gemma 4 multimodal model.
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

    # Determine correct MIME type
    format_lower = metadata.get("format", "png").lower()
    mime_type = "image/jpeg" if format_lower in ("jpg", "jpeg") else (
        "image/webp" if format_lower == "webp" else "image/png"
    )

    # 3. Create ephemeral in-memory session (never permanently written to disk)
    session_id = session_manager.create_session(image_b64=b64_image, metadata=metadata)
    session = session_manager.get_session(session_id)

    # 4. Perform Google Gemini Multimodal Inference
    explanation, used_tag, duration = await google_service.analyze_screenshot(
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
    Test endpoint for text-only queries with Google Gemini / Gemma 4 model.
    """
    answer, model_name, duration = await google_service.generate_text(req.prompt)
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

    follow_up_resp, used_tag, duration = await google_service.follow_up_chat(
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


@app.post("/api/analyze-batch", response_model=BatchAnalysisResponse)
async def analyze_batch(
    images: List[UploadFile] = File(..., description="List of screenshot files (PNG, JPG, or WEBP)"),
    question: str = Form(default="What are these screens showing?", description="User's inquiry across the screenshots"),
    language: str = Form(default="en", description="Explanation language ('en', 'hi', 'gu')"),
    generate_summary: bool = Form(default=True, description="Whether to synthesize an overarching multi-screen summary"),
):
    """
    Analyze multiple screenshots with bounded concurrency using Google Gemini API.
    Validates limits, runs concurrent grounded analyses, and synthesizes a combined summary.
    """
    if not question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A question about the screenshots is required.",
        )

    if not images or len(images) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one screenshot must be provided for batch analysis.",
        )

    if len(images) > settings.MAX_BATCH_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch image count ({len(images)}) exceeds maximum limit of {settings.MAX_BATCH_IMAGES} images.",
        )

    batch_id = str(uuid.uuid4())
    start_batch_time = time.perf_counter()

    # Pre-read and validate total size
    file_payloads: List[Tuple[str, bytes, str]] = []
    total_bytes = 0

    for img in images:
        try:
            content = await img.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read file {img.filename}: {str(e)}",
            )
        total_bytes += len(content)
        file_payloads.append((img.filename or "screenshot.png", content, img.content_type or "image/png"))

    if total_bytes > settings.MAX_BATCH_TOTAL_SIZE_BYTES:
        max_mb = settings.MAX_BATCH_TOTAL_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Total batch size ({round(total_bytes / (1024*1024), 2)} MB) exceeds maximum allowed limit of {max_mb} MB.",
        )

    semaphore = asyncio.Semaphore(settings.BATCH_CONCURRENCY)
    created_session_ids: List[str] = []

    async def process_item(idx: int, filename: str, file_bytes: bytes, content_type: str) -> BatchItemResult:
        item_id = f"item_{idx + 1}"
        # 1. Validate & process image
        try:
            b64_image, metadata = validate_and_process_image(
                file_bytes=file_bytes,
                content_type=content_type,
            )
        except HTTPException as he:
            return BatchItemResult(
                item_id=item_id,
                filename=filename,
                success=False,
                status="error",
                error=he.detail,
            )
        except Exception as ex:
            return BatchItemResult(
                item_id=item_id,
                filename=filename,
                success=False,
                status="error",
                error=f"Image validation failed: {str(ex)}",
            )

        format_lower = metadata.get("format", "png").lower()
        mime_type = "image/jpeg" if format_lower in ("jpg", "jpeg") else (
            "image/webp" if format_lower == "webp" else "image/png"
        )

        # 2. Create session
        session_id = session_manager.create_session(image_b64=b64_image, metadata=metadata)
        created_session_ids.append(session_id)
        session = session_manager.get_session(session_id)

        # 3. Multimodal inference under semaphore
        async with semaphore:
            try:
                explanation, used_tag, duration = await google_service.analyze_screenshot(
                    image_b64=b64_image,
                    question=question,
                    language=language,
                    mime_type=mime_type,
                )
            except HTTPException as he:
                return BatchItemResult(
                    item_id=item_id,
                    filename=filename,
                    success=False,
                    status="error",
                    error=he.detail,
                )
            except Exception as ex:
                return BatchItemResult(
                    item_id=item_id,
                    filename=filename,
                    success=False,
                    status="error",
                    error=f"Inference failed: {str(ex)}",
                )

        if session:
            session.last_explanation = explanation
            session.add_message("user", question)
            session.add_message("assistant", explanation.answer_to_user_question)

        analysis = AnalysisResponse(
            session_id=session_id,
            question=question,
            language=language,
            explanation=explanation,
            model_tag=used_tag,
            inference_duration_seconds=duration,
            timestamp=datetime.now(timezone.utc).isoformat(),
            image_metadata=ImageMetadata(**metadata),
        )

        return BatchItemResult(
            item_id=item_id,
            filename=filename,
            success=True,
            status="completed",
            analysis=analysis,
        )

    tasks = [
        process_item(i, fn, bts, ct)
        for i, (fn, bts, ct) in enumerate(file_payloads)
    ]
    results: List[BatchItemResult] = await asyncio.gather(*tasks)

    successful = [r for r in results if r.success and r.analysis]
    failed = [r for r in results if not r.success]

    # Register all sessions for this batch so they can be deleted together
    session_manager.register_batch(batch_id, created_session_ids)

    # 4. Generate combined summary if requested and at least one image succeeded
    combined_summary: Optional[str] = None
    if generate_summary and len(successful) > 0:
        summaries_for_synthesis = [
            {
                "filename": r.filename,
                "summary": r.analysis.explanation.screen_summary,
                "answer": r.analysis.explanation.answer_to_user_question,
            }
            for r in successful
            if r.analysis
        ]
        combined_summary = await google_service.synthesize_batch_summary(
            question=question,
            screen_summaries=summaries_for_synthesis,
            language=language,
        )

    total_duration = round(time.perf_counter() - start_batch_time, 2)

    return BatchAnalysisResponse(
        batch_id=batch_id,
        total_images=len(images),
        successful_count=len(successful),
        failed_count=len(failed),
        results=results,
        combined_summary=combined_summary,
        question=question,
        language=language,
        total_duration_seconds=total_duration,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.delete("/api/batch-session/{batch_id}", response_model=BatchSessionDeleteResponse)
async def clear_batch_session(batch_id: str):
    """
    Privacy endpoint: Explicitly purge all screenshots in a batch session from server RAM.
    """
    cleared_count = session_manager.delete_batch(batch_id)
    return BatchSessionDeleteResponse(
        batch_id=batch_id,
        cleared_count=cleared_count,
        cleared=True,
        message=f"Purged {cleared_count} batch screenshot session(s) from memory.",
    )
