"""Phase 3 provider adapter: strict local validation of provider responses.

Work Unit 3a pins the pure validation contract (``parse_provider_response``,
``ClassificationResult``, ``DECISION_JSON_SCHEMA``, the policy prompt). Work
Unit 3b adds the transport seam and ``classify_product``. CI makes zero network
calls: the transport is always injected or monkeypatched in these tests.
"""
import inspect
import json
import os
from dataclasses import FrozenInstanceError, fields

import pytest
import requests

import curation_provider
from curation import EDITORIAL_CONTEXTS, EDITORIAL_STATES
from curation_provider import (
    DECISION_JSON_SCHEMA,
    POLICY_PROMPT,
    ClassificationResult,
    classify_product,
    parse_provider_response,
)


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


def _content(state="eligible", context=None, reason="good gift"):
    return json.dumps({"state": state, "context": context, "reason": reason})


def _body(content):
    """A minimal OpenAI-compatible chat-completions body."""
    return {"choices": [{"message": {"content": content}}]}


# --------------------------------------------------------------------------- #
# 3.1 — Response validation: well-formed bodies
# --------------------------------------------------------------------------- #


def test_parse_returns_a_classification_result_for_a_well_formed_body():
    result = parse_provider_response(_body(_content(state="eligible", reason="suitable")))

    assert isinstance(result, ClassificationResult)
    assert result.state == "eligible"
    assert result.context is None
    assert result.reason == "suitable"


def test_parse_accepts_contextual_when_the_context_is_in_vocabulary():
    body = _body(_content(state="contextual", context="hogar-y-cocina", reason="only for home"))

    result = parse_provider_response(body, allowed_contexts={"hogar-y-cocina"})

    assert result is not None
    assert result.state == "contextual"
    assert result.context == "hogar-y-cocina"
    assert result.reason == "only for home"


def test_parse_accepts_unknown_as_a_first_class_outcome():
    result = parse_provider_response(_body(_content(state="unknown", reason="not determinable")))

    assert result is not None
    assert result.state == "unknown"
    assert result.context is None


# --------------------------------------------------------------------------- #
# 3.1 — Response validation: invalid shapes ⇒ None (failure-not-cached)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "body",
    [{}, {"choices": []}, {"choices": "not-a-list"}, {"choices": None}],
    ids=["empty-body", "empty-choices", "choices-not-a-list", "choices-null"],
)
def test_parse_returns_none_when_choices_are_missing_or_empty(body):
    assert parse_provider_response(body) is None


def test_parse_returns_none_when_the_body_is_not_a_dict():
    assert parse_provider_response(None) is None
    assert parse_provider_response("not a body") is None


@pytest.mark.parametrize(
    "content",
    ["not json", "[1, 2, 3]", '"a scalar string"', "123", "null", ""],
    ids=["garbage", "json-array", "json-string", "json-number", "json-null", "empty-string"],
)
def test_parse_returns_none_when_content_is_not_a_json_object(content):
    assert parse_provider_response(_body(content)) is None


@pytest.mark.parametrize(
    "state", ["banned", "ELIGIBLE", "", None],
    ids=["outside-enum", "wrong-case", "empty", "missing"],
)
def test_parse_returns_none_when_state_is_outside_the_enum(state):
    payload = {"context": None, "reason": "why"}
    if state is not None:
        payload["state"] = state
    assert parse_provider_response(_body(json.dumps(payload))) is None


@pytest.mark.parametrize("context", [None, "", "   "], ids=["missing", "empty", "blank"])
def test_parse_returns_none_for_contextual_without_a_context(context):
    body = _body(_content(state="contextual", context=context, reason="why"))
    assert parse_provider_response(body, allowed_contexts={"hogar-y-cocina"}) is None


def test_parse_returns_none_for_contextual_context_outside_the_vocabulary():
    body = _body(_content(state="contextual", context="electronica", reason="why"))
    assert parse_provider_response(body, allowed_contexts={"hogar-y-cocina"}) is None


