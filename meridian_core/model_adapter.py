"""Provider-neutral model adapter boundary for the Model Harness.

Adapters receive only approved prompt payload text. Provider credentials,
models, account/session details, and transport concerns stay inside the
adapter implementation and outside Relay's dispatch payload.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol


class ModelAdapter(Protocol):
    """Callable boundary: receive approved payload text, return model text."""

    def __call__(self, payload: str) -> str: ...


class ModelAdapterConfigError(RuntimeError):
    """Raised when a live model adapter is missing required configuration."""


@dataclass(frozen=True)
class ModelAdapterConfig:
    """Environment-backed configuration for a live provider adapter."""

    provider: str
    model: str
    api_key_env_var: str

    def require_api_key(self, env: Mapping[str, str] | None = None) -> str:
        """Return the configured API key or raise before any live call."""
        source = os.environ if env is None else env
        key = source.get(self.api_key_env_var, "").strip()
        if not key:
            raise ModelAdapterConfigError(
                f"Missing required API key environment variable: {self.api_key_env_var}"
            )
        return key


class FakeModelAdapter:
    """Deterministic test adapter that records payload-only calls."""

    def __init__(self, response: str = "fake model response") -> None:
        self.response = response
        self.received_payloads: list[str] = []

    def __call__(self, payload: str) -> str:
        self.received_payloads.append(payload)
        return self.response


class EnvConfiguredModelAdapter:
    """Env-safe wrapper for a future live provider transport.

    The transport is injected so this module has no vendor SDK dependency.
    Missing credentials fail before the transport is called.
    """

    def __init__(
        self,
        config: ModelAdapterConfig,
        transport: Callable[[str, ModelAdapterConfig, str], str],
        *,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.config = config
        self._transport = transport
        self._env = env

    def __call__(self, payload: str) -> str:
        api_key = self.config.require_api_key(self._env)
        return self._transport(payload, self.config, api_key)
