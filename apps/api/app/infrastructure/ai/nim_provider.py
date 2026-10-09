import os
import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import httpx

from apps.api.app.core.config import get_settings

logger = logging.getLogger("sentinel.ai.nim")


class NvidiaNimProvider:
    """
    NVIDIA NIM Model Provider interface.
    Connects to NVIDIA NIM endpoints (e.g., https://integrate.api.nvidia.com/v1)
    to query Nemotron, Llama, and Gemma models for aerospace verification proposals.
    Operates securely with fallback handling when credentials are not configured.
    """

    CATALOG = [
        {
            "id": "meta/llama-3.3-70b-instruct",
            "name": "Meta Llama 3.3 70B Instruct",
            "provider": "NVIDIA_NIM",
            "contextWindow": 131072,
            "description": "State-of-the-art instruction model for structured DO-178C requirement extraction and test case authoring.",
        },
        {
            "id": "nvidia/nemotron-4-340b-instruct",
            "name": "NVIDIA Nemotron-4 340B Instruct",
            "provider": "NVIDIA_NIM",
            "contextWindow": 4096,
            "description": "NVIDIA flagship model optimized for complex code reasoning, scenario synthesis, and fault injection analysis.",
        },
        {
            "id": "google/gemma-2-27b-it",
            "name": "Google Gemma 2 27B IT",
            "provider": "NVIDIA_NIM",
            "contextWindow": 8192,
            "description": "High-efficiency open weights model tailored for fast test proposal generation and diagnostic reporting.",
        },
    ]

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = (
            api_key
            or os.environ.get("NVIDIA_NIM_API_KEY")
            or os.environ.get("NVIDIA_API_KEY")
            or os.environ.get("NIM_API_KEY")
            or getattr(self.settings, "NVIDIA_NIM_API_KEY", "")
        )
        self.base_url = (
            base_url
            or os.environ.get("NVIDIA_NIM_BASE_URL")
            or getattr(self.settings, "NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        ).rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def get_models(self) -> List[Dict[str, Any]]:
        configured = self.is_configured()
        return [
            {
                "id": m["id"],
                "name": m["name"],
                "provider": m["provider"],
                "available": configured,
                "contextWindow": m["contextWindow"],
                "description": m["description"],
            }
            for m in self.CATALOG
        ]

    def check_health(self) -> Dict[str, Any]:
        configured = self.is_configured()
        res = {
            "isConfigured": configured,
            "baseUrl": self.base_url,
            "modelsCount": len(self.CATALOG),
            "liveCallTested": False,
            "status": "ready" if configured else "disabled_no_key",
        }
        if configured:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                with httpx.Client(timeout=5.0) as client:
                    resp = client.get(f"{self.base_url}/models", headers=headers)
                    if resp.status_code == 200:
                        res["liveCallTested"] = True
                        res["status"] = "healthy"
                    else:
                        res["status"] = f"provider_http_{resp.status_code}"
            except Exception as e:
                res["status"] = f"unreachable ({type(e).__name__})"
        return res

    def complete_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_format_json: bool = False,
        timeout: float = 30.0,
    ) -> Tuple[Optional[str], bool, Optional[str]]:
        """
        Sends chat completion request to NVIDIA NIM.
        Returns: (response_text, is_live_call, error_message)
        """
        if not self.is_configured():
            return None, False, "NVIDIA NIM API key is not configured in environment."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0] and "content" in choices[0]["message"]:
                        content = choices[0]["message"]["content"]
                        return content, True, None
                    return None, False, "Malformed provider response payload"
                elif resp.status_code == 401:
                    logger.warning("NVIDIA NIM authentication rejected: invalid API key.")
                    return None, False, "Authentication failed with NVIDIA NIM (401 Unauthorized)"
                elif resp.status_code == 429:
                    logger.warning("NVIDIA NIM rate limit encountered.")
                    return None, False, "NVIDIA NIM rate limit exceeded (429 Too Many Requests)"
                else:
                    err_msg = f"NVIDIA NIM error HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(err_msg)
                    return None, False, err_msg
        except httpx.TimeoutException:
            logger.warning("NVIDIA NIM request timed out after %ss", timeout)
            return None, False, f"Request timed out after {timeout}s"
        except Exception as e:
            logger.warning("NVIDIA NIM request failed with exception: %s", str(e))
            return None, False, f"Provider error: {type(e).__name__} ({str(e)})"

    @staticmethod
    def extract_json_payload(raw_text: str) -> Optional[Any]:
        """Safely parses JSON from LLM output, extracting from markdown code fences if present."""
        if not raw_text:
            return None
        trimmed = raw_text.strip()
        # Look for ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", trimmed, re.DOTALL)
        candidate = fence_match.group(1).strip() if fence_match else trimmed
        try:
            return json.loads(candidate)
        except Exception:
            # Fallback: search for first { or [ to last } or ]
            first_brace = min((candidate.find(b) for b in ("{", "[") if candidate.find(b) != -1), default=-1)
            last_brace = max((candidate.rfind(b) for b in ("}", "]") if candidate.rfind(b) != -1), default=-1)
            if first_brace != -1 and last_brace > first_brace:
                sub = candidate[first_brace : last_brace + 1]
                try:
                    return json.loads(sub)
                except Exception:
                    pass
        return None
