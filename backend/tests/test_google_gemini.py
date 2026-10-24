"""Tests for Google Gemini / Gemma 4 service."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from google.genai import errors
from backend.app.services.google_gemini import GoogleGeminiService


@pytest.fixture
def service():
    return GoogleGeminiService(
        api_key="fake-google-api-key-12345",
        model="gemma-4-31b-it",
        timeout=10.0,
    )


def test_missing_api_key():
    unconfigured = GoogleGeminiService(api_key="")
    assert unconfigured.is_configured() is False
    with pytest.raises(HTTPException) as exc_info:
        unconfigured.get_client()
    assert exc_info.value.status_code == 503


def test_configured_api_key():
    s = GoogleGeminiService(api_key="test-key-123456")
    assert s.is_configured() is True


@pytest.mark.asyncio
async def test_text_generation_success(service):
    mock_resp = MagicMock()
    mock_resp.text = "391"

    with patch.object(service, "get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        answer, model, duration = await service.generate_text("What is 17 * 23?")
        assert answer == "391"
        assert model == "gemma-4-31b-it"
        assert duration >= 0.0


@pytest.mark.asyncio
async def test_multimodal_screenshot_analysis_success(service):
    mock_content = """{
        "screen_summary": "A software dashboard with an error banner.",
        "visible_ui_elements": [
            {
                "element_name": "Error Banner",
                "element_type": "error_banner",
                "likely_purpose": "Alerts user of connectivity failure",
                "visible_text": "Error 503: Service Unavailable",
                "bounding_box": {"ymin": 10.0, "xmin": 5.0, "ymax": 20.0, "xmax": 95.0}
            }
        ],
        "likely_purpose_of_important_elements": ["Informs user of server outage"],
        "relevant_visible_text": ["Error 503: Service Unavailable"],
        "answer_to_user_question": "The error indicates the upstream server is down.",
        "suggested_next_steps": ["Retry in a few minutes"],
        "uncertainties_and_missing_visual_information": []
    }"""

    mock_resp = MagicMock()
    mock_resp.text = mock_content

    # 1x1 png in base64
    sample_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    with patch.object(service, "get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        explanation, model, duration = await service.analyze_screenshot(
            image_b64=sample_b64,
            question="What does this error mean?",
            language="en",
        )
        assert explanation.screen_summary == "A software dashboard with an error banner."
        assert len(explanation.visible_ui_elements) == 1
        assert explanation.visible_ui_elements[0].element_name == "Error Banner"
        assert explanation.coordinate_support_verified is True
        assert model == "gemma-4-31b-it"


@pytest.mark.asyncio
async def test_multimodal_malformed_json_response(service):
    mock_resp = MagicMock()
    mock_resp.text = "This is definitely not JSON"
    sample_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    with patch.object(service, "get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_screenshot(
                image_b64=sample_b64,
                question="What is this?",
            )
        assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_google_api_401_error(service):
    err = errors.APIError(401, {"error": {"message": "API_KEY_INVALID"}})

    with patch.object(service, "get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = err
        mock_get_client.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_text("Hi")
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_google_api_429_quota_error(service):
    err = errors.APIError(429, {"error": {"message": "RESOURCE_EXHAUSTED"}})

    with patch.object(service, "get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = err
        mock_get_client.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_text("Hi")
        assert exc_info.value.status_code == 429
