"""Pydantic data models and schemas for ScreenSage AI."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0 to 100 percentage scale for responsive overlays)."""
    ymin: float = Field(..., ge=0.0, le=100.0, description="Top edge percentage (0-100)")
    xmin: float = Field(..., ge=0.0, le=100.0, description="Left edge percentage (0-100)")
    ymax: float = Field(..., ge=0.0, le=100.0, description="Bottom edge percentage (0-100)")
    xmax: float = Field(..., ge=0.0, le=100.0, description="Right edge percentage (0-100)")
    label: Optional[str] = Field(None, description="Label for region overlay")

    @field_validator("ymax")
    @classmethod
    def check_y_order(cls, v: float, info) -> float:
        ymin = info.data.get("ymin", 0.0)
        if v < ymin:
            return max(ymin, v)
        return v

    @field_validator("xmax")
    @classmethod
    def check_x_order(cls, v: float, info) -> float:
        xmin = info.data.get("xmin", 0.0)
        if v < xmin:
            return max(xmin, v)
        return v


class UIElement(BaseModel):
    """Represents a visible UI component discovered on the screenshot."""
    id: Optional[str] = Field(None, description="Identifier for referencing in explanation cards")
    element_name: str = Field(..., description="Name or descriptive label of the UI element")
    element_type: str = Field(..., description="Type of element (button, input, modal, text, icon, menu, etc.)")
    likely_purpose: str = Field(..., description="Likely purpose or function based strictly on visible context")
    visible_text: Optional[str] = Field(None, description="Exact visible text on or near this element")
    bounding_box: Optional[BoundingBox] = Field(None, description="Verified bounding box coordinates if available")


class ScreenExplanation(BaseModel):
    """Structured explanation returned from Gemma 4 analysis."""
    screen_summary: str = Field(
        ...,
        description="Concise, plain-language summary of what the screen represents"
    )
    visible_ui_elements: List[UIElement] = Field(
        default_factory=list,
        description="Catalog of key visible UI elements and their roles"
    )
    likely_purpose_of_important_elements: List[str] = Field(
        default_factory=list,
        description="Key takeaways regarding the primary purpose of important screen elements"
    )
    relevant_visible_text: List[str] = Field(
        default_factory=list,
        description="Extracted or referenced visible text (e.g. error messages, headers, buttons)"
    )
    answer_to_user_question: str = Field(
        ...,
        description="Direct, grounded answer addressing the user's specific inquiry"
    )
    suggested_next_steps: List[str] = Field(
        default_factory=list,
        description="Recommended next actions or troubleshooting steps grounded in visible evidence"
    )
    uncertainties_and_missing_visual_information: List[str] = Field(
        default_factory=list,
        description="Explicit notice of elements not visible, obscured context, or unverified assumptions"
    )
    coordinate_support_verified: bool = Field(
        False,
        description="True only if image region coordinates are verified and supported by model output"
    )


class ImageMetadata(BaseModel):
    width: int
    height: int
    format: str
    size_bytes: int


class AnalysisResponse(BaseModel):
    session_id: str
    question: str
    language: str = "en"
    explanation: ScreenExplanation
    model_tag: str
    inference_duration_seconds: float
    timestamp: str
    image_metadata: ImageMetadata


class FollowUpRequest(BaseModel):
    session_id: str
    question: str = Field(..., min_length=1, max_length=1000)
    language: Optional[str] = "en"


class FollowUpResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    suggested_next_steps: List[str] = Field(default_factory=list)
    visible_evidence: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    referenced_elements: List[UIElement] = Field(default_factory=list)
    model_tag: str
    inference_duration_seconds: float


class AIStatusResponse(BaseModel):
    configured: bool
    model: str
    provider: str = "NVIDIA"
    has_key: bool
    tagline: str
    endpoint: str


class HealthResponse(BaseModel):
    status: str
    nvidia_configured: bool
    model: str
    tagline: str
    message: str


class TextPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)


class TextPromptResponse(BaseModel):
    answer: str
    model: str
    duration_seconds: float