def test_parse_rejects_contextual_against_the_default_empty_vocabulary():
    # v1 default: without a product slug the closed vocabulary is empty, so a
    # contextual decision cannot be validated and is treated as invalid.
    assert parse_provider_response(_body(_content(state="contextual", context="hogar"))) is None
    assert EDITORIAL_CONTEXTS == frozenset()


@pytest.mark.parametrize("reason", [None, "", "   "], ids=["missing", "empty", "blank"])
def test_parse_returns_none_when_reason_is_missing_or_empty(reason):
    payload = {"state": "eligible", "context": None}
    if reason is not None:
        payload["reason"] = reason
    assert parse_provider_response(_body(json.dumps(payload))) is None


def test_parse_normalizes_a_stray_context_on_a_non_contextual_state():
    body = _body(_content(state="eligible", context="hogar-y-cocina", reason="ok"))

    result = parse_provider_response(body)

    assert result is not None
    assert result.context is None


def test_parse_returns_none_when_the_message_shape_is_broken():
    assert parse_provider_response({"choices": [{"message": "nope"}]}) is None
    assert parse_provider_response({"choices": [{"message": {"content": 42}}]}) is None
    assert parse_provider_response({"choices": [{"not_message": {}}]}) is None


# --------------------------------------------------------------------------- #
# 3.1 — Structural constants
# --------------------------------------------------------------------------- #


def test_decision_json_schema_is_strict_and_pins_the_state_enum():
    assert DECISION_JSON_SCHEMA["type"] == "object"
    assert DECISION_JSON_SCHEMA["additionalProperties"] is False
    assert DECISION_JSON_SCHEMA["properties"]["state"]["enum"] == list(EDITORIAL_STATES)
    assert "null" in DECISION_JSON_SCHEMA["properties"]["context"]["type"]
    assert DECISION_JSON_SCHEMA["properties"]["reason"]["minLength"] == 1
    assert set(DECISION_JSON_SCHEMA["required"]) >= {"state", "context", "reason"}


def test_policy_prompt_is_a_non_empty_constant():
    assert isinstance(POLICY_PROMPT, str)
    assert POLICY_PROMPT.strip()
    # The prompt is a constant, never interpolated with product or user data.
    assert "{" not in POLICY_PROMPT and "}" not in POLICY_PROMPT


def test_classification_result_is_frozen_and_has_the_three_documented_fields():
    result = ClassificationResult(state="eligible", context=None, reason="ok")

    assert [field.name for field in fields(ClassificationResult)] == [
        "state",
        "context",
        "reason",
    ]
    with pytest.raises(FrozenInstanceError):
        result.state = "excluded"  # type: ignore[misc]



# --------------------------------------------------------------------------- #
# 3.2 — production transport + minimal payload
# --------------------------------------------------------------------------- #


def _item(**overrides):
    base = {
        "title": "Cafetera",
        "category": "Hogar y cocina",
        "category_slug": "hogar-y-cocina",
    }
    base.update(overrides)
    return base


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


def test_transport_contract_is_payload_to_body():
    from typing import Callable

    assert curation_provider.Transport == Callable[[dict], dict]


def test_provider_env_constants_default_from_the_environment():
    assert curation_provider.EDITORIAL_PROVIDER_BASE_URL == os.getenv(
        "EDITORIAL_PROVIDER_BASE_URL", "https://api.nan.builders/v1"
    )
    assert curation_provider.EDITORIAL_PROVIDER_MODEL == os.getenv(
        "EDITORIAL_PROVIDER_MODEL", "qwen3.6"
    )
    assert curation_provider.EDITORIAL_PROVIDER_API_KEY == os.getenv(
        "EDITORIAL_PROVIDER_API_KEY"
    )


