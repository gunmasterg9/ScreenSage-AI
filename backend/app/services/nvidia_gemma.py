"""Dedicated NVIDIA Gemma 4 AI Service.
Integrates with hosted google/gemma-4-31b-it on https://integrate.api.nvidia.com/v1.
"""

import asyncio
import json
import logging
import re
import time
from typing import Optional, Tuple, Dict, Any, List
import httpx
from fastapi import HTTPException, status
from backend.app.config import settings
from backend.app.schemas import (
    ScreenExplanation,
    BoundingBox,
    UIElement,
    FollowUpResponse,
)

logger = logging.getLogger("screensage.nvidia_gemma")

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
    "Key visible heading, message, or error text copied verbatim from screenshot"
  ],
  "answer_to_user_question": "Direct, actionable answer to the user's question '{question}', grounded in visible evidence.",
  "suggested_next_steps": [
    "Actionable next step grounded in visible buttons or options",
    "What the user should click or check next"
  ],
  "uncertainties_and_missing_visual_information": [
    "Explicitly note if any asked-for setting or detail is NOT visible in this screenshot, or if context is truncated"
  ]
}}

Note on bounding_box:
- All coordinates must be numbers between 0.0 and 100.0 representing percentage of the image dimensions (ymin=top, xmin=left, ymax=bottom, xmax=right).
- If you are not confident in precise coordinates for an element, set "bounding_box": null.
Output only the JSON object.
"""

FOLLOW_UP_PROMPT_TEMPLATE = """Previous context about this screenshot:
Summary: {summary}
Original Question: {original_question}
Original Answer: {original_answer}

{language_instruction}

The user has a follow-up question about the SAME screenshot:
"{follow_up_question}"

