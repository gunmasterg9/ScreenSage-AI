"""Unit and integration tests for bulk image upload and batch analysis in ScreenSage AI."""

import io
import pytest
from PIL import Image
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.schemas import ScreenExplanation, UIElement, BoundingBox

client = TestClient(app)


def create_test_image_bytes(format="PNG", size=(120, 120), color="blue") -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


@pytest.fixture
def mock_gemini_analysis():
    explanation = ScreenExplanation(
        screen_summary="Test screen showing system preferences.",
        visible_ui_elements=[
            UIElement(
                id="elem_1",
                element_name="Save Button",
                element_type="button",
                likely_purpose="Saves active preferences",
                visible_text="Save",
                bounding_box=BoundingBox(ymin=10.0, xmin=20.0, ymax=20.0, xmax=35.0),
            )
        ],
        likely_purpose_of_important_elements=["Save button"],
        relevant_visible_text=["Save"],
        answer_to_user_question="The screen contains a preferences dialog with a Save button.",
        suggested_next_steps=["Click Save to confirm changes."],
        uncertainties_and_missing_visual_information=[],
        coordinate_support_verified=True,
    )
    return explanation, "gemma-4-31b-it", 1.25


def test_ai_status_returns_batch_limits():
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert "max_batch_images" in data
    assert data["max_batch_images"] == settings.MAX_BATCH_IMAGES
    assert "max_batch_total_size_bytes" in data
    assert data["max_batch_total_size_bytes"] == settings.MAX_BATCH_TOTAL_SIZE_BYTES


def test_batch_analyze_success(mock_gemini_analysis):
    img1 = create_test_image_bytes("PNG", color="red")
    img2 = create_test_image_bytes("JPEG", color="green")

    files = [
        ("images", ("screen1.png", img1, "image/png")),
        ("images", ("screen2.jpg", img2, "image/jpeg")),
    ]
    data = {
        "question": "What are these screens displaying?",
        "language": "en",
        "generate_summary": "true",
    }

    with patch(
        "backend.app.services.google_gemini.google_service.analyze_screenshot",
        return_value=mock_gemini_analysis,
    ), patch(
        "backend.app.services.google_gemini.google_service.synthesize_batch_summary",
        return_value="Synthesized cross-screen summary of the workflow.",
    ):
        response = client.post("/api/analyze-batch", files=files, data=data)

    assert response.status_code == 200
    res = response.json()
    assert res["total_images"] == 2
    assert res["successful_count"] == 2
    assert res["failed_count"] == 0
    assert len(res["results"]) == 2
    assert res["results"][0]["success"] is True
    assert res["results"][0]["filename"] == "screen1.png"
    assert res["results"][1]["success"] is True
    assert res["results"][1]["filename"] == "screen2.jpg"
    assert res["combined_summary"] == "Synthesized cross-screen summary of the workflow."
    assert "batch_id" in res


def test_batch_analyze_exceeds_max_image_count():
    # Attempt to upload more than MAX_BATCH_IMAGES
    files = [
        ("images", (f"screen_{i}.png", create_test_image_bytes(), "image/png"))
        for i in range(settings.MAX_BATCH_IMAGES + 1)
    ]
    data = {"question": "What is here?"}

    response = client.post("/api/analyze-batch", files=files, data=data)
    assert response.status_code == 400
    assert "exceeds maximum limit" in response.json()["detail"]


def test_batch_analyze_missing_question():
    files = [("images", ("screen.png", create_test_image_bytes(), "image/png"))]
    data = {"question": "   "}

    response = client.post("/api/analyze-batch", files=files, data=data)
    assert response.status_code == 400
    assert "question about the screenshots is required" in response.json()["detail"].lower()


def test_batch_analyze_exceeds_total_size():
    # Simulate a payload that exceeds MAX_BATCH_TOTAL_SIZE_BYTES
    with patch.object(settings, "MAX_BATCH_TOTAL_SIZE_BYTES", 500):
        img = create_test_image_bytes("PNG")
        files = [
            ("images", ("screen1.png", img, "image/png")),
            ("images", ("screen2.png", img, "image/png")),
        ]
        response = client.post("/api/analyze-batch", files=files, data={"question": "Test?"})
        assert response.status_code == 413
        assert "exceeds maximum allowed limit" in response.json()["detail"]


def test_batch_analyze_partial_failure(mock_gemini_analysis):
    valid_img = create_test_image_bytes("PNG")
    corrupt_bytes = b"not_a_valid_image_file_content"

    files = [
        ("images", ("valid.png", valid_img, "image/png")),
        ("images", ("corrupt.png", corrupt_bytes, "image/png")),
    ]
    data = {"question": "Describe screens", "generate_summary": "true"}

    with patch(
        "backend.app.services.google_gemini.google_service.analyze_screenshot",
        return_value=mock_gemini_analysis,
    ), patch(
        "backend.app.services.google_gemini.google_service.synthesize_batch_summary",
        return_value="Summary of the 1 valid screen.",
    ):
        response = client.post("/api/analyze-batch", files=files, data=data)

    assert response.status_code == 200
    res = response.json()
    assert res["total_images"] == 2
    assert res["successful_count"] == 1
    assert res["failed_count"] == 1

    valid_res = next(r for r in res["results"] if r["filename"] == "valid.png")
    assert valid_res["success"] is True
    assert valid_res["analysis"] is not None

    corrupt_res = next(r for r in res["results"] if r["filename"] == "corrupt.png")
    assert corrupt_res["success"] is False
    assert corrupt_res["error"] is not None


def test_batch_session_cleanup(mock_gemini_analysis):
    img = create_test_image_bytes("PNG")
    files = [("images", ("screen.png", img, "image/png"))]

    with patch(
        "backend.app.services.google_gemini.google_service.analyze_screenshot",
        return_value=mock_gemini_analysis,
    ):
        res = client.post("/api/analyze-batch", files=files, data={"question": "Test?"})

    assert res.status_code == 200
    batch_id = res.json()["batch_id"]

    # Delete batch session
    del_res = client.delete(f"/api/batch-session/{batch_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["batch_id"] == batch_id
    assert del_data["cleared"] is True
    assert del_data["cleared_count"] == 1
