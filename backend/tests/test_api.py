"""API integration tests for ScreenSage AI endpoints with Google Gemini / Gemma 4."""

import io
import pytest
from PIL import Image
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas import ScreenExplanation, UIElement, BoundingBox

client = TestClient(app)


def create_test_image_bytes(format="PNG", size=(200, 200), color="purple"):
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model" in data
    assert "tagline" in data
    assert data["tagline"] == "Understand any screen. Take the next step."


def test_ai_status_endpoint_never_exposes_secret():
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "model" in data
    assert data["provider"] == "Google Gemini API"
    assert "has_key" in data
    assert "privacy_disclosure" in data
    # Ensure no secret key field is present in response
    assert "api_key" not in data
    assert "key" not in data or data["key"] is None if "key" in data else True


def test_analyze_screenshot_success():
    img_bytes = create_test_image_bytes("PNG")

    fake_explanation = ScreenExplanation(
        screen_summary="A dashboard showing system resources.",
        visible_ui_elements=[
            UIElement(
                id="elem_1",
                element_name="Restart Button",
                element_type="button",
                likely_purpose="Restarts the active service",
                visible_text="Restart",
                bounding_box=BoundingBox(ymin=15.0, xmin=80.0, ymax=25.0, xmax=95.0),
            )
        ],
        likely_purpose_of_important_elements=["Service controls"],
        relevant_visible_text=["Dashboard", "Restart"],
        answer_to_user_question="The restart button is located at the top right.",
        suggested_next_steps=["Click Restart to reboot service"],
        uncertainties_and_missing_visual_information=[],
        coordinate_support_verified=True,
    )

    with patch(
        "backend.app.services.google_gemini.google_service.analyze_screenshot",
        return_value=(fake_explanation, "gemma-4-31b-it", 0.95),
    ):
        response = client.post(
            "/api/analyze-screenshot",
            files={"image": ("screen.png", img_bytes, "image/png")},
            data={"question": "Where is the restart button?", "language": "en"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] != ""
        assert data["language"] == "en"
        assert data["explanation"]["screen_summary"] == "A dashboard showing system resources."
        assert data["explanation"]["coordinate_support_verified"] is True
        assert data["model_tag"] == "gemma-4-31b-it"

        session_id = data["session_id"]

        # Test follow-up endpoint
        with patch(
            "backend.app.services.google_gemini.google_service.follow_up_chat"
        ) as mock_follow:
            from backend.app.schemas import FollowUpResponse
            mock_follow.return_value = (
                FollowUpResponse(
                    session_id=session_id,
                    question="What color is the button?",
                    answer="It is blue with white text.",
                    suggested_next_steps=[],
                    visible_evidence=["Blue background"],
                    uncertainties=[],
                    referenced_elements=[],
                    model_tag="gemma-4-31b-it",
                    inference_duration_seconds=0.45,
                ),
                "gemma-4-31b-it",
                0.45,
            )

            follow_resp = client.post(
                "/api/follow-up",
                json={"session_id": session_id, "question": "What color is the button?"},
            )
            assert follow_resp.status_code == 200
            assert "blue with white text" in follow_resp.json()["answer"]

        # Test session privacy cleanup
        del_resp = client.delete(f"/api/session/{session_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["cleared"] is True

        # Subsequent follow-up should 404
        follow_again = client.post(
            "/api/follow-up",
            json={"session_id": session_id, "question": "Are you still there?"},
        )
        assert follow_again.status_code == 404


def test_analyze_missing_question():
    img_bytes = create_test_image_bytes("PNG")
    response = client.post(
        "/api/analyze-screenshot",
        files={"image": ("screen.png", img_bytes, "image/png")},
        data={"question": "   "},
    )
    assert response.status_code == 400
    assert "question" in response.json()["detail"].lower()


def test_analyze_invalid_file_format():
    response = client.post(
        "/api/analyze-screenshot",
        files={"image": ("file.txt", b"plain text content", "text/plain")},
        data={"question": "What is this?"},
    )
    assert response.status_code in (400, 415)


def test_text_prompt_endpoint():
    with patch(
        "backend.app.services.google_gemini.google_service.generate_text",
        return_value=("391", "gemma-4-31b-it", 0.5),
    ):
        response = client.post(
            "/api/generate-text",
            json={"prompt": "What is 17 * 23?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "391"
        assert data["model"] == "gemma-4-31b-it"


def test_follow_up_empty_question():
    response = client.post(
        "/api/follow-up",
        json={"session_id": "test-id", "question": "   "},
    )
    assert response.status_code in (400, 422)