Answer the follow-up question by referencing the screenshot. Maintain strict visual grounding.
Output a JSON object with this exact structure:
{{
  "answer": "Clear, grounded answer to the follow-up question referencing visible evidence.",
  "suggested_next_steps": [
    "Recommended next action grounded in what is visible"
  ],
  "visible_evidence": [
    "Visual clues or text in the screenshot that support this answer"
  ],
  "uncertainties": [
    "Any assumptions or features not visible on screen"
  ],
  "referenced_elements": [
    {{
      "element_name": "Name of relevant element",
      "element_type": "button | input | text | menu | etc.",
      "likely_purpose": "Purpose in relation to this question",
      "visible_text": "Visible text",
      "bounding_box": null
    }}
  ]
}}
Output only the JSON object.
"""


class NvidiaGemmaService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.NVIDIA_API_KEY
        self.model = model or settings.NVIDIA_MODEL
        self.base_url = (base_url or settings.NVIDIA_BASE_URL).rstrip("/")
        self.endpoint = f"{self.base_url}/chat/completions"
        self.timeout = timeout or settings.INFERENCE_TIMEOUT_SECONDS

    @property
    def current_api_key(self) -> str:
        key = self.api_key if self.api_key is not None else (settings.NVIDIA_API_KEY or os.getenv("NVIDIA_API_KEY", ""))
        return (key or "").strip()

    def is_configured(self) -> bool:
        """Check if NVIDIA API key is configured."""
        key = self.current_api_key
        return bool(key and len(key) > 5)

    def _get_headers(self) -> Dict[str, str]:
        """Construct authorization headers without leaking key."""
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="NVIDIA API key is not configured. Please set NVIDIA_API_KEY in the backend environment or .env file.",
            )
        key = self.current_api_key
        if key.lower().startswith("bearer "):
            auth_header = key
        else:
            auth_header = f"Bearer {key}"

        return {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

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

                    # Normalized 0.0 - 1.0 from model should scale to 0.0 - 100.0%
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

    async def _send_chat_completion(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """
        Send chat completion request to NVIDIA API with telemetry, safe error masking, and controlled transient retry.
        Never logs API keys, prompt texts, or base64 screenshot contents.
        """
        headers = self._get_headers()
        masked_model = str(payload.get("model", self.model))
        msg_count = len(payload.get("messages", []))
        max_retries = 1
        total_duration = 0.0

        for attempt in range(max_retries + 1):
            start_time = time.perf_counter()
            logger.info(
                "NVIDIA API request dispatched: endpoint=%s, model=%s, messages=%d, attempt=%d/%d, timeout=%.1fs",
                self.endpoint,
                masked_model,
                msg_count,
                attempt + 1,
                max_retries + 1,
                self.timeout,
            )

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.endpoint,
                        headers=headers,
                        json=payload,
                    )
            except httpx.TimeoutException:
                elapsed = round(time.perf_counter() - start_time, 2)
                total_duration += elapsed
                logger.warning(
                    "NVIDIA API inference timed out after %.2fs on attempt %d/%d (model=%s)",
                    elapsed,
                    attempt + 1,
                    max_retries + 1,
                    masked_model,
                )
                # Avoid duplicate expensive requests on long-running timeouts
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=(
                        f"NVIDIA API inference timed out after {self.timeout}s. "
                        "The upstream NVIDIA hosted Gemma 4 cluster (google/gemma-4-31b-it) is experiencing queue backlog or latency. "
                        "Please retry shortly or try with a smaller screenshot."
                    ),
                )
            except httpx.ConnectError as ce:
                elapsed = round(time.perf_counter() - start_time, 2)
                total_duration += elapsed
                logger.warning(
                    "Connection error contacting NVIDIA API on attempt %d/%d: %s",
                    attempt + 1,
                    max_retries + 1,
                    type(ce).__name__,
                )
                if attempt < max_retries:
                    logger.info("Retrying NVIDIA connection after 1.5s backoff...")
                    await asyncio.sleep(1.5)
                    continue
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not establish connection to NVIDIA API endpoint (https://integrate.api.nvidia.com). Please check internet connectivity.",
                )
            except HTTPException:
                raise
            except Exception as e:
                elapsed = round(time.perf_counter() - start_time, 2)
                total_duration += elapsed
                logger.error("Unexpected network error contacting NVIDIA API: %s: %s", type(e).__name__, str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Network error contacting NVIDIA API: {type(e).__name__}",
                )

            elapsed = round(time.perf_counter() - start_time, 2)
            total_duration += elapsed

            logger.info(
                "NVIDIA API response received: status=%d, attempt=%d, duration=%.2fs",
                response.status_code,
                attempt + 1,
                elapsed,
            )

            # Controlled single retry for transient upstream gateway failures (502, 503, 504)
            if response.status_code in (502, 503, 504) and attempt < max_retries:
                logger.warning(
                    "Upstream NVIDIA API returned transient HTTP %d on attempt %d. Retrying once after 1.5s backoff...",
                    response.status_code,
                    attempt + 1,
                )
                await asyncio.sleep(1.5)
                continue

            # Handle HTTP error statuses from NVIDIA API
            if response.status_code == 401:
                logger.error("NVIDIA API authentication failed (HTTP 401).")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="NVIDIA API authentication failed. Please verify your NVIDIA_API_KEY has active credits at build.nvidia.com.",
                )
            elif response.status_code == 429:
                logger.warning("NVIDIA API rate limit exceeded (HTTP 429).")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="NVIDIA API rate limit reached (HTTP 429). Please wait a few seconds before submitting another request.",
                )
            elif response.status_code >= 500:
                logger.error("NVIDIA API server error (HTTP %d).", response.status_code)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"NVIDIA API server error ({response.status_code}). Upstream NIM service is currently unavailable or experiencing high load.",
                )
            elif response.status_code != 200:
                logger.error("NVIDIA API returned HTTP %d: %s", response.status_code, response.text[:120])
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"NVIDIA API request failed ({response.status_code}): {response.text[:150]}",
                )

            try:
                return response.json(), total_duration
            except Exception as e:
                logger.error("Failed to parse JSON response: %s", str(e))
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to parse NVIDIA API JSON response: {str(e)}",
                )

    async def generate_text(self, prompt: str) -> Tuple[str, str, float]:
        """
        Text-only query against hosted google/gemma-4-31b-it.
        Used for verification and text-based reasoning.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }

        res_json, duration = await self._send_chat_completion(payload)
        choices = res_json.get("choices", [])
        if not choices:
            raise HTTPException(status_code=502, detail="No completion choices returned by NVIDIA API.")

        answer = choices[0].get("message", {}).get("content", "").strip()
        return answer, self.model, duration

    async def analyze_screenshot(
        self,
        image_b64: str,
        question: str,
        language: str = "en",
        mime_type: str = "image/png",
    ) -> Tuple[ScreenExplanation, str, float]:
        """
        Multimodal screenshot analysis using NVIDIA-hosted google/gemma-4-31b-it.
        Formats image as data URL in the official OpenAI-compatible content array.
        """
        lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
        user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            question=question,
            language_instruction=lang_instruction,
        )

        # Official NVIDIA multimodal format
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_BASE},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            },
                        },
                    ],
                },
            ],
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 1500,
        }

        res_json, duration = await self._send_chat_completion(payload)
        choices = res_json.get("choices", [])
        if not choices:
            raise HTTPException(status_code=502, detail="Empty response received from NVIDIA Gemma 4.")

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise HTTPException(status_code=502, detail="No content in NVIDIA Gemma 4 response.")

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
        lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
        user_prompt = FOLLOW_UP_PROMPT_TEMPLATE.format(
            summary=summary,
            original_question=original_question,
            original_answer=original_answer,
            follow_up_question=question,
            language_instruction=lang_instruction,
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_BASE},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            },
                        },
                    ],
                },
            ],
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 1000,
        }

        res_json, duration = await self._send_chat_completion(payload)
        choices = res_json.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""

        try:
            parsed_json = self.clean_and_parse_json(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Follow-up model response could not be parsed: {str(e)}",
            )

        raw_elements = parsed_json.get("referenced_elements", [])
        ui_elements, _ = self.sanitize_coordinates(raw_elements)

        follow_up_resp = FollowUpResponse(
            session_id="",
            question=question,
            answer=parsed_json.get("answer", "Follow-up response generated."),
            suggested_next_steps=parsed_json.get("suggested_next_steps", []),
            visible_evidence=parsed_json.get("visible_evidence", []),
            uncertainties=parsed_json.get("uncertainties", []),
            referenced_elements=ui_elements,
            model_tag=self.model,
            inference_duration_seconds=duration,
        )

        return follow_up_resp, self.model, duration


# Global service instance
nvidia_service = NvidiaGemmaService()
