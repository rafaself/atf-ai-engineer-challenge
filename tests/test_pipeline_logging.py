"""Temporary diagnostics must preserve correlation and avoid disclosing secrets."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from emporio_music.diagnostics import failure
from emporio_music.domain.chat import ChatRequest, ChatResponse
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.errors import ConfigurationError
from emporio_music_api.app import create_app
from fastapi.testclient import TestClient


def test_token_retrieval_failure_has_a_safe_provider_hint() -> None:
    class TokenRetrievalError(Exception):
        def __init__(self) -> None:
            self.provider = "private-profile-name"
            self.error_msg = "private token detail"

    error = TokenRetrievalError()

    summary = failure(error)

    assert summary["hint"] == (
        "Check the configured AWS token provider and its authentication state."
    )
    assert "private-profile-name" not in json.dumps(summary)
    assert "private token detail" not in json.dumps(summary)


def test_concurrent_http_logs_are_correlated_and_redact_active_credentials(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    demo_customer: dict[str, int],
) -> None:
    monkeypatch.setenv("PIPELINE_LOGS", "1")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret-for-test-only")
    monkeypatch.setattr(logging.getLogger("emporio.pipeline"), "propagate", True)

    class Service:
        async def chat(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            return ChatResponse(
                answer=request.message,
                session_id=UUID("00000000-0000-4000-8000-000000000001"),
            )

    with TestClient(create_app(Service())) as client:
        monkeypatch.setenv("PIPELINE_LOGS", "0")
        assert (
            client.post(
                "/api/chat", json={**demo_customer, "message": "secret-for-test-only"}
            ).status_code
            == 200
        )
        assert not [r for r in caplog.records if r.name == "emporio.pipeline"]
        monkeypatch.setenv("PIPELINE_LOGS", "1")

        def send(index: int) -> int:
            return client.post(
                "/api/chat",
                json={
                    **demo_customer,
                    "message": f"{index} secret-for-test-only\nnext line",
                },
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert list(pool.map(send, range(2))) == [200, 200]
    entries = [
        json.loads(r.getMessage())
        for r in caplog.records
        if r.name == "emporio.pipeline"
    ]
    requests = [e for e in entries if e["event"] == "http.request"]
    responses = [e for e in entries if e["event"] == "http.response"]
    assert len({e["request_id"] for e in requests}) == 2
    assert {e["request_id"] for e in requests} == {e["request_id"] for e in responses}
    assert all("secret-for-test-only" not in json.dumps(e) for e in entries)
    assert all(set(e) == {"event", "request_id"} for e in requests)


def test_failure_logs_show_cause_type_without_raw_exception_body(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    demo_customer: dict[str, int],
) -> None:
    monkeypatch.setenv("PIPELINE_LOGS", "1")
    monkeypatch.setattr(logging.getLogger("emporio.pipeline"), "propagate", True)

    class Service:
        async def chat(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            try:
                raise RuntimeError("private provider body and credential contents")
            except RuntimeError as exc:
                raise ConfigurationError("private settings") from exc

    with TestClient(create_app(Service()), raise_server_exceptions=False) as client:
        assert (
            client.post(
                "/api/chat", json={**demo_customer, "message": "Olá"}
            ).status_code
            == 503
        )
    entries = [
        json.loads(r.getMessage())
        for r in caplog.records
        if r.name == "emporio.pipeline"
    ]
    errors = [e for e in entries if e["event"] == "http.failure"]
    assert errors[0]["causes"] == ["ConfigurationError", "RuntimeError"]
    assert "private" not in json.dumps(entries)
