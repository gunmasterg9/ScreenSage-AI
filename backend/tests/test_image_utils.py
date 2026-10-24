"""Tests for image validation, sanitization, and decompression protection."""

import io
import pytest
from PIL import Image
from fastapi import HTTPException
from backend.app.image_utils import validate_and_process_image
from backend.app.config import settings


def create_test_image(format: str = "PNG", size: tuple = (200, 200), color: str = "blue") -> bytes:
    """Helper to generate in-memory test image bytes."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def test_valid_png_image():
    raw_bytes = create_test_image(format="PNG", size=(300, 150))
    b64, meta = validate_and_process_image(raw_bytes, "image/png")
    assert isinstance(b64, str)
    assert len(b64) > 0
    assert meta["width"] == 300
    assert meta["height"] == 150
    assert meta["format"] == "PNG"


def test_valid_jpeg_image():
    raw_bytes = create_test_image(format="JPEG", size=(400, 300))
    b64, meta = validate_and_process_image(raw_bytes, "image/jpeg")
    assert isinstance(b64, str)
    assert meta["width"] == 400
    assert meta["height"] == 300
    assert meta["format"] == "JPEG"


def test_valid_webp_image():
    raw_bytes = create_test_image(format="WEBP", size=(250, 250))
    b64, meta = validate_and_process_image(raw_bytes, "image/webp")
    assert isinstance(b64, str)
    assert meta["format"] == "WEBP"


def test_empty_image_rejection():
    with pytest.raises(HTTPException) as exc_info:
        validate_and_process_image(b"", "image/png")
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail.lower()


def test_file_size_limit_rejection():
    # Exceed maximum size
    oversized = b"x" * (settings.MAX_UPLOAD_SIZE_BYTES + 1024)
    with pytest.raises(HTTPException) as exc_info:
        validate_and_process_image(oversized, "image/png")
    assert exc_info.value.status_code == 413
    assert "exceeds" in exc_info.value.detail.lower()


def test_invalid_format_rejection():
    # GIF or plain text is rejected
    raw_bytes = create_test_image(format="GIF", size=(100, 100))
    with pytest.raises(HTTPException) as exc_info:
        validate_and_process_image(raw_bytes, "image/gif")
    assert exc_info.value.status_code == 415
    assert "unsupported" in exc_info.value.detail.lower()


def test_corrupted_image_rejection():
    corrupted_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRcorruptedcontent"
    with pytest.raises(HTTPException) as exc_info:
        validate_and_process_image(corrupted_bytes, "image/png")
    assert exc_info.value.status_code == 400


def test_oversized_dimensions_auto_scaled():
    # If image exceeds MAX_IMAGE_DIMENSION, it is safely scaled down
    large_img = Image.new("RGB", (5000, 2500), color="green")
    buf = io.BytesIO()
    large_img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    b64, meta = validate_and_process_image(raw_bytes, "image/png")
    assert meta["width"] <= settings.MAX_IMAGE_DIMENSION
    assert meta["height"] <= settings.MAX_IMAGE_DIMENSION
