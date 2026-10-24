"""Dedicated Google Gemini / Gemma 4 AI Service.
Integrates with Google Gen AI SDK (google-genai).
"""

import asyncio
import base64
import io
import json
import logging
import os
import re
import time
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image
from fastapi import HTTPException, status
from google import genai
from google.genai import errors

from backend.app.config import settings
from backend.app.schemas import (
    ScreenExplanation,
    BoundingBox,
    UIElement,
    FollowUpResponse,
)

logger = logging.getLogger("screensage.google_gemini")

SYSTEM_PROMPT_BASE = """You are ScreenSage AI, an expert vision-grounded assistant designed to explain screenshots of websites, desktop software, settings, dialogs, and error messages.
Product Tagline: "Understand any screen. Take the next step."

Core Principles:
1. Grounding First: Base your explanation STRICTLY on what is visibly present in the screenshot.
2. No Hallucinations: DO NOT invent buttons, settings, menu items, or error causes that cannot be visually confirmed in the image.
3. Explicit Missing Information: If an element, setting, or requested feature is not visible in the screenshot, explicitly state that it is not visible under 'uncertainties_and_missing_visual_information'.
4. Coordinate Verification: If you provide bounding boxes for visible UI elements, provide normalized percentages (0.0 to 100.0) where ymin is top, xmin is left, ymax is bottom, xmax is right. ONLY provide coordinates when confident of the element's visual location. If unsure, set "bounding_box": null.
5. Structured JSON Output: You must respond ONLY with a valid JSON object matching the requested schema. Do not include markdown or text outside the JSON.
"""

LANGUAGE_INSTRUCTIONS = {
    "en": "Provide all text explanations and answers in English.",
    "hi": "Provide all explanations, descriptions, and answers in Hindi (हिन्दी). Ensure technical terms are clearly explained.",
    "gu": "Provide all explanations, descriptions, and answers in Gujarati (ગુજરાતી). Ensure technical terms are clearly explained.",
}

ANALYSIS_PROMPT_TEMPLATE = """Please analyze this screenshot and answer the user's question: "{question}"

{language_instruction}

Analyze the screenshot carefully and output a JSON object with this exact structure:
{{
  "screen_summary": "A 1-2 sentence plain language summary of what application or website this screen shows and its general state.",
  "visible_ui_elements": [
    {{
      "element_name": "Name or title of key element",
      "element_type": "button | input | modal | menu | text | error_banner | tab | icon | table | sidebar",
      "likely_purpose": "Grounded explanation of what this element does or signifies based on visual layout",
      "visible_text": "Exact text visible on or beside this element",
      "bounding_box": {{
        "ymin": 0.0,
        "xmin": 0.0,
        "ymax": 100.0,
        "xmax": 100.0
      }}
    }}
  ],
  "likely_purpose_of_important_elements": [
    "Key takeaway 1 explaining a primary component's role",
    "Key takeaway 2 explaining another primary component's role"
  ],
  "relevant_visible_text": [
    "Important snippet 1",
    "Important snippet 2"
  ],
  "answer_to_user_question": "Direct, evidence-grounded answer to the user's specific question based only on what is visible.",
  "suggested_next_steps": [
    "First concrete, actionable step the user should take",
    "Second optional follow-up step"
  ],
  "uncertainties_and_missing_visual_information": [
    "Any requested items that could not be seen or confirmed in the screenshot"
  ]
}}
"""

FOLLOW_UP_PROMPT_TEMPLATE = """You are answering a follow-up question about the screenshot you previously analyzed.

Context from previous analysis:
- Screen Summary: {summary}
- Original Question: {original_question}
- Original Answer: {original_answer}

Follow-up Question: "{follow_up_question}"

{language_instruction}

Ground your follow-up answer strictly in the visible contents of the screenshot. If the answer cannot be determined from the image, explicitly state so.

Respond with a JSON object in this exact format:
{{
  "answer": "Direct, clear answer to the follow-up question grounded in the screenshot.",
  "suggested_next_steps": [
    "Relevant next step based on the follow-up answer"
  ],
  "visible_ui_elements": [],
  "uncertainties_and_missing_visual_information": []
}}
"""


