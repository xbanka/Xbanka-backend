import json
import logging

from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter, REDACTED, RedactionFilter, redact
from app.main import app


def test_redact_masks_sensitive_dict_keys():
    data = {"email": "a@b.com", "password": "hunter2", "nested": {"api_key": "k"}}

    result = redact(data)

    assert result["email"] == "a@b.com"
    assert result["password"] == REDACTED
    assert result["nested"]["api_key"] == REDACTED


def test_redact_masks_secrets_in_text():
    text = "failed: password=hunter2 Authorization: Bearer abc.def.ghi"

    result = redact(text)

    assert "hunter2" not in result
    assert "abc.def.ghi" not in result


def test_redaction_filter_masks_extra_fields():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
    record.account_number = "0123456789"
    record.payload = {"token": "secret-token"}

    RedactionFilter().filter(record)

    assert record.account_number == REDACTED
    assert record.payload["token"] == REDACTED


def test_json_formatter_outputs_extra_fields():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello %s", ("x",), None)
    record.user_id = "42"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "hello x"
    assert payload["level"] == "INFO"
    assert payload["user_id"] == "42"


def test_response_has_request_id_and_request_is_logged(test_client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = test_client.get("/", headers={"X-Request-ID": "req-123"})

    assert response.headers["X-Request-ID"] == "req-123"
    record = next(r for r in caplog.records if r.name == "app.request")
    assert record.status == 200
    assert record.path == "/"
    assert record.duration_ms >= 0


def test_request_id_generated_when_absent(test_client):
    response = test_client.get("/")

    assert response.headers["X-Request-ID"]


def test_validation_error_log_omits_submitted_values(test_client, caplog):
    with caplog.at_level(logging.WARNING):
        response = test_client.post(
            "/api/auth/erp/login",
            json={"email": 123, "password": "SuperSecret!1", "extra": object.__name__},
        )

    assert response.status_code == 422
    assert "SuperSecret!1" not in caplog.text


def test_unhandled_exception_returns_request_id_without_internals(caplog):
    def boom():
        raise RuntimeError("internal detail")

    app.add_api_route("/__test_boom", boom)
    client = TestClient(app, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR):
        response = client.get("/__test_boom", headers={"X-Request-ID": "req-boom"})

    assert response.status_code == 500
    body = response.json()
    assert body["request_id"] == "req-boom"
    assert "internal detail" not in response.text
    assert "internal detail" in caplog.text
