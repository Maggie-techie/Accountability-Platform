"""
LLM API wrapper with retry logic, JSON/text modes, and observability hooks.
"""
import logging
import os
import time
import requests
from typing import Optional

from .schemas import ErrorResponse

logger = logging.getLogger(__name__)

# Configuration from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 2  # seconds
REQUEST_TIMEOUT = 60  # seconds


class LLMError(Exception):
    """Raised when LLM call fails after retries."""
    def __init__(self, message: str, status_code: int = None, details: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


def _build_headers() -> dict:
    """Build request headers."""
    if not GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY not configured", status_code=500)
    return {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }


def _build_payload(prompt: str, model: str, json_mode: bool, temperature: float = 0.2, max_tokens: int = 8000) -> dict:
    """Build request payload."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return payload


def _handle_rate_limit(response: requests.Response, attempt: int) -> tuple[bool, int]:
    """Handle 429 rate limit. Returns (should_retry, delay_seconds)."""
    if response.status_code != 429:
        return False, 0

    if attempt >= MAX_RETRIES - 1:
        return False, 0

    retry_after = response.headers.get('retry-after')
    if retry_after:
        try:
            delay = int(retry_after)
        except ValueError:
            delay = BASE_DELAY * (2 ** attempt)
    else:
        delay = BASE_DELAY * (2 ** attempt)

    logger.warning(f"Rate limited (429). Retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
    return True, delay


def call_llm_json(prompt: str, model: str = None, temperature: float = 0.2, max_tokens: int = 8000) -> dict:
    """
    Call Groq API and return parsed JSON.
    Raises LLMError on failure after retries.
    """
    model = model or GROQ_MODEL
    headers = _build_headers()
    payload = _build_payload(prompt, model, json_mode=True, temperature=temperature, max_tokens=max_tokens)

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)

            # Handle rate limiting
            should_retry, delay = _handle_rate_limit(response, attempt)
            if should_retry:
                time.sleep(delay)
                continue

            if not response.ok:
                logger.error(f"Groq {response.status_code}: {response.text[:300]}")
                response.raise_for_status()

            result = response.json()

            if "choices" not in result or len(result["choices"]) == 0:
                raise LLMError("Empty response from Groq API", status_code=502)

            message = result["choices"][0].get("message", {})
            content = message.get("content", "")
            finish_reason = result["choices"][0].get("finish_reason")

            # Log observability data
            usage = result.get("usage", {})
            logger.info(
                f"LLM call completed | model={model} | "
                f"prompt_tokens={usage.get('prompt_tokens')} | "
                f"completion_tokens={usage.get('completion_tokens')} | "
                f"finish_reason={finish_reason}"
            )

            # Parse JSON
            try:
                import json
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Groq response as JSON: {e}")
                logger.error(f"Finish reason: {finish_reason}")
                logger.error(f"Response content: {content[:500]}")
                raise LLMError("Groq API returned invalid JSON", status_code=502)

        except requests.exceptions.Timeout:
            logger.error(f"Groq API timeout (attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt == MAX_RETRIES - 1:
                raise LLMError("Groq API request timeout", status_code=504)
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {e}")
            if attempt == MAX_RETRIES - 1:
                raise LLMError(f"Groq API request failed: {e}", status_code=502)
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in call_llm_json: {e}")
            raise LLMError(f"Internal error: {e}", status_code=500)

    raise LLMError("Max retries exceeded", status_code=502)


def call_llm_text(prompt: str, model: str = None, temperature: float = 0.3, max_tokens: int = 2000) -> str:
    """
    Call Groq API and return plain text response.
    Raises LLMError on failure after retries.
    """
    model = model or GROQ_MODEL
    headers = _build_headers()
    payload = _build_payload(prompt, model, json_mode=False, temperature=temperature, max_tokens=max_tokens)

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)

            should_retry, delay = _handle_rate_limit(response, attempt)
            if should_retry:
                time.sleep(delay)
                continue

            if not response.ok:
                logger.error(f"Groq {response.status_code}: {response.text[:300]}")
                response.raise_for_status()

            result = response.json()

            if "choices" not in result or len(result["choices"]) == 0:
                raise LLMError("Empty response from Groq API", status_code=502)

            message = result["choices"][0].get("message", {})
            content = message.get("content", "")
            finish_reason = result["choices"][0].get("finish_reason")

            # Log observability data
            usage = result.get("usage", {})
            logger.info(
                f"LLM text call completed | model={model} | "
                f"prompt_tokens={usage.get('prompt_tokens')} | "
                f"completion_tokens={usage.get('completion_tokens')} | "
                f"finish_reason={finish_reason}"
            )

            return content

        except requests.exceptions.Timeout:
            logger.error(f"Groq API timeout (attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt == MAX_RETRIES - 1:
                raise LLMError("Groq API request timeout", status_code=504)
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {e}")
            if attempt == MAX_RETRIES - 1:
                raise LLMError(f"Groq API request failed: {e}", status_code=502)
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in call_llm_text: {e}")
            raise LLMError(f"Internal error: {e}", status_code=500)

    raise LLMError("Max retries exceeded", status_code=502)


# Backward compatibility functions
def call_llm_api(prompt: str, model: str = None) -> dict:
    """Legacy wrapper for JSON mode."""
    try:
        return call_llm_json(prompt, model)
    except LLMError as e:
        logger.error(f"LLM call failed: {e}")
        return ErrorResponse(
            _error=True,
            narrative_fields={
                "summary": "Error: " + str(e),
                "details": e.details or "LLM service unavailable"
            }
        ).model_dump()


def call_llm_api_text(prompt: str, model: str = None) -> dict:
    """Legacy wrapper for text mode."""
    try:
        text = call_llm_text(prompt, model)
        return {"response": text}
    except LLMError as e:
        logger.error(f"LLM text call failed: {e}")
        return ErrorResponse(
            _error=True,
            narrative_fields={
                "summary": "Error: " + str(e),
                "details": e.details or "LLM service unavailable"
            }
        ).model_dump()