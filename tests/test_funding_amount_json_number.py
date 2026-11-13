"""The core validates `amount` with @IsNumber (no string coercion), so the ERP must
forward it as a JSON number. pydantic's model_dump(mode="json") turns Decimal into a
string, which the core rejected with "amount must be a number conforming to the
specified constraints"."""

import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

CREDIT_URL = "/api/transactions/funding/credit"
INTENT_ID = "3f2c8a56-7d52-4b1e-9a43-0d5b1f2c9e77"
COMPLETE_URL = f"/api/transactions/funding/intents/{INTENT_ID}/complete"
ACCOUNT_ID = "7c0c1d2e-5b4a-4c53-9d57-0f3f0f4a1b11"


def _mock_response(json_data=None):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = json_data if json_data is not None else {}
    return response


def _sent_body(request):
    """The JSON body the core would receive, as it appears on the wire."""
    request.assert_called_once()
    return json.loads(json.dumps(request.call_args.kwargs["json"]))


@pytest.mark.parametrize(
    "amount, wire",
    [(1000, "1000"), (1.5, "1.5"), (0.1, "0.1"), (1000.5, "1000.5"), (2500.55, "2500.55")],
)
def test_credit_sends_amount_as_a_json_number(mocker, super_client, amount, wire):
    request = mocker.patch("requests.request", return_value=_mock_response({"ok": True}))

    response = super_client.post(
        CREDIT_URL,
        json={
            "fundingAccountId": ACCOUNT_ID,
            "amount": amount,
            "reference": "REF-1",
            "creditedBy": "ops@xbankang.com",
        },
    )

    assert response.status_code == 200
    assert request.call_args.args[1].endswith("/internal/funding/credit")
    body = _sent_body(request)
    assert not isinstance(body["amount"], str)
    assert body["amount"] == amount
    # no float noise such as 0.10000000000000001, and whole numbers stay whole
    assert json.dumps(request.call_args.kwargs["json"]["amount"]) == wire


@pytest.mark.parametrize(
    "amount, wire",
    [
        (1000.555, "1000.55"),  # trimmed, not rounded up
        (0.019, "0.01"),
        (1.999, "1.99"),
        ("2.50999999", "2.5"),
        (1234.5, "1234.5"),  # nothing to trim
    ],
)
def test_credit_trims_extra_decimal_places(mocker, super_client, amount, wire):
    request = mocker.patch("requests.request", return_value=_mock_response({"ok": True}))

    response = super_client.post(
        CREDIT_URL,
        json={
            "fundingAccountId": ACCOUNT_ID,
            "amount": amount,
            "reference": "REF-1",
            "creditedBy": "ops@xbankang.com",
        },
    )

    assert response.status_code == 200
    assert json.dumps(request.call_args.kwargs["json"]["amount"]) == wire


@pytest.mark.parametrize("amount", [0, -5, 0.001, 0.009, "0.0099", 1e40])
def test_credit_rejects_amounts_below_a_cent_or_too_large(mocker, super_client, amount):
    request = mocker.patch("requests.request")

    response = super_client.post(
        CREDIT_URL,
        json={
            "fundingAccountId": ACCOUNT_ID,
            "amount": amount,
            "reference": "REF-1",
            "creditedBy": "ops@xbankang.com",
        },
    )

    assert response.status_code == 422
    request.assert_not_called()


def test_complete_intent_trims_extra_decimal_places(mocker, super_client):
    request = mocker.patch("requests.request", return_value=_mock_response({"ok": True}))

    response = super_client.post(
        COMPLETE_URL,
        json={
            "bankReference": "BANK-REF-1",
            "creditedBy": "ops@xbankang.com",
            "amount": 99.999,
            "overrideReason": "Bank received a different amount",
        },
    )

    assert response.status_code == 200
    assert json.dumps(request.call_args.kwargs["json"]["amount"]) == "99.99"


def test_complete_intent_rejects_amount_below_a_cent(mocker, super_client):
    request = mocker.patch("requests.request")

    response = super_client.post(
        COMPLETE_URL,
        json={
            "bankReference": "BANK-REF-1",
            "creditedBy": "ops@xbankang.com",
            "amount": 0.004,
            "overrideReason": "Bank received a different amount",
        },
    )

    assert response.status_code == 422
    request.assert_not_called()


def test_complete_intent_override_sends_amount_as_a_json_number(mocker, super_client):
    request = mocker.patch("requests.request", return_value=_mock_response({"ok": True}))

    response = super_client.post(
        COMPLETE_URL,
        json={
            "bankReference": "BANK-REF-1",
            "creditedBy": "ops@xbankang.com",
            "amount": 1500.75,
            "overrideReason": "Bank received a different amount",
        },
    )

    assert response.status_code == 200
    assert request.call_args.args[1].endswith(f"/internal/funding/intents/{INTENT_ID}/complete")
    body = _sent_body(request)
    assert not isinstance(body["amount"], str)
    assert body["amount"] == 1500.75
    assert body["overrideReason"] == "Bank received a different amount"


def test_complete_intent_without_amount_omits_it(mocker, super_client):
    request = mocker.patch("requests.request", return_value=_mock_response({"ok": True}))

    response = super_client.post(
        COMPLETE_URL,
        json={"bankReference": "BANK-REF-1", "creditedBy": "ops@xbankang.com"},
    )

    assert response.status_code == 200
    body = _sent_body(request)
    assert "amount" not in body
    assert body["bankReference"] == "BANK-REF-1"


def test_python_mode_dump_keeps_decimal():
    """Only the JSON dump changes; the audit log still receives an exact Decimal."""
    from app.schemas.transactions import FundingIntentCompleteRequest

    payload = FundingIntentCompleteRequest(
        bankReference="BANK-REF-1",
        creditedBy="ops@xbankang.com",
        amount="0.10",
        overrideReason="different amount",
    )

    assert payload.amount == Decimal("0.10")
    assert isinstance(payload.model_dump()["amount"], Decimal)
    assert payload.model_dump(mode="json")["amount"] == 0.1
