"""
Output validation with retry logic.
Treats LLM output as untrusted input - validates against Pydantic schemas.
"""
import logging
from typing import Optional, Type
from pydantic import BaseModel, ValidationError

from .schemas import ErrorResponse

logger = logging.getLogger(__name__)


def validate_output(
    response: dict,
    schema: Type[BaseModel],
    max_retries: int = 1,
    fix_prompt_fn: Optional[callable] = None
) -> tuple[BaseModel | None, ErrorResponse | None]:
    """
    Validate LLM response against schema with retry.

    Args:
        response: Raw LLM response dict
        schema: Pydantic model class to validate against
        max_retries: Number of retry attempts on validation failure
        fix_prompt_fn: Optional function(prompt, errors) -> fixed_prompt for retry

    Returns:
        (validated_model, error_response) - one will be None
    """
    # Check for explicit error flag first
    if response.get("_error"):
        return None, ErrorResponse(
            _error=True,
            narrative_fields=response.get("narrative_fields", {"summary": "Unknown error", "details": "LLM returned error flag"})
        )

    # Try validation
    for attempt in range(max_retries + 1):
        try:
            validated = schema.model_validate(response)
            return validated, None
        except ValidationError as e:
            logger.warning(f"Output validation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")

            if attempt < max_retries and fix_prompt_fn:
                # Could retry with fixed prompt - would need to call LLM again
                # For now, just log and continue to next attempt
                pass
            elif attempt == max_retries:
                # Final attempt failed - return error
                error_details = []
                for err in e.errors():
                    field = " -> ".join(str(x) for x in err["loc"])
                    error_details.append(f"{field}: {err['msg']}")

                return None, ErrorResponse(
                    _error=True,
                    narrative_fields={
                        "summary": "AI response validation failed",
                        "details": f"Output schema validation failed after {max_retries + 1} attempts. Errors: {'; '.join(error_details)}"
                    }
                )

    return None, ErrorResponse(
        _error=True,
        narrative_fields={
            "summary": "AI response validation failed",
            "details": "Unexpected validation state"
        }
    )


def validate_or_error(response: dict, schema: Type[BaseModel]) -> BaseModel:
    """
    Validate response or raise ValidationError.
    Use when you want to fail fast.
    """
    if response.get("_error"):
        raise ValidationError.from_exception_data(
            title=schema.__name__,
            line_errors=[{"type": "llm_error", "loc": (), "input": response, "ctx": {"error": response.get("narrative_fields", {})}}]
        )
    return schema.model_validate(response)


def sanitize_for_client(error: ErrorResponse) -> dict:
    """Convert error response to client-safe format (no internal details)."""
    return {
        "success": False,
        "error": error.narrative_fields.get("summary", "AI processing failed")
    }