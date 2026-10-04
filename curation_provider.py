"""NaN Builders provider adapter for editorial classification.

Pure response validation plus the transport seam used by the classification
job. This module performs no validation of its own beyond what the spec allows:
every provider response is validated locally and strictly, and any invalid
shape is treated as a failure (``None``) so it is never cached.

Work Unit 3a covers the pure validation layer (``ClassificationResult``,
``DECISION_JSON_SCHEMA``, the policy prompt and ``parse_provider_response``).
Work Unit 3b adds the transport and ``classify_product``.
"""

import json
from dataclasses import dataclass
from typing import Iterable, Optional

from curation import EDITORIAL_CONTEXTS, EDITORIAL_STATES


@dataclass(frozen=True)
class ClassificationResult:
    """A validated editorial classification produced by the provider."""

    state: str
    context: Optional[str]
    reason: str


#: Strict object schema handed to the provider as ``response_format.json_schema``.
#: ``state`` is constrained to the four editorial states, ``context`` is nullable,
#: and ``reason`` must be non-empty. The provider is not trusted to honour it;
#: ``parse_provider_response`` re-validates every field regardless.
DECISION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "state": {"type": "string", "enum": list(EDITORIAL_STATES)},
        "context": {"type": ["string", "null"]},
        "reason": {"type": "string", "minLength": 1},
    },
    "required": ["state", "context", "reason"],
    "additionalProperties": False,
}

#: System prompt describing the editorial policy. A constant, never interpolated
#: with product or user data (the product's facts travel in the user message).
POLICY_PROMPT = (
    "You classify Amazon product titles for a gift-ideas catalogue. "
    "Reply with a single strict JSON object and nothing else, using exactly these keys: "
    "state (one of eligible, contextual, excluded, unknown), "
    "context (a category slug when state is contextual, otherwise null), and "
    "reason (a short non-empty explanation). "
    "eligible means a suitable general gift idea; "
    "contextual means suitable only within a specific category; "
    "excluded means not suitable as a gift idea; "
    "unknown means gift suitability cannot be determined from the title and category. "
    "Base the decision only on the title and category provided."
)


def _resolve_allowed_contexts(allowed_contexts: Optional[Iterable[str]]) -> set[str]:
    """The vocabulary a ``contextual`` context must belong to.

    v1 defaults to the closed ``EDITORIAL_CONTEXTS`` policy vocabulary (empty at
    v1): without a product slug supplied by ``classify_product`` a contextual
    decision cannot be validated and is treated as invalid.
    """
    if allowed_contexts is None:
        return set(EDITORIAL_CONTEXTS)
    return set(allowed_contexts)


def parse_provider_response(body: dict,
                            *,
                            allowed_contexts: Optional[Iterable[str]] = None
                            ) -> Optional[ClassificationResult]:
    """Validate a raw chat-completions body into a ``ClassificationResult``.

    Pure: it never performs I/O and never raises. It returns ``None`` for every
    invalid shape — a missing/empty ``choices`` list, content that does not parse
    as a JSON object, a ``state`` outside the four-state enum, a ``contextual``
    decision with an empty, missing or out-of-vocabulary ``context``, a
    missing/empty ``reason`` — and normalizes a stray ``context`` to ``None`` for
    every non-contextual state.
    """
    if not isinstance(body, dict):
        return None

    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None

    content = message.get("content")
    if not isinstance(content, str):
        return None
    try:
        decision = json.loads(content)
    except (ValueError, TypeError):
        return None
    if not isinstance(decision, dict):
        return None

    state = decision.get("state")
    if state not in EDITORIAL_STATES:
        return None

    reason = decision.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return None

    context = decision.get("context")
    if state == "contextual":
        if not isinstance(context, str) or not context.strip():
            return None
        if context not in _resolve_allowed_contexts(allowed_contexts):
            return None
        return ClassificationResult(state=state, context=context, reason=reason)

    # A stray context on a non-contextual decision is normalized away.
    return ClassificationResult(state=state, context=None, reason=reason)
