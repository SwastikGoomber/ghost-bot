"""
IntentRouter — fast local classification of incoming messages.

Uses Gemma 4 E4B via Ollama to decide, per-route, whether the message
needs RAG retrieval or contains an explicit cone request.

The router is intentionally narrow in scope:
- It does NOT have Ghost's full persona or relationship context.
- It does NOT predict autonomous coning (that is Gemini's job).
- It receives a short conversation window (last 4 messages) to resolve
  implicit references (e.g. "what if i say pwease" after a cone request).

Output: RouterFlags — two independent booleans.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from ..utils.config import get_config
from ..utils.exceptions import LLMError
from ..utils.llm import get_llm_client
from ..utils.llm.ollama import OllamaClient
from ..utils.models import RouterFlags

logger = logging.getLogger(__name__)

# Load prompt once at import time
from pathlib import Path
_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "router.md"
_ROUTER_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


class IntentRouter:
    """
    Classifies a single user message into per-route boolean flags.

    Both flags may be True simultaneously (e.g., a RAG query that also
    explicitly requests a cone). Both False means plain casual chat.
    """

    async def classify(
        self,
        message: str,
        recent_messages: Optional[list] = None,
    ) -> RouterFlags:
        """
        Classify a message and return RouterFlags.

        Args:
            message:         Raw user message text.
            recent_messages: Optional list of Message objects (last N turns).
                             Used to resolve implicit references like
                             'what if i say pwease?' after a prior cone ask.

        Falls back to RouterFlags(rag_required=False, cone_relevant=False)
        on any error so the pipeline always continues.

        Returns:
            RouterFlags with per-route booleans.
        """
        client = get_llm_client("router")
        if not isinstance(client, OllamaClient):
            logger.error("Router client is not an OllamaClient — skipping routing.")
            return RouterFlags()

        try:
            # Build user content — prepend short history if available so the
            # classifier can resolve implicit references.
            if recent_messages:
                history_lines = []
                for msg in recent_messages[-4:]:
                    speaker = "Ghost" if msg.from_bot else "User"
                    history_lines.append(f"{speaker}: {msg.content}")
                history_block = "\n".join(history_lines)
                user_content = (
                    f"Recent conversation:\n{history_block}\n\n"
                    f"New message to classify: {message}"
                )
            else:
                user_content = message

            raw = await client.generate_json(
                messages=[{"role": "user", "content": user_content}],
                system_prompt=_ROUTER_PROMPT,
            )
            
            # Clean markdown codeblocks if Ollama adds them despite format="json"
            cleaned_raw = raw.strip()
            import re
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_raw, re.DOTALL)
            if json_match:
                cleaned_raw = json_match.group(1).strip()
            elif not cleaned_raw.startswith("{") and "{" in cleaned_raw:
                # Fallback: try to find the first `{` and last `}`
                start = cleaned_raw.find("{")
                end = cleaned_raw.rfind("}")
                if start != -1 and end != -1:
                    cleaned_raw = cleaned_raw[start:end+1]

            if not cleaned_raw:
                logger.warning("IntentRouter received empty response from Ollama — defaulting to no flags.")
                return RouterFlags()

            data = json.loads(cleaned_raw)
            flags = RouterFlags(
                rag_required=bool(data.get("rag_required", False)),
                cone_relevant=bool(data.get("cone_relevant", False)),
            )
            logger.debug("Router flags for message %r: %s", message[:60], flags)
            return flags

        except json.JSONDecodeError as exc:
            logger.warning("IntentRouter JSON parse failed. Raw output: %r. Error: %s", raw, exc)
            return RouterFlags()
        except LLMError as exc:
            logger.warning("IntentRouter failed (%s) — defaulting to no flags.", exc)
            return RouterFlags()
