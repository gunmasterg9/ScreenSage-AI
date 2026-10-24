"""Tests for NVIDIA Gemma 4 service."""

import pytest
from unittest.mock import patch
from fastapi import HTTPException
import httpx
from backend.app.services.nvidia_gemma import NvidiaGemmaService


@pytest.fixture
def service():
    return NvidiaGemmaService(
        api_key="nvapi-test-fake-key-12345",
        model="google/gemma-4-31b-it",
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=10.0,
    )


def test_missing_api_key():
    unconfigured_service = NvidiaGemmaService(api_key="")
    assert unconfigured_service.is_configured() is False
    with pytest.raises(HTTPException) as exc_info:
        unconfigured_service._get_headers()
    assert exc_info.value.status_code == 503
    assert "not configured" in exc_info.value.detail.lower()


def test_configured_api_key():
    s = NvidiaGemmaService(api_key="nvapi-12345678")
    assert s.is_configured() is True
    headers = s._get_headers()
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer nvapi-12345678"


@pytest.mark.asyncio
async def test_authentication_failure_401(service):
    mock_resp = httpx.Response(401, json={"detail": "Unauthorized"})
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_text("Hello")
        assert exc_info.value.status_code == 401
        assert "authentication failed" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_rate_limit_429(service):
    mock_resp = httpx.Response(429, json={"detail": "Rate limit exceeded"})
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_text("Hello")
        assert exc_info.value.status_code == 429
        assert "rate limit" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_server_error_500(service):
    mock_resp = httpx.Response(500, text="Internal Server Error")
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_text("Hello")
        assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_timeout_504(service):
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_text("Hello")
        assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_text_only_successful_response(service):
    mock_resp = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": "391"
                    }
                }
            ]
        },
    )
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        answer, model, duration = await service.generate_text("What is 17 * 23?")
        assert answer == "391"
        assert model == "google/gemma-4-31b-it"
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

    mock_resp = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": mock_content
                    }
                }
            ]
        },
    )

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        explanation, model, duration = await service.analyze_screenshot(
            image_b64="fakeimagebytes",
            question="What does this error mean?",
            language="en",
        )
        assert explanation.screen_summary == "A software dashboard with an error banner."
        assert len(explanation.visible_ui_elements) == 1
        assert explanation.visible_ui_elements[0].element_name == "Error Banner"
        assert explanation.coordinate_support_verified is True
        assert model == "google/gemma-4-31b-it"


@pytest.mark.asyncio
async def test_multimodal_malformed_json_response(service):
    mock_resp = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": "Not JSON at all"
                    }
                }
            ]
        },
    )

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_screenshot(
                image_b64="fakebytes",
                question="What is this?",
            )
        assert exc_info.value.status_code == 422