class GoogleGeminiService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GOOGLE_API_KEY
        self.model = model or settings.GOOGLE_GEMINI_MODEL
        self.timeout = timeout or settings.INFERENCE_TIMEOUT_SECONDS
        self._client: Optional[genai.Client] = None

    @property
    def current_api_key(self) -> str:
        key = self.api_key if self.api_key is not None else (settings.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY", ""))
        return (key or "").strip()

    def is_configured(self) -> bool:
        """Check if Google API key is configured."""
        key = self.current_api_key
        return bool(key and len(key) > 5)

    def get_client(self) -> genai.Client:
        """Lazy-initialize and return the Google Gen AI client."""
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google API key is not configured. Please set GOOGLE_API_KEY in the backend .env file.",
            )
        return genai.Client(api_key=self.current_api_key)

    def clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Robust extraction and parsing of JSON from model generation."""
        text = raw_text.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            candidate = fence_match.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            sub = text[first_brace : last_brace + 1]
            try:
                return json.loads(sub)
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse valid JSON from model response: {text[:200]}")

    def sanitize_coordinates(self, elements_data: List[Dict[str, Any]]) -> Tuple[List[UIElement], bool]:
        """
        Validate and normalize bounding box coordinates.
        Never claim precise localization unless coordinates are valid and reasonable.
        """
        verified_any = False
        ui_elements: List[UIElement] = []

        for idx, item in enumerate(elements_data):
            elem_name = str(item.get("element_name", f"Element {idx + 1}"))
            elem_type = str(item.get("element_type", "element"))
            likely_purpose = str(item.get("likely_purpose", ""))
            visible_text = item.get("visible_text")
            box_data = item.get("bounding_box")

            bounding_box: Optional[BoundingBox] = None
            if isinstance(box_data, dict):
                try:
                    ymin = float(box_data.get("ymin", -1))
                    xmin = float(box_data.get("xmin", -1))
                    ymax = float(box_data.get("ymax", -1))
                    xmax = float(box_data.get("xmax", -1))

                    # Normalized 0.0 - 1.0 scales to 0.0 - 100.0%
                    if 0.0 <= ymin <= 1.0 and 0.0 <= xmin <= 1.0 and 0.0 <= ymax <= 1.0 and 0.0 <= xmax <= 1.0:
                        ymin *= 100.0
                        xmin *= 100.0
                        ymax *= 100.0
                        xmax *= 100.0
                    elif ymax > 100.0 or xmax > 100.0:
                        ymin = (ymin / 1000.0) * 100.0
                        xmin = (xmin / 1000.0) * 100.0
                        ymax = (ymax / 1000.0) * 100.0
                        xmax = (xmax / 1000.0) * 100.0

                    if 0.0 <= ymin <= 100.0 and 0.0 <= xmin <= 100.0 and 0.0 <= ymax <= 100.0 and 0.0 <= xmax <= 100.0:
                        if (ymax - ymin > 0.5) and (xmax - xmin > 0.5) and not (ymin == 0 and xmin == 0 and ymax == 100 and xmax == 100):
                            bounding_box = BoundingBox(
                                ymin=round(ymin, 2),
                                xmin=round(xmin, 2),
                                ymax=round(ymax, 2),
                                xmax=round(xmax, 2),
                                label=elem_name,
                            )
                            verified_any = True
                except (ValueError, TypeError):
                    bounding_box = None

            ui_elements.append(
                UIElement(
                    id=f"elem_{idx + 1}",
                    element_name=elem_name,
                    element_type=elem_type,
                    likely_purpose=likely_purpose,
                    visible_text=visible_text,
                    bounding_box=bounding_box,
                )
            )

        return ui_elements, verified_any

    def _convert_b64_to_pil(self, image_b64: str) -> Image.Image:
        """Safely convert base64 image data to PIL Image."""
        try:
            raw_data = base64.b64decode(image_b64)
            img = Image.open(io.BytesIO(raw_data))
            img.load()
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            return img
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image data provided: {str(e)}",
            )

    async def generate_text(self, prompt: str) -> Tuple[str, str, float]:
        """
        Text-only query against configured Google Gemini / Gemma 4 model.
        Used for verification and text-based reasoning.
        """
        client = self.get_client()
        start_time = time.perf_counter()

        logger.info("Google Gen AI text request dispatched: model=%s", self.model)

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                ),
            )
        except errors.APIError as e:
            logger.error("Google Gen AI APIError: %s (code: %s)", e.message, e.code)
            if e.code == 400:
                raise HTTPException(status_code=400, detail=f"Google API request error: {e.message}")
            elif e.code in (401, 403):
                raise HTTPException(status_code=401, detail="Google API authentication failed. Please verify GOOGLE_API_KEY.")
            elif e.code == 429:
                raise HTTPException(status_code=429, detail="Google API quota exceeded. Please wait a moment before trying again.")
            elif e.code == 503:
                raise HTTPException(status_code=503, detail="Google AI model is currently experiencing high demand. Please retry shortly.")
            raise HTTPException(status_code=502, detail=f"Google API error ({e.code}): {e.message}")
        except Exception as e:
            logger.error("Unexpected error contacting Google API: %s: %s", type(e).__name__, str(e))
            raise HTTPException(status_code=500, detail=f"Error contacting Google API: {type(e).__name__}")

        duration = round(time.perf_counter() - start_time, 2)
        answer = (response.text or "").strip()
        logger.info("Google Gen AI text response received: duration=%.2fs", duration)
        return answer, self.model, duration

    async def analyze_screenshot(
        self,
        image_b64: str,
        question: str,
        language: str = "en",
        mime_type: str = "image/png",
    ) -> Tuple[ScreenExplanation, str, float]:
        """
        Multimodal screenshot analysis using official Google Gen AI SDK.
        Passes PIL Image directly to client.models.generate_content.
        """
        client = self.get_client()
        pil_img = self._convert_b64_to_pil(image_b64)

        lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
        user_prompt = f"{SYSTEM_PROMPT_BASE}\n\n" + ANALYSIS_PROMPT_TEMPLATE.format(
            question=question,
            language_instruction=lang_instruction,
        )

        start_time = time.perf_counter()
        logger.info("Google Gen AI multimodal request dispatched: model=%s, language=%s", self.model, language)

        max_retries = 1
        response = None

        for attempt in range(max_retries + 1):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model,
                        contents=[user_prompt, pil_img],
                    ),
                )
                break
            except errors.APIError as e:
                logger.warning("Google Gen AI APIError on attempt %d: code=%s, msg=%s", attempt + 1, e.code, e.message)
                if e.code == 503 and attempt < max_retries:
                    logger.info("Retrying after 2.0s high-demand backoff...")
                    await asyncio.sleep(2.0)
                    continue
                if e.code in (401, 403):
                    raise HTTPException(status_code=401, detail="Google API authentication failed. Please verify GOOGLE_API_KEY.")
                elif e.code == 429:
                    raise HTTPException(status_code=429, detail="Google API quota exceeded. Please wait a moment before trying again.")
                elif e.code == 503:
                    raise HTTPException(status_code=503, detail="Google AI model is experiencing high demand. Please try again shortly.")
                raise HTTPException(status_code=502, detail=f"Google API error ({e.code}): {e.message}")
            except Exception as e:
                logger.error("Unexpected error contacting Google API: %s: %s", type(e).__name__, str(e))
                raise HTTPException(status_code=500, detail=f"Error contacting Google API: {type(e).__name__}")

        duration = round(time.perf_counter() - start_time, 2)
        content = (response.text or "").strip() if response else ""

        if not content:
            raise HTTPException(status_code=502, detail="No content returned by Google AI model.")

        try:
            parsed_json = self.clean_and_parse_json(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not parse model output into structured explanation: {str(e)}",
            )

        raw_elements = parsed_json.get("visible_ui_elements", [])
        ui_elements, coordinate_support_verified = self.sanitize_coordinates(raw_elements)

        try:
            explanation = ScreenExplanation(
                screen_summary=parsed_json.get("screen_summary", "Screenshot analysis completed."),
                visible_ui_elements=ui_elements,
                likely_purpose_of_important_elements=parsed_json.get("likely_purpose_of_important_elements", []),
                relevant_visible_text=parsed_json.get("relevant_visible_text", []),
                answer_to_user_question=parsed_json.get("answer_to_user_question", ""),
                suggested_next_steps=parsed_json.get("suggested_next_steps", []),
                uncertainties_and_missing_visual_information=parsed_json.get(
                    "uncertainties_and_missing_visual_information", []
                ),
                coordinate_support_verified=coordinate_support_verified,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Schema validation error on model output: {str(e)}",
            )

        logger.info("Google Gen AI multimodal analysis completed: duration=%.2fs", duration)
        return explanation, self.model, duration

    async def follow_up_chat(
        self,
        image_b64: str,
        question: str,
        summary: str,
        original_question: str,
        original_answer: str,
        language: str = "en",
        mime_type: str = "image/png",
    ) -> Tuple[FollowUpResponse, str, float]:
        """
        Follow-up visual question grounded in the active session screenshot.
        """
        client = self.get_client()
        pil_img = self._convert_b64_to_pil(image_b64)

        lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
        user_prompt = f"{SYSTEM_PROMPT_BASE}\n\n" + FOLLOW_UP_PROMPT_TEMPLATE.format(
            summary=summary,
            original_question=original_question,
            original_answer=original_answer,
            follow_up_question=question,
            language_instruction=lang_instruction,
        )

        start_time = time.perf_counter()
        logger.info("Google Gen AI follow-up request dispatched: model=%s", self.model)

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=self.model,
                    contents=[user_prompt, pil_img],
                ),
            )
        except errors.APIError as e:
            if e.code in (401, 403):
                raise HTTPException(status_code=401, detail="Google API authentication failed.")
            elif e.code == 429:
                raise HTTPException(status_code=429, detail="Google API rate limit reached.")
            elif e.code == 503:
                raise HTTPException(status_code=503, detail="Google AI model is experiencing high demand.")
            raise HTTPException(status_code=502, detail=f"Google API error: {e.message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error contacting Google API: {str(e)}")

        duration = round(time.perf_counter() - start_time, 2)
        content = (response.text or "").strip()

        try:
            parsed = self.clean_and_parse_json(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not parse follow-up JSON: {str(e)}",
            )

        elements_raw = parsed.get("referenced_elements", parsed.get("visible_ui_elements", []))
        ui_elements, _ = self.sanitize_coordinates(elements_raw)

        return (
            FollowUpResponse(
                session_id="",
                question=question,
                answer=parsed.get("answer", "No response generated."),
                suggested_next_steps=parsed.get("suggested_next_steps", []),
                visible_evidence=parsed.get("visible_evidence", []),
                uncertainties=parsed.get(
                    "uncertainties",
                    parsed.get("uncertainties_and_missing_visual_information", []),
                ),
                referenced_elements=ui_elements,
                model_tag=self.model,
                inference_duration_seconds=duration,
            ),
            self.model,
            duration,
        )


# Global singleton instance
google_service = GoogleGeminiService()
