"""Image validation, sanitization, and processing utilities."""

import io
import base64
from PIL import Image, ImageOps
from fastapi import HTTPException, UploadFile
from backend.app.config import settings

# Enforce strict decompression bomb protection
Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS


def validate_and_process_image(
    file_bytes: bytes,
    content_type: str = "image/png"
) -> tuple[str, dict]:
    """
    Validates uploaded image bytes, checks size, format, prevents decompression bombs,
    strips EXIF metadata, and returns (base64_encoded_image, metadata_dict).
    """
    # 1. Size check
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Image size exceeds maximum allowed limit of {max_mb} MB."
        )

    # 2. Open with Pillow safely
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.verify()  # Verifies integrity without decoding entire raster yet
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Malformed or corrupted image file: {str(e)}"
        )

    # Re-open for actual processing (verify() closes or exhausts the stream)
    try:
        image = Image.open(io.BytesIO(file_bytes))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot decode image: {str(e)}"
        )

    # 3. Format validation
    detected_format = (image.format or "").upper()
    if detected_format not in settings.ALLOWED_IMAGE_FORMATS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image format '{detected_format}'. Allowed formats are: {', '.join(settings.ALLOWED_IMAGE_FORMATS)}."
        )

    # 4. Dimension checks
    width, height = image.size
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=400, detail="Invalid image dimensions.")

    if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
        # Resize while keeping aspect ratio if oversized
        image.thumbnail((settings.MAX_IMAGE_DIMENSION, settings.MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
        width, height = image.size

    # 5. Orientation fix & EXIF stripping (privacy requirement)
    try:
        image = ImageOps.exif_transpose(image)
        width, height = image.size
    except Exception:
        pass

    # Convert to RGB (or RGBA if transparent PNG/WEBP)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    # 6. Save sanitized image to in-memory buffer without original EXIF
    output_buffer = io.BytesIO()
    save_format = "PNG" if detected_format == "PNG" else ("WEBP" if detected_format == "WEBP" else "JPEG")
    if save_format == "JPEG" and image.mode == "RGBA":
        image = image.convert("RGB")

    image.save(output_buffer, format=save_format, quality=90)
    sanitized_bytes = output_buffer.getvalue()

    # 7. Base64 encode for Ollama API
    b64_string = base64.b64encode(sanitized_bytes).decode("utf-8")

    metadata = {
        "width": width,
        "height": height,
        "format": save_format,
        "size_bytes": len(sanitized_bytes),
    }

    return b64_string, metadata