def test_post_chat_completions_uses_bearer_auth_url_and_timeout(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return _FakeResponse(_body(_content()))

    monkeypatch.setattr(curation_provider.requests, "post", fake_post)

    body = curation_provider._post_chat_completions(
        {"model": "m"}, base_url="https://api.example/v1", api_key="secret", timeout=7.5
    )

    assert captured["url"] == "https://api.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["timeout"] == 7.5
    assert body == _body(_content())


def test_post_chat_completions_refuses_without_an_api_key(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no HTTP call may be attempted without an API key")

    monkeypatch.setattr(curation_provider.requests, "post", forbidden)

    with pytest.raises(ValueError):
        curation_provider._post_chat_completions({"model": "m"}, api_key=None)


def test_build_payload_contains_only_the_product_title_and_category():
    item = _item(
        user_id=7,
        wishes=[{"receiver": "Ana", "email": "ana@example.com"}],
        email="ana@example.com",
    )

    payload = curation_provider._build_payload(item, "qwen3.6")

    product = json.loads(payload["messages"][1]["content"])
    assert set(product) == {"title", "category"}
    assert product["title"] == "Cafetera"
    assert product["category"] == "Hogar y cocina"
    assert payload["messages"][0]["role"] == "system"

    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("user_id", "wishes", "email", "ana@example.com", "receiver"):
        assert forbidden not in serialized


def test_build_payload_sets_the_model_and_the_strict_response_format():
    payload = curation_provider._build_payload(_item(), "override-model")

    assert payload["model"] == "override-model"
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": DECISION_JSON_SCHEMA,
    }


# --------------------------------------------------------------------------- #
# 3.3 — classify_product orchestration and failure semantics
# --------------------------------------------------------------------------- #


class _RecordingTransport:
    """Records every payload; optionally raises or returns a fixed body."""

    def __init__(self, *, body=None, exc=None):
        self.body = body
        self.exc = exc
        self.payloads = []

    def __call__(self, payload):
        self.payloads.append(payload)
        if self.exc is not None:
            raise self.exc
        return self.body


def test_classify_product_signature_matches_the_expanded_contract():
    params = inspect.signature(classify_product).parameters

    assert list(params) == [
        "item", "transport", "timeout", "max_attempts", "base_url", "model", "api_key",
    ]
    assert params["item"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    for name in ("transport", "timeout", "max_attempts", "base_url", "model", "api_key"):
        assert params[name].kind is inspect.Parameter.KEYWORD_ONLY, name
    assert params["transport"].default is None
    assert params["timeout"].default == 30.0
    assert params["max_attempts"].default == 2


def test_classify_returns_a_result_via_an_injected_transport():
    transport = _RecordingTransport(body=_body(_content(state="excluded", reason="not a gift")))

    result = classify_product(_item(), transport=transport)

    assert result == ClassificationResult(state="excluded", context=None, reason="not a gift")
    assert len(transport.payloads) == 1


def test_classify_sends_the_minimal_build_payload():
    transport = _RecordingTransport(body=_body(_content()))

    classify_product(_item(), transport=transport)

    assert transport.payloads[0] == curation_provider._build_payload(
        _item(), curation_provider.EDITORIAL_PROVIDER_MODEL
    )


def test_classify_returns_none_when_the_transport_raises():
    transport = _RecordingTransport(exc=RuntimeError("connection reset"))

    assert classify_product(_item(), transport=transport) is None


def test_classify_returns_none_on_a_transport_timeout():
    transport = _RecordingTransport(exc=requests.exceptions.Timeout("slow"))

    assert classify_product(_item(), transport=transport) is None


def test_classify_retries_are_bounded_by_max_attempts():
    transport = _RecordingTransport(exc=RuntimeError("boom"))

    assert classify_product(_item(), transport=transport) is None
    assert len(transport.payloads) == 2  # default max_attempts

    transport_three = _RecordingTransport(exc=RuntimeError("boom"))
    assert classify_product(_item(), transport=transport_three, max_attempts=3) is None
    assert len(transport_three.payloads) == 3


def test_classify_returns_none_on_invalid_response_after_bounded_attempts():
    transport = _RecordingTransport(body={"choices": []})

    assert classify_product(_item(), transport=transport) is None
    assert len(transport.payloads) == 2


def test_classify_never_raises_to_callers():
    def exploding(payload):
        raise ValueError("unexpected provider client bug")

    assert classify_product(_item(), transport=exploding) is None


def test_classify_enforces_the_v1_context_equals_category_slug_rule():
    bad = _RecordingTransport(
        body=_body(_content(state="contextual", context="electronica", reason="cross-category"))
    )
    good = _RecordingTransport(
        body=_body(_content(state="contextual", context="hogar-y-cocina", reason="home only"))
    )

    # Out-of-vocabulary context is invalid, so the response is treated as a failure.
    assert classify_product(_item(), transport=bad) is None
    result = classify_product(_item(), transport=good)
    assert result is not None
    assert result.state == "contextual"
    assert result.context == "hogar-y-cocina"


def test_classify_rejects_contextual_when_the_item_has_no_category_slug():
    transport = _RecordingTransport(
        body=_body(_content(state="contextual", context="hogar-y-cocina", reason="x"))
    )

    assert classify_product({"title": "T", "category": "C"}, transport=transport) is None


def test_classify_uses_the_env_model_in_the_payload(monkeypatch):
    monkeypatch.setattr(curation_provider, "EDITORIAL_PROVIDER_MODEL", "env-model")
    transport = _RecordingTransport(body=_body(_content()))

    classify_product(_item(), transport=transport)

    assert transport.payloads[0]["model"] == "env-model"


def test_classify_model_override_reaches_the_payload():
    transport = _RecordingTransport(body=_body(_content()))

    classify_product(_item(), transport=transport, model="override-model")

    assert transport.payloads[0]["model"] == "override-model"


def test_classify_overrides_reach_the_production_request(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return _FakeResponse(_body(_content(reason="ok")))

    monkeypatch.setattr(curation_provider.requests, "post", fake_post)

    result = classify_product(
        _item(),
        base_url="https://api.override/v1",
        model="override-model",
        api_key="key-123",
        timeout=5.0,
    )

    assert result is not None
    assert captured["url"] == "https://api.override/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer key-123"
    assert captured["json"]["model"] == "override-model"
    assert captured["timeout"] == 5.0


def test_classify_env_defaults_reach_the_production_request(monkeypatch):
    monkeypatch.setattr(curation_provider, "EDITORIAL_PROVIDER_BASE_URL", "https://api.env/v1")
    monkeypatch.setattr(curation_provider, "EDITORIAL_PROVIDER_MODEL", "env-model")
    monkeypatch.setattr(curation_provider, "EDITORIAL_PROVIDER_API_KEY", "env-key")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return _FakeResponse(_body(_content()))

    monkeypatch.setattr(curation_provider.requests, "post", fake_post)

    result = classify_product({"title": "T", "category": "C", "category_slug": "hogar-y-cocina"})

    assert result is not None
    assert captured["url"] == "https://api.env/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer env-key"
    assert captured["json"]["model"] == "env-model"


def test_injected_transport_never_calls_requests_post(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("requests.post must never be hit when a transport is injected")

    monkeypatch.setattr(curation_provider.requests, "post", forbidden)

    result = classify_product(_item(), transport=_RecordingTransport(body=_body(_content())))

    assert result is not None


def test_classify_returns_none_when_the_api_key_is_unconfigured(monkeypatch):
    monkeypatch.setattr(curation_provider, "EDITORIAL_PROVIDER_API_KEY", None)

    def forbidden(*args, **kwargs):
        raise AssertionError("no HTTP call may be attempted without an API key")

    monkeypatch.setattr(curation_provider.requests, "post", forbidden)

    assert classify_product(_item()) is None
