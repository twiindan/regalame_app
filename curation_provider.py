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

#: Optional OpenAI-compatible ``reasoning_effort`` sent on every request. The
#: default is unset — the field is omitted — because the latency probe showed the
#: lowered settings return a materially higher rate of *unusable* decisions: the
#: model answers ``contextual`` with an invented sub-context (e.g. ``coffee-
#: enthusiast``) that the v1 validator rejects, so those products are never cached
#: and coverage cannot reach 1.0. The system prompt now names the exact allowed
#: context vocabulary, which addresses that failure mode at the default effort;
#: the lowered settings remain opt-in until a re-probe confirms them. An empty
#: value also omits the field.
EDITORIAL_PROVIDER_REASONING_EFFORT = (
    os.getenv("EDITORIAL_PROVIDER_REASONING_EFFORT") or None
)

#: A transport turns a request payload into a parsed JSON body.
Transport = Callable[[dict], dict]

_DEFAULT_TIMEOUT = 30.0

#: Sentinel: ``_build_payload`` resolves the module-level
#: ``EDITORIAL_PROVIDER_REASONING_EFFORT`` when the caller does not pass a value.
_UNSET = object()



@dataclass(frozen=True)
class ClassificationResult:
    """A validated editorial classification produced by the provider."""

    state: str
    context: Optional[str]
    reason: str


#: Strict object schema handed to the provider as the named schema inside
#: ``response_format.json_schema``. ``state`` is constrained to the four editorial
#: states, ``context`` is nullable, and ``reason`` must be non-empty. The provider
#: is not trusted to honour it; ``parse_provider_response`` re-validates every
#: field regardless.
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
#: v2 (see ``EDITORIAL_POLICY_VERSION``): ``eligible`` is the default for any
#: plausible gift, ``excluded`` names routine replenishment/consumables, parts,
#: supplies and software explicitly, and ``contextual`` is reserved for the
#: narrow niche-use cases (the prior prompt let the model over-select
#: ``contextual`` and under-detect ``excluded``).
POLICY_PROMPT = (
    "You classify Amazon product titles for a gift-ideas catalogue. Reply with a single strict JSON object and "
    "nothing else, using exactly these keys: state (one of eligible, contextual, excluded, unknown), context (a "
    "category slug when state is contextual, otherwise null), and reason (a short non-empty explanation). Choose "
    "eligible whenever the item is a plausible gift for an ordinary person: a specific, identifiable product that "
    "is not routine replenishment. Examples: a phone, tablet or e-reader, headphones, a streaming stick, a "
    "smartwatch, a camera, a videogame or console, a board game, a toy, LEGO, a book, a film or album with a "
    "recognisable title, a gift card, voucher or store credit, clothing or shoes, jewellery, a bag, a cosmetic or "
    "skincare product, a hobby tool or gadget, a home gadget such as a lamp, an LED strip or a thermometer, an "
    "emergency or safety gadget such as a warning beacon or a torch, a USB adapter or other tech accessory, "
    "fitness equipment, a personalised or handmade keepsake, a decorative item. Choose excluded for routine "
    "replenishment and consumables, replacement parts, and professional or industrial supplies. Examples: nappies "
    "and baby wipes; pet food, cat litter and litter refills; groceries, drinks, coffee beans and coffee "
    "capsules; water, coffee-machine and vacuum filters, cartridges and descalers; dishwasher, washing-machine "
    "and dryer accessories, covers and kits; covers or fundas for clothes airers, drying racks and heated dryers "
    "(cubre-tendedero); large built-in appliances and fixtures such as extractor hoods; shower heads, fittings "
    "and other bathroom fixtures; lights designed to be mounted inside a fixture, such as under-cabinet, cupboard "
    "or ceiling lights, even when rechargeable (a freestanding or decorative lamp or an LED strip is eligible "
    "instead); flooring, tiles, wall coverings, adhesives and other building or renovation materials; toothbrush "
    "heads and replacement blades; oral irrigators or water flossers, electric toothbrushes and other "
    "personal-hygiene appliances with their refills; sewing, corset-making, haberdashery and other garment-making "
    "materials and kits; printer ink, printer paper, batteries and light bulbs; shampoo and personal-care "
    "refills; food supplements; cleaning, pest-control and disinfecting chemicals; guitar strings, glue, "
    "3D-printer filament and similar workshop refills; disposable nitrile gloves and other professional or "
    "industrial supplies; software, antivirus, operating systems and digital subscriptions; software "
    "applications, add-ons and digital subscriptions, including screen-mirroring, screen-duplication, casting, downloader "
    "and installer apps (a gift card or store credit for a store, game or app is eligible instead). Also exclude "
    "an item whose title is too vague or fragmentary to identify a concrete gift: a single word, a brand name "
    "alone, a short phrase, a slogan or a lyric. When the title is only a mood, a dedication or a fragment and "
    "names no product, brand or format, choose excluded, never eligible and never unknown. Choose contextual ONLY "
    "when the item is meaningful to someone already engaged in a specific activity or occasion and is pointless "
    "as a general gift, for example snow chains, a chainsaw or other powered garden tool, a blood-pressure "
    "monitor, a clothes-lint remover, a made-to-measure age or anniversary number, or a single mobile-account "
    "top-up. Most items are eligible or excluded; contextual is a narrow exception. Belonging to a category is "
    "NOT by itself a reason to choose contextual: a category alone never makes an item contextual, and "
    "appliances, home fixtures and tech accessories are never contextual. Choose unknown only when the title and "
    "category genuinely cannot decide. Base the decision only on the title and category provided."
)


