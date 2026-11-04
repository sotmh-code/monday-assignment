"""Runtime configuration loaded from the process environment and an optional .env file.

The POC deliberately reads its own CRESTVIEW_* variables and passes the key to the SDK
explicitly, so it never silently picks up an ambient ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Versions are recorded on every output record so a run can be reproduced / audited.
PIPELINE_VERSION = "1.0.0"
RISK_PROMPT_VERSION = "risk-triage-v4"
SUMMARY_PROMPT_VERSION = "onboarding-summary-v3"
SCHEMA_VERSION = "enriched-record-v1"

SUPPORTED_PROVIDERS = {"anthropic"}


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    api_key: str | None
    model: str
    effort: str
    timeout_seconds: float
    max_retries: int
    max_concurrency: int

    def require_api_key(self) -> str:
        if not self.api_key or self.api_key == "put_your_key_here":
            raise ConfigError(
                "CRESTVIEW_LLM_API_KEY is not set. Copy .env.example to .env and add a key, "
                "or use --replay to show previously recorded output without API calls."
            )
        return self.api_key


@dataclass(frozen=True)
class MondaySettings:
    api_token: str | None
    board_id: str | None
    api_version: str


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def load_llm_settings() -> LLMSettings:
    load_dotenv(override=False)
    provider = os.getenv("CRESTVIEW_LLM_PROVIDER", "anthropic").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ConfigError(f"Unsupported CRESTVIEW_LLM_PROVIDER {provider!r}; supported: {sorted(SUPPORTED_PROVIDERS)}")
    effort = os.getenv("CRESTVIEW_LLM_EFFORT", "medium").strip().lower()
    if effort not in {"low", "medium", "high"}:
        raise ConfigError("CRESTVIEW_LLM_EFFORT must be one of low, medium, high")
    return LLMSettings(
        provider=provider,
        api_key=os.getenv("CRESTVIEW_LLM_API_KEY") or None,
        model=os.getenv("CRESTVIEW_LLM_MODEL", "claude-sonnet-5-5").strip(),
        effort=effort,
        timeout_seconds=_float("CRESTVIEW_LLM_TIMEOUT_SECONDS", 120.0),
        max_retries=max(0, min(_int("CRESTVIEW_LLM_MAX_RETRIES", 3), 6)),
        max_concurrency=max(1, min(_int("CRESTVIEW_MAX_CONCURRENCY", 3), 8)),
    )


def load_monday_settings() -> MondaySettings:
    load_dotenv(override=False)
    return MondaySettings(
        api_token=os.getenv("MONDAY_API_TOKEN") or None,
        board_id=os.getenv("MONDAY_BOARD_ID") or None,
        api_version=os.getenv("MONDAY_API_VERSION", "2026-10"),
    )
