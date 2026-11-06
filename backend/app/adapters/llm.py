from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.core.settings import get_settings

logger = logging.getLogger(__name__)

FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def complete_json(system: str, user: str) -> dict[str, Any]:
    """OpenAI-compatible chat completion expecting a JSON object.

    Parses defensively; retries once on parse failure; raises ValueError after that.
    """
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM is not configured")

    def _call(extra_user: str | None = None) -> str:
        content = user if not extra_user else f"{user}\n\n{extra_user}"
        payload = {
            "model": settings.llm_model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        url = settings.llm_base_url.rstrip("/") + "/chat/completions"
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    raw = _call()
    try:
        return _extract_json(raw)
    except (json.JSONDecodeError, KeyError, TypeError) as first_err:
        logger.warning("LLM JSON parse failed once: %s", first_err)
        raw2 = _call("Reply with a single JSON object only. No markdown.")
        try:
            return _extract_json(raw2)
        except (json.JSONDecodeError, KeyError, TypeError) as second_err:
            raise ValueError("llm_parse_error") from second_err
