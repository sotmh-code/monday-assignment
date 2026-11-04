"""Provider adapter: one place that talks to the model API.

Responsibilities
  * Structured output: send the Pydantic model's JSON schema via output_config.format, then
    validate the returned JSON locally (never trust the wire blindly).
  * Transport retries: delegated to the Anthropic SDK (max_retries) which retries 408/409/429/5xx
    and connection errors with exponential backoff + jitter and honours retry-after headers.
  * Output retries: one extra attempt when the response is truncated or fails validation.
  * Error classification: every failure becomes an LLMError with a stable `kind`, and errors that
    will fail every subsequent call (bad key, unknown model) are marked fatal_for_batch.
  * Audit: model actually used, request IDs, token usage, attempts, latency. No prompt or
    response content is logged here.

The rest of the pipeline only depends on the StructuredLLM protocol, so tests use a fake.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Generic, Protocol, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    def __init__(
        self,
        kind: str,
        message: str,
        *,
        retryable: bool = False,
        fatal_for_batch: bool = False,
        request_ids: list[str] | None = None,
        attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.retryable = retryable
        self.fatal_for_batch = fatal_for_batch
        self.request_ids = request_ids or []
        self.attempts = attempts


@dataclass
class LLMResult(Generic[T]):
    parsed: T
    model: str
    request_ids: list[str] = field(default_factory=list)
    attempts: int = 1
    stop_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    latency_ms: int = 0


class StructuredLLM(Protocol):
    model: str

    def generate(self, *, system: str, user: str, schema: type[T], purpose: str) -> LLMResult[T]: ...


def _classify_api_error(exc: Exception) -> LLMError:
    """Map SDK exceptions (raised after the SDK's own transport retries) to LLMError."""
    request_id = getattr(exc, "request_id", None)
    rids = [request_id] if request_id else []
    # Order matters: most specific first. APITimeoutError subclasses APIConnectionError.
    if isinstance(exc, anthropic.AuthenticationError):
        return LLMError("auth", "Authentication failed: check CRESTVIEW_LLM_API_KEY", fatal_for_batch=True, request_ids=rids)
    if isinstance(exc, anthropic.PermissionDeniedError):
        return LLMError("permission", "API key lacks permission for this model/feature", fatal_for_batch=True, request_ids=rids)
    if isinstance(exc, anthropic.NotFoundError):
        return LLMError("model_not_found", "Model or endpoint not found: check CRESTVIEW_LLM_MODEL", fatal_for_batch=True, request_ids=rids)
    if isinstance(exc, anthropic.RateLimitError):
        return LLMError("rate_limited", "Rate limited after SDK retries were exhausted", retryable=True, request_ids=rids)
    if isinstance(exc, anthropic.BadRequestError):
        return LLMError("bad_request", f"Request rejected: {getattr(exc, 'message', exc)}", request_ids=rids)
    if isinstance(exc, anthropic.APIStatusError):
        status = exc.status_code
        if status >= 500:
            return LLMError("server_error", f"Provider error HTTP {status} after retries", retryable=True, request_ids=rids)
        return LLMError("api_error", f"HTTP {status}: {getattr(exc, 'message', exc)}", request_ids=rids)
    if isinstance(exc, anthropic.APITimeoutError):
        return LLMError("timeout", "Request timed out after retries", retryable=True)
    if isinstance(exc, anthropic.APIConnectionError):
        return LLMError("connection", "Could not reach provider after retries", retryable=True)
    return LLMError("unexpected", f"{type(exc).__name__}: {exc}")


class AnthropicStructuredLLM:
    """Anthropic Messages API with JSON-schema structured outputs."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        effort: str = "medium",
        timeout_seconds: float = 120.0,
        max_retries: int = 3,
        max_tokens: int = 16000,
        max_output_attempts: int = 2,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        # api_key is passed explicitly; never rely on an ambient ANTHROPIC_API_KEY.
        self.client = client or anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds, max_retries=max_retries)
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.max_output_attempts = max(1, max_output_attempts)
        self._schema_cache: dict[type, dict] = {}

    def _format_for(self, schema: type[BaseModel]) -> dict:
        if schema not in self._schema_cache:
            self._schema_cache[schema] = {
                "type": "json_schema",
                "schema": anthropic.transform_schema(schema.model_json_schema()),
            }
        return self._schema_cache[schema]

    def generate(self, *, system: str, user: str, schema: type[T], purpose: str) -> LLMResult[T]:
        request_ids: list[str] = []
        in_tok = out_tok = cache_read = 0
        started = time.monotonic()
        last_problem = ""
        last_kind = "invalid_output"
        messages: list[dict] = [{"role": "user", "content": user}]

        for attempt in range(1, self.max_output_attempts + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    # Stable system prompt is cached across the batch (prefix caching).
                    system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                    messages=messages,
                    output_config={"effort": self.effort, "format": self._format_for(schema)},
                )
            except anthropic.APIError as exc:
                err = _classify_api_error(exc)
                err.request_ids = request_ids + err.request_ids
                err.attempts = attempt
                raise err from exc

            if response._request_id:
                request_ids.append(response._request_id)
            in_tok += response.usage.input_tokens or 0
            out_tok += response.usage.output_tokens or 0
            cache_read += getattr(response.usage, "cache_read_input_tokens", None) or 0
            log.debug("%s attempt=%d stop=%s request_id=%s", purpose, attempt, response.stop_reason, response._request_id)

            if response.stop_reason == "refusal":
                category = getattr(getattr(response, "stop_details", None), "category", None)
                raise LLMError(
                    "refusal",
                    f"Model declined the request (category={category}); route to manual triage",
                    request_ids=request_ids,
                    attempts=attempt,
                )

            text = "".join(b.text for b in response.content if b.type == "text")
            if response.stop_reason == "max_tokens":
                last_kind, last_problem = "truncated_output", "Response hit max_tokens before completing the JSON"
                continue
            try:
                parsed = schema.model_validate_json(text)
            except ValidationError as exc:
                last_kind = "invalid_output"
                last_problem = f"Schema validation failed: {exc.error_count()} error(s); first: {exc.errors()[0]['msg']}"
                # Repair attempt: show the model its own output and the validation error.
                messages = [
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": text or "(empty)"},
                    {
                        "role": "user",
                        "content": "Your previous output did not validate against the required schema: "
                        f"{json.dumps(str(exc)[:1500])}. Return a corrected, complete JSON object only.",
                    },
                ]
                continue

            return LLMResult(
                parsed=parsed,
                model=response.model,
                request_ids=request_ids,
                attempts=attempt,
                stop_reason=response.stop_reason,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cache_read_input_tokens=cache_read,
                latency_ms=int((time.monotonic() - started) * 1000),
            )

        raise LLMError(last_kind, last_problem, request_ids=request_ids, attempts=self.max_output_attempts)
