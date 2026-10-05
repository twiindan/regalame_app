"""NaN Builders provider adapter for editorial classification.

Pure response validation plus the transport seam used by the classification
job. Every provider response is validated locally and strictly, and any invalid
shape is treated as a failure (``None``) so it is never cached. The production
transport uses the pinned ``requests`` dependency; the transport is injectable so
tests and CI make zero network calls.
"""

import json
import os
from dataclasses import dataclass
from functools import partial
from typing import Callable, Iterable, Optional

import requests

from curation import EDITORIAL_CONTEXTS, EDITORIAL_STATES

# --------------------------------------------------------------------------- #
# Provider configuration (repo convention: module-level ``os.getenv``)
# --------------------------------------------------------------------------- #

#: Provider base URL; OpenAI-compatible ``/chat/completions`` is appended.
EDITORIAL_PROVIDER_BASE_URL = os.getenv(
    "EDITORIAL_PROVIDER_BASE_URL", "https://api.nan.builders/v1"
)

#: Model identifier sent in the request payload.
EDITORIAL_PROVIDER_MODEL = os.getenv("EDITORIAL_PROVIDER_MODEL", "qwen3.6")

#: Provider API key. No default: an unconfigured key fails the call (never raises
#: to callers; ``classify_product`` turns it into a ``None`` result). It may be
#: supplied as ``EDITORIAL_PROVIDER_API_KEY`` (preferred) or, as a fallback, the
#: shared ``NAN_API_KEY`` used across the NaN Builders environment.
EDITORIAL_PROVIDER_API_KEY = os.getenv("EDITORIAL_PROVIDER_API_KEY") or os.getenv("NAN_API_KEY")

#: A transport turns a request payload into a parsed JSON body.
Transport = Callable[[dict], dict]

_DEFAULT_TIMEOUT = 30.0



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


# --------------------------------------------------------------------------- #
# Transport + classification
# --------------------------------------------------------------------------- #


def _post_chat_completions(payload: dict, *, base_url: Optional[str] = None,
                           api_key: Optional[str] = None,
                           timeout: float = _DEFAULT_TIMEOUT) -> dict:
    """Production transport: POST ``payload`` to the chat-completions endpoint.

    Resolves the base URL and API key from the explicit arguments or the module
    env configuration, and authenticates with ``Authorization: Bearer <key>``.
    Raises on any HTTP or key error; ``classify_product`` converts that into a
    ``None`` result.
    """
    resolved_base_url = base_url if base_url is not None else EDITORIAL_PROVIDER_BASE_URL
    resolved_api_key = api_key if api_key is not None else EDITORIAL_PROVIDER_API_KEY
    if not resolved_api_key:
        raise ValueError("EDITORIAL_PROVIDER_API_KEY is not configured")

    response = requests.post(
        f"{resolved_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {resolved_api_key}"},
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _build_payload(item: dict, model: str) -> dict:
    """Build the provider payload from a product item.

    Data minimization: the only product facts sent are the title and the
    observed category. User, wish and account data never enter the payload.
    """
    product = {"title": item.get("title"), "category": item.get("category")}
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": POLICY_PROMPT},
            {"role": "user", "content": json.dumps(product, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_schema", "json_schema": DECISION_JSON_SCHEMA},
    }


def _allowed_contexts(item: dict) -> set[str]:
    """The v1 contextual vocabulary for a product item.

    v1: a contextual decision is valid only when its context equals the
    product's own ``category_slug`` (plus the closed policy vocabulary, empty at
    v1). It is supplied from the item because ``parse_provider_response`` is pure
    and cannot know the product.
    """
    allowed = set(EDITORIAL_CONTEXTS)
    slug = item.get("category_slug")
    if isinstance(slug, str) and slug:
        allowed.add(slug)
    return allowed


def classify_product(item: dict, *, transport: Optional[Transport] = None,
                     timeout: float = _DEFAULT_TIMEOUT, max_attempts: int = 2,
                     base_url: Optional[str] = None, model: Optional[str] = None,
                     api_key: Optional[str] = None) -> Optional[ClassificationResult]:
    """Classify one product, returning ``None`` on any failure.

    ``transport`` is injectable (tests pass a fake; CI makes zero network calls).
    When omitted, the production ``requests`` transport is used with the explicit
    configuration or the module env defaults. Any transport error, timeout, or
    invalid response yields ``None``; attempts are bounded by ``max_attempts`` and
    this function never raises to its caller.
    """
    resolved_model = model if model is not None else EDITORIAL_PROVIDER_MODEL

    if transport is None:
        resolved_base_url = base_url if base_url is not None else EDITORIAL_PROVIDER_BASE_URL
        resolved_api_key = api_key if api_key is not None else EDITORIAL_PROVIDER_API_KEY
        transport = partial(
            _post_chat_completions,
            base_url=resolved_base_url,
            api_key=resolved_api_key,
            timeout=timeout,
        )

    payload = _build_payload(item, resolved_model)
    allowed_contexts = _allowed_contexts(item)

    for _ in range(max(0, int(max_attempts))):
        try:
            body = transport(payload)
        except Exception:
            continue
        result = parse_provider_response(body, allowed_contexts=allowed_contexts)
        if result is not None:
            return result
    return None