def _context_constraint(allowed_contexts: Iterable[str]) -> str:
    """System-prompt suffix naming the exact contextual vocabulary.

    The model invents slugs (``coffee-enthusiast``, ``alcohol``) when it answers
    ``contextual``; telling it the exact values ``parse_provider_response`` will
    accept is what turns those answers from invalid into cacheable decisions.
    Rendered here, never into the constant ``POLICY_PROMPT``.
    """
    values = sorted(set(allowed_contexts))
    if values:
        rendered = ", ".join(values)
        return (
            " When state is contextual, context MUST be exactly one of: "
            f"{rendered}. If none of these fit, choose eligible, excluded, or unknown instead."
        )
    return (
        " When state is contextual, context MUST be exactly one of the allowed "
        "category contexts; none are available here, so choose eligible, excluded, "
        "or unknown instead."
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


def _build_payload(item: dict, model: str, *, allowed_contexts: Optional[Iterable[str]] = None,
                   reasoning_effort=_UNSET) -> dict:
    """Build the provider payload from a product item.

    Data minimization: the only product facts sent are the title and the
    observed category (plus the allowed context vocabulary in the system prompt,
    which is category metadata, never user data). ``allowed_contexts`` defaults
    to ``_allowed_contexts(item)`` so the prompt always names the exact values the
    strict validator accepts. ``reasoning_effort`` defaults to the module-level
    ``EDITORIAL_PROVIDER_REASONING_EFFORT`` and is omitted entirely when falsy.
    """
    if reasoning_effort is _UNSET:
        reasoning_effort = EDITORIAL_PROVIDER_REASONING_EFFORT
    if allowed_contexts is None:
        allowed_contexts = _allowed_contexts(item)
    system_prompt = POLICY_PROMPT + _context_constraint(allowed_contexts)
    product = {"title": item.get("title"), "category": item.get("category")}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(product, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "editorial_decision",
                "strict": True,
                "schema": DECISION_JSON_SCHEMA,
            },
        },
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    return payload


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


def _log_title(item: dict, limit: int = 80) -> str:
    """A bounded rendering of the item title for a failure diagnostic."""
    title = item.get("title")
    rendered = "" if title is None else str(title)
    if len(rendered) > limit:
        rendered = rendered[: limit - 3] + "..."
    return rendered


def classify_product(item: dict, *, transport: Optional[Transport] = None,
                     timeout: float = _DEFAULT_TIMEOUT, max_attempts: int = 2,
                     base_url: Optional[str] = None, model: Optional[str] = None,
                     api_key: Optional[str] = None,
                     log: Optional[Callable[..., None]] = None
                     ) -> Optional[ClassificationResult]:
    """Classify one product, returning ``None`` on any failure.

    ``transport`` is injectable (tests pass a fake; CI makes zero network calls).
    When omitted, the production ``requests`` transport is used with the explicit
    configuration or the module env defaults. Any transport error, timeout, or
    invalid response yields ``None``; attempts are bounded by ``max_attempts`` and
    this function never raises to its caller.

    ``log`` is an optional callable (the job threads its own logger in) that
    receives exactly one diagnostic line when every attempt fails, naming the last
    reason: ``error=<exc>`` for a transport failure, including a missing
    credential, or ``reason=invalid_response`` for a response the strict validator
    rejected. It is never called on success, so a healthy run stays quiet.
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

    allowed_contexts = _allowed_contexts(item)
    payload = _build_payload(item, resolved_model, allowed_contexts=allowed_contexts)

    attempts = max(0, int(max_attempts))
    last_error = None
    invalid = False
    for _ in range(attempts):
        try:
            body = transport(payload)
        except Exception as exc:
            last_error = exc
            invalid = False
            continue
        result = parse_provider_response(body, allowed_contexts=allowed_contexts)
        if result is not None:
            return result
        last_error = None
        invalid = True

    if log is not None:
        if last_error is not None:
            detail = f"error={last_error!r}"
        elif invalid:
            detail = "reason=invalid_response"
        else:
            detail = "reason=no_attempt"
        log(f"provider_failed title={_log_title(item)!r} attempts={attempts} {detail}")
    return None
