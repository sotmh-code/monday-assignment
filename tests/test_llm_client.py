"""Adapter tests against the real Anthropic SDK with a mocked HTTP transport (no network).

These exercise the SDK's own retry/backoff for 429/5xx, our error classification, the
refusal / truncation handling, and the single repair attempt for invalid JSON.
"""

import json

import anthropic
import httpx2
import pytest
from anthropic import DefaultHttpxClient

from src.llm_client import AnthropicStructuredLLM, LLMError
from src.schemas import RiskAssessment
from tests.conftest import make_risk


def _message(text: str, stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


class Script:
    """Returns scripted HTTP responses in order and records request bodies."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(json.loads(request.content))
        status, body = self.responses.pop(0)
        headers = {"request-id": f"req_{len(self.requests)}", "retry-after-ms": "1"}
        return httpx2.Response(status, json=body, headers=headers)


def _llm(script: Script, max_retries: int = 2) -> AnthropicStructuredLLM:
    client = anthropic.Anthropic(
        api_key="test-key",
        max_retries=max_retries,
        http_client=DefaultHttpxClient(transport=httpx2.MockTransport(script)),
    )
    return AnthropicStructuredLLM(api_key="unused", model="claude-sonnet-5-5", client=client)


def _gen(llm):
    return llm.generate(system="sys", user="<application>x</application>", schema=RiskAssessment, purpose="t")


ERR = {"type": "error", "error": {"type": "x", "message": "x"}}
GOOD = _message(make_risk().model_dump_json())


def test_success_parses_and_sends_schema_and_explicit_settings():
    script = Script((200, GOOD))
    result = _gen(_llm(script))
    assert result.parsed.risk_level.value == "LOW"
    assert result.request_ids == ["req_1"]
    body = script.requests[0]
    assert body["model"] == "claude-sonnet-5-5"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["output_config"]["effort"] == "medium"
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_rate_limit_then_success_is_retried_by_sdk():
    script = Script((429, ERR), (529, ERR), (200, GOOD))
    result = _gen(_llm(script, max_retries=2))
    assert result.parsed is not None
    assert len(script.requests) == 3


def test_rate_limit_exhausted_is_classified_retryable():
    script = Script((429, ERR), (429, ERR))
    with pytest.raises(LLMError) as ei:
        _gen(_llm(script, max_retries=1))
    assert ei.value.kind == "rate_limited" and ei.value.retryable and not ei.value.fatal_for_batch
    assert len(script.requests) == 2  # bounded


def test_auth_error_is_fatal_and_not_retried():
    script = Script((401, ERR))
    with pytest.raises(LLMError) as ei:
        _gen(_llm(script, max_retries=3))
    assert ei.value.kind == "auth" and ei.value.fatal_for_batch
    assert len(script.requests) == 1


def test_unknown_model_is_fatal():
    with pytest.raises(LLMError) as ei:
        _gen(_llm(Script((404, ERR))))
    assert ei.value.kind == "model_not_found" and ei.value.fatal_for_batch


def test_timeout_is_classified():
    def handler(request):
        raise httpx2.ReadTimeout("slow", request=request)

    client = anthropic.Anthropic(
        api_key="k", max_retries=1, http_client=DefaultHttpxClient(transport=httpx2.MockTransport(handler))
    )
    llm = AnthropicStructuredLLM(api_key="unused", model="m", client=client)
    with pytest.raises(LLMError) as ei:
        _gen(llm)
    assert ei.value.kind == "timeout" and ei.value.retryable


def test_invalid_json_gets_one_repair_attempt_then_succeeds():
    script = Script((200, _message('{"risk_level": "LOW"}')), (200, GOOD))
    result = _gen(_llm(script))
    assert result.attempts == 2
    repair_turns = script.requests[1]["messages"]
    assert [m["role"] for m in repair_turns] == ["user", "assistant", "user"]
    assert "did not validate" in repair_turns[2]["content"]


def test_invalid_json_twice_fails_explicitly():
    script = Script((200, _message("")), (200, _message("not json")))
    with pytest.raises(LLMError) as ei:
        _gen(_llm(script))
    assert ei.value.kind == "invalid_output" and ei.value.attempts == 2
    assert ei.value.request_ids == ["req_1", "req_2"]


def test_refusal_is_not_retried_or_parsed():
    script = Script((200, _message("", stop_reason="refusal")))
    with pytest.raises(LLMError) as ei:
        _gen(_llm(script))
    assert ei.value.kind == "refusal"
    assert len(script.requests) == 1


def test_truncated_output_is_retried_then_reported():
    trunc = _message('{"risk_level": "HI', stop_reason="max_tokens")
    with pytest.raises(LLMError) as ei:
        _gen(_llm(Script((200, trunc), (200, trunc))))
    assert ei.value.kind == "truncated_output"
