"""Tests for provider-neutral Model Harness adapters."""

from __future__ import annotations

import pytest

from meridian_core.model_adapter import (
    EnvConfiguredModelAdapter,
    FakeModelAdapter,
    ModelAdapterConfig,
    ModelAdapterConfigError,
)


class TestFakeModelAdapter:
    def test_returns_deterministic_response(self) -> None:
        adapter = FakeModelAdapter("ok")
        assert adapter("payload") == "ok"

    def test_records_only_payload_text(self) -> None:
        adapter = FakeModelAdapter("ok")
        adapter("approved prompt")
        assert adapter.received_payloads == ["approved prompt"]


class TestModelAdapterConfig:
    def test_require_api_key_reads_configured_env_name(self) -> None:
        config = ModelAdapterConfig(
            provider="example",
            model="example-model",
            api_key_env_var="EXAMPLE_API_KEY",
        )
        assert config.require_api_key({"EXAMPLE_API_KEY": "secret"}) == "secret"

    def test_require_api_key_strips_whitespace(self) -> None:
        config = ModelAdapterConfig(
            provider="example",
            model="example-model",
            api_key_env_var="EXAMPLE_API_KEY",
        )
        assert config.require_api_key({"EXAMPLE_API_KEY": "  secret  "}) == "secret"

    def test_missing_api_key_raises_clear_error(self) -> None:
        config = ModelAdapterConfig(
            provider="example",
            model="example-model",
            api_key_env_var="EXAMPLE_API_KEY",
        )
        with pytest.raises(ModelAdapterConfigError, match="EXAMPLE_API_KEY"):
            config.require_api_key({})


class TestEnvConfiguredModelAdapter:
    def test_missing_config_fails_before_transport_call(self) -> None:
        calls: list[str] = []

        def transport(payload: str, config: ModelAdapterConfig, api_key: str) -> str:
            calls.append(payload)
            return "should not run"

        adapter = EnvConfiguredModelAdapter(
            ModelAdapterConfig("example", "example-model", "EXAMPLE_API_KEY"),
            transport,
            env={},
        )

        with pytest.raises(ModelAdapterConfigError):
            adapter("approved prompt")

        assert calls == []

    def test_transport_receives_payload_when_configured(self) -> None:
        calls: list[str] = []

        def transport(payload: str, config: ModelAdapterConfig, api_key: str) -> str:
            calls.append(payload)
            assert config.provider == "example"
            assert api_key == "secret"
            return "live response"

        adapter = EnvConfiguredModelAdapter(
            ModelAdapterConfig("example", "example-model", "EXAMPLE_API_KEY"),
            transport,
            env={"EXAMPLE_API_KEY": "secret"},
        )

        assert adapter("approved prompt") == "live response"
        assert calls == ["approved prompt"]
