"""Real live integration tests for Google Gemini / Gemma 4 API.
Runs only when GOOGLE_API_KEY is configured in the environment or .env file.
Never claims a real API test passed unless it actually ran against the live endpoint.
"""

import io
import pytest
from PIL import Image, ImageDraw
from backend.app.services.google_gemini import google_service
from backend.app.image_utils import validate_and_process_image


def create_sample_screenshot() -> bytes:
    """Generate a clean synthetic application screenshot with buttons and text."""
    img = Image.new("RGB", (640, 480), color="#102a1e")
    draw = ImageDraw.Draw(img)

    # Draw header bar
    draw.rectangle([0, 0, 640, 60], fill="#081710")
    draw.text((20, 20), "ScreenSage AI Control Center", fill="#e9c46a")

    # Draw card
    draw.rectangle([50, 100, 590, 380], fill="#1b4332", outline="#2d6a4f", width=2)
    draw.text((80, 130), "System Status: Online", fill="#4ade80")
    draw.text((80, 170), "Memory Usage: 42%", fill="#f8fafc")

    # Draw action button
    draw.rectangle([80, 240, 280, 290], fill="#e06d53")
    draw.text((100, 255), "Restart Service", fill="#ffffff")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_real_google_text_multiplication():
    """
    Test A: Text API
    Ask the model: 'What is 17 * 23?'
    Expected answer contains: '391'
    """
    if not google_service.is_configured():
        pytest.skip("Skipping Test A: GOOGLE_API_KEY is not configured in environment or .env")

    answer, model, duration = await google_service.generate_text("What is 17 * 23? Return only the numeric answer.")
    assert "391" in answer
    print(f"\n[REAL GOOGLE TEST A PASSED] Model: {model}, Duration: {duration}s, Answer: {answer}")


@pytest.mark.asyncio
async def test_real_google_screenshot_multimodal():
    """
    Test B: Screenshot API
    Upload an actual screenshot and ask a question whose answer can be verified visually.
    """
    if not google_service.is_configured():
        pytest.skip("Skipping Test B: GOOGLE_API_KEY is not configured in environment or .env")

    raw_bytes = create_sample_screenshot()
    b64_img, meta = validate_and_process_image(raw_bytes, "image/png")

    explanation, model, duration = await google_service.analyze_screenshot(
        image_b64=b64_img,
        question="What is the exact text on the button in this screenshot?",
        language="en",
        mime_type="image/png",
    )

    assert explanation.screen_summary != ""
    assert "Restart Service" in explanation.answer_to_user_question or any(
        "restart" in el.element_name.lower() or "restart" in (el.visible_text or "").lower()
        for el in explanation.visible_ui_elements
    )
    print(f"\n[REAL GOOGLE TEST B PASSED] Model: {model}, Duration: {duration}s")
    print(f"Summary: {explanation.screen_summary}")
    print(f"Answer: {explanation.answer_to_user_question}")
