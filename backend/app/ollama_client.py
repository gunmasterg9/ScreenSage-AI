"""Client for local Ollama integration and vision-capable Gemma 4 inference."""

import json
import re
import time
from typing import List, Tuple, Optional, Dict, Any
import httpx
from fastapi import HTTPException
from backend.app.config import settings
from backend.app.schemas import (
    ScreenExplanation,
    FollowUpResponse,
    ModelInfo,
    BoundingBox,
    UIElement,
)
from backend.app.prompts import (
    SYSTEM_PROMPT,
    ANALYSIS_USER_PROMPT_TEMPLATE,
    FOLLOW_UP_USER_PROMPT_TEMPLATE,
)

# Known vision-capable families and keywords in Ollama
KNOWN_VISION_PATTERNS = [
    "gemma4",
    "gemma3:4b",
    "gemma3:12b",
    "gemma3:27b",
    "llama3.2-vision",
    "llava",
    "bakllava",
    "moondream",
    "qwen2-vl",
    "minicpm-v",
    "paligemma",
]


class OllamaClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    async def get_ollama_status(self) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
        """
        Check if Ollama is running and retrieve installed models.
        Returns (is_running, version, model_list).
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 1. Fetch tags / models
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])

                    # Try to fetch version if available
                    version = None
                    try:
                        v_resp = await client.get(f"{self.base_url}/api/version")
                        if v_resp.status_code == 200:
                            version = v_resp.json().get("version")
                    except Exception:
                        pass

                    return True, version, models
        except Exception:
            return False, None, []
        return False, None, []

    def is_vision_capable_model(self, model_name: str, model_details: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a model name or its details indicate image-input / vision support."""
        name_lower = model_name.lower()
        for pattern in KNOWN_VISION_PATTERNS:
            if pattern in name_lower:
                return True

        if model_details:
            families = model_details.get("families", [])
            for f in families:
                if "clip" in f.lower() or "vision" in f.lower():
                    return True
            runner = model_details.get("runner", "")
            if "vision" in runner.lower():
                return True

        return False

    async def get_available_models(self) -> List[ModelInfo]:
        """List all installed models in Ollama with vision capability flags."""
        is_running, _, raw_models = await self.get_ollama_status()
        if not is_running:
            return []

        models: List[ModelInfo] = []
        for m in raw_models:
            name = m.get("name", "")
            details = m.get("details", {})
            is_vision = self.is_vision_capable_model(name, details)
            models.append(
                ModelInfo(
                    name=name,
                    size=m.get("size"),
                    modified_at=m.get("modified_at"),
                    is_vision_capable=is_vision,
                    is_default=(name == settings.DEFAULT_MODEL_TAG),
                    status="installed",
                )
            )
        return models

    async def verify_model(self, model_tag: str) -> Tuple[bool, bool, str]:
        """
        Verify that the requested model is installed and vision-capable.
        Never silently substitutes another model.
        Returns (is_installed, is_vision_capable, helpful_message).
        """
        is_running, _, raw_models = await self.get_ollama_status()
        if not is_running:
            return (
                False,
                False,
                f"Ollama service is not reachable at {self.base_url}. Please ensure Ollama is running (`ollama serve`).",
            )

        installed_names = [m.get("name", "") for m in raw_models]
        # Match exact name or without ':latest' tag
        matched_model = None
        for m in raw_models:
            name = m.get("name", "")
            if name == model_tag or name == f"{model_tag}:latest" or (model_tag.endswith(":latest") and name == model_tag[:-7]):
                matched_model = m
                break

        if not matched_model:
            return (
                False,
                False,
                f"Model '{model_tag}' is not installed in local Ollama. "
                f"Run `ollama pull {model_tag}` to install it. "
                f"Available models: {', '.join(installed_names) if installed_names else 'None'}.",
            )

        details = matched_model.get("details", {})
        is_vision = self.is_vision_capable_model(matched_model.get("name", model_tag), details)

        if not is_vision:
            return (
                True,
                False,
                f"Model '{model_tag}' is installed, but it does not support image/vision input. "
                f"ScreenSage AI requires a vision-capable model such as 'gemma4:e2b' or 'gemma4:e4b'.",
            )

        return True, True, "Model is installed and vision-ready."

    def clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Robust extraction and parsing of JSON from model generation."""
        text = raw_text.strip()
        # Handle markdown fences ```json ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            candidate = fence_match.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # Try raw text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try finding outer JSON object brackets {...}
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

                    # Check if coordinates were normalized to 0-1 instead of 0-100
                    if 0.0 <= ymin <= 1.0 and 0.0 <= xmin <= 1.0 and 0.0 <= ymax <= 1.0 and 0.0 <= xmax <= 1.0:
                        ymin *= 100.0
                        xmin *= 100.0
                        ymax *= 100.0
                        xmax *= 100.0

                    # Check if coordinates were normalized to 0-1000 instead of 0-100
                    elif ymax > 100.0 or xmax > 100.0:
                        ymin = (ymin / 1000.0) * 100.0
                        xmin = (xmin / 1000.0) * 100.0
                        ymax = (ymax / 1000.0) * 100.0
                        xmax = (xmax / 1000.0) * 100.0

                    # Coordinate bounds validation
                    if 0.0 <= ymin <= 100.0 and 0.0 <= xmin <= 100.0 and 0.0 <= ymax <= 100.0 and 0.0 <= xmax <= 100.0:
                        # Ensure reasonable size (not a 0-area point or full 100% canvas)
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

    async def analyze_screenshot(
        self,
        image_b64: str,
        question: str,
        model_tag: Optional[str] = None
    ) -> Tuple[ScreenExplanation, str, float]:
        """
        Execute vision analysis on the uploaded screenshot with Gemma 4 via Ollama.
        Returns (ScreenExplanation, model_tag, duration_seconds).
        """
        tag = model_tag or settings.DEFAULT_MODEL_TAG

        # 1. Verification
        is_installed, is_vision, message = await self.verify_model(tag)
        if not is_installed:
            raise HTTPException(status_code=404, detail=message)
        if not is_vision:
            raise HTTPException(status_code=422, detail=message)

        # 2. Build payload
        user_prompt = ANALYSIS_USER_PROMPT_TEMPLATE.format(question=question)
        payload = {
            "model": tag,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": user_prompt,
                    "images": [image_b64],
                },
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,  # Low temperature for factual visual grounding
            },
        }

        # 3. Call Ollama API with timing
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.INFERENCE_TIMEOUT_SECONDS) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail=f"Inference timed out after {settings.INFERENCE_TIMEOUT_SECONDS}s. Try a smaller image or lighter model tag.",
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running locally.",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama request error: {str(e)}")

        duration = round(time.perf_counter() - start_time, 2)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Ollama inference failed with code {response.status_code}: {response.text}",
            )

        # 4. Extract generated text
        try:
            res_data = response.json()
            message_content = res_data.get("message", {}).get("content", "")
            if not message_content:
                raise HTTPException(status_code=502, detail="Empty response received from Ollama model.")

            parsed_json = self.clean_and_parse_json(message_content)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Model response could not be parsed into expected schema: {str(e)}",
            )

        # 5. Sanitize and validate bounding boxes
        raw_elements = parsed_json.get("visible_ui_elements", [])
        ui_elements, coordinate_support_verified = self.sanitize_coordinates(raw_elements)

        # 6. Build and validate ScreenExplanation
        try:
            explanation = ScreenExplanation(
                screen_summary=parsed_json.get("screen_summary", "Screenshot analysis completed."),
                visible_ui_elements=ui_elements,
                likely_purpose_of_important_elements=parsed_json.get(
                    "likely_purpose_of_important_elements", []
                ),
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
                status_code=422,
                detail=f"Validation error converting model output to ScreenExplanation: {str(e)}",
            )

        return explanation, tag, duration

    async def follow_up_chat(
        self,
        image_b64: str,
        question: str,
        summary: str,
        original_question: str,
        original_answer: str,
        model_tag: Optional[str] = None
    ) -> Tuple[FollowUpResponse, str, float]:
        """
        Execute follow-up visual question against the active session screenshot.
        """
        tag = model_tag or settings.DEFAULT_MODEL_TAG

        is_installed, is_vision, message = await self.verify_model(tag)
        if not is_installed:
            raise HTTPException(status_code=404, detail=message)
        if not is_vision:
            raise HTTPException(status_code=422, detail=message)

        user_prompt = FOLLOW_UP_USER_PROMPT_TEMPLATE.format(
            summary=summary,
            original_question=original_question,
            original_answer=original_answer,
            follow_up_question=question,
        )

        payload = {
            "model": tag,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": user_prompt,
                    "images": [image_b64],
                },
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.INFERENCE_TIMEOUT_SECONDS) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail=f"Follow-up inference timed out after {settings.INFERENCE_TIMEOUT_SECONDS}s.",
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to Ollama at {self.base_url}.",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama request error: {str(e)}")

        duration = round(time.perf_counter() - start_time, 2)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Ollama inference failed with code {response.status_code}: {response.text}",
            )

        try:
            res_data = response.json()
            message_content = res_data.get("message", {}).get("content", "")
            parsed_json = self.clean_and_parse_json(message_content)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Follow-up model response could not be parsed: {str(e)}",
            )

        raw_elements = parsed_json.get("referenced_elements", [])
        ui_elements, _ = self.sanitize_coordinates(raw_elements)

        follow_up_resp = FollowUpResponse(
            session_id="",  # will be populated by endpoint
            question=question,
            answer=parsed_json.get("answer", "Follow-up response generated."),
            suggested_next_steps=parsed_json.get("suggested_next_steps", []),
            visible_evidence=parsed_json.get("visible_evidence", []),
            uncertainties=parsed_json.get("uncertainties", []),
            referenced_elements=ui_elements,
            model_tag=tag,
            inference_duration_seconds=duration,
        )

        return follow_up_resp, tag, duration


# Global client instance
ollama_client = OllamaClient()
