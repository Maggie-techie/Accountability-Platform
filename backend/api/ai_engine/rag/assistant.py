"""
Conversational AI Assistant with RAG (Retrieval-Augmented Generation).
Provides grounded, conversational responses using database context.
"""
import logging
from typing import Optional
from flask import Blueprint, request, jsonify

from ..core.llm import call_llm_text, LLMError
from ..core.schemas import ErrorResponse
from ..core.validation import validate_or_error, sanitize_for_client
from ..rag.retrieval import (
    retrieve_relevant_data,
    format_context_for_prompt,
    detect_intent
)

logger = logging.getLogger(__name__)

# Create blueprint
assistant_bp = Blueprint("assistant", __name__, url_prefix="/api/ai")


def build_conversational_prompt(
    user_message: str,
    conversation_history: list,
    retrieved_data: dict
) -> str:
    """
    Build a grounded prompt for conversational AI with retrieved data as context.
    """
    # Format conversation history (last 6 messages = 3 exchanges)
    history_str = ""
    if conversation_history:
        for msg in conversation_history[-6:]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_str += f"{role.capitalize()}: {content}\n"

    # Format retrieved data as context
    context_str = format_context_for_prompt(retrieved_data)

    # Build the full prompt
    prompt = f"""You are the Nyeri Accountability Platform AI Assistant. You help citizens understand Nyeri County's public finances, audit findings, and leader performance.

Your role:
- Answer questions in plain, accessible English (Kiswahili/English mix is fine)
- Ground ALL claims in the provided data context
- If data doesn't support an answer, say "I don't have data on that" rather than guessing
- Cite specific figures, findings, or sources from the context
- Be conversational but factual - like a knowledgeable civic educator
- Never fabricate numbers, findings, or quotes

CONTEXT DATA FROM DATABASE:
{context_str}

CONVERSATION HISTORY:
{history_str if history_str else "(No prior conversation)"}

CURRENT QUESTION:
User: {user_message}

INSTRUCTIONS:
Answer the user's question conversationally using ONLY the context data above.
If the context doesn't contain enough information, say so and suggest what data might help.
Keep responses concise (3-6 sentences typically) but informative.
Use a helpful, civic-education tone - not bureaucratic or academic.

Response:"""

    return prompt


def track_sources_used(retrieved_data: dict, constituency_slug: Optional[str]) -> list:
    """Track which data sources were used for response attribution."""
    sources_used = []
    if retrieved_data.get('governor'):
        sources_used.append("governor/county executive data")
    if retrieved_data.get('constituency'):
        sources_used.append(f"constituency data ({constituency_slug or 'specific'})")
    if retrieved_data.get('constituencies'):
        sources_used.append("all constituencies summary")
    if retrieved_data.get('mps'):
        sources_used.append("MP/NG-CDF data")
    if retrieved_data.get('audit_findings'):
        sources_used.append("audit findings")
    if retrieved_data.get('projects'):
        sources_used.append("project data")
    if retrieved_data.get('departments'):
        sources_used.append("department performance data")
    if retrieved_data.get('financial_data'):
        sources_used.append("county financial data")
    return sources_used


@assistant_bp.route("/assistant", methods=["POST"])
def ai_assistant():
    """
    Conversational AI Assistant endpoint with RAG.

    Request body:
    {
        "message": "string - user's question",
        "history": [{"role": "user|assistant", "content": "string"}, ...] - optional,
        "constituency_slug": "string" - optional, for constituency-specific context
    }

    Response:
    {
        "success": true,
        "response": "string - AI response",
        "sources_used": ["list of data sources referenced"],
        "constituency_slug": "string or null",
        "intent": {"needs_financial": true, ...} - detected intent
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"success": False, "error": "Message is required"}), 400

        conversation_history = data.get("history", [])
        constituency_slug = data.get("constituency_slug")

        # Detect intent and retrieve relevant data
        intent = detect_intent(user_message, constituency_slug)
        retrieved_data = retrieve_relevant_data(user_message, constituency_slug, intent)

        # Build grounded prompt
        prompt = build_conversational_prompt(user_message, conversation_history, retrieved_data)

        # Call LLM (text mode for conversational response)
        try:
            response_text = call_llm_text(prompt, temperature=0.3, max_tokens=2000)
        except LLMError as e:
            logger.error(f"LLM call failed: {e}")
            return jsonify({
                "success": False,
                "error": "AI service temporarily unavailable. Please try again."
            }), 503

        # Track sources
        sources_used = track_sources_used(retrieved_data, constituency_slug)

        return jsonify({
            "success": True,
            "response": response_text,
            "sources_used": sources_used,
            "constituency_slug": constituency_slug,
            "intent": intent
        })

    except Exception as e:
        logger.error(f"Error in AI assistant: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@assistant_bp.route("/assistant/intent", methods=["POST"])
def detect_query_intent():
    """
    Debug endpoint to see what intent was detected for a query.
    Useful for testing RAG retrieval logic.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        query = data.get("message", "").strip()
        constituency_slug = data.get("constituency_slug")

        if not query:
            return jsonify({"success": False, "error": "Message is required"}), 400

        intent = detect_intent(query, constituency_slug)
        retrieved_data = retrieve_relevant_data(query, constituency_slug, intent)

        return jsonify({
            "success": True,
            "query": query,
            "intent": intent,
            "data_sections_retrieved": list(retrieved_data.keys()),
            "constituency_slug": constituency_slug
        })

    except Exception as e:
        logger.error(f"Error in intent detection: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500