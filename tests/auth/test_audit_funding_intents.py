import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.funding_intent_log import FundingIntentLog
from app.models.role import Role
from app.services.auth import AuthService
from app.services.internal_backend import InternalAPIService


def _headers(staff) -> dict:
    token = AuthService.create_access_token(
        data={"sub": str(staff.id), "account_type": "erp"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def core_backend(monkeypatch):
    """Stand-in for the core backend. Tests set `.response` / `.error` per case."""

    class Stub:
        response = {"success": True}
        error = None
        calls = []

        def _answer(self, *args):
            self.calls.append(args)
            if self.error:
                raise self.error
            return self.response

    stub = Stub()
    stub.calls = []
    monkeypatch.setattr(
        InternalAPIService,
        "complete_funding_intent",
        staticmethod(lambda txn_id, payload: stub._answer("complete", txn_id, payload)),
    )
    monkeypatch.setattr(
        InternalAPIService,
        "reject_funding_intent",
        staticmethod(lambda txn_id, payload: stub._answer("reject", txn_id, payload)),
    )
    return stub


def _complete(test_client, staff, txn_id, **overrides):
    body = {"bankReference": "NIP/1", "creditedBy": "ignored@example.com", **overrides}
    return test_client.post(
        f"/api/transactions/funding/intents/{txn_id}/complete",
        json=body,
        headers=_headers(staff),
    )


def _reject(test_client, staff, txn_id, reason="No matching credit"):
    return test_client.post(
        f"/api/transactions/funding/intents/{txn_id}/reject",
        json={"rejectedBy": "ignored@example.com", "reason": reason},
        headers=_headers(staff),
    )


def _listing(test_client, staff, **params):
    response = test_client.get(
        "/api/audit/funding-intents", params=params, headers=_headers(staff)
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_completing_an_intent_is_audited_against_the_authenticated_staff(
    test_client, verified_superadmin, core_backend
):
    txn_id = uuid.uuid4()
    funding_account_id = uuid.uuid4()

    response = _complete(
        test_client,
        verified_superadmin,
        txn_id,
        amount=48000,
        overrideReason="Customer sent 48k, not 50k",
        fundingAccountId=str(funding_account_id),
        attachmentUrls=["https://files.example.com/proof.png"],
    )
    assert response.status_code == 200

    (row,) = _listing(test_client, verified_superadmin)
    assert row["action"] == "COMPLETED"
    assert row["status"] == "SUCCESS"
    assert row["transaction_id"] == str(txn_id)
    assert row["bank_reference"] == "NIP/1"
    assert float(row["override_amount"]) == 48000
    assert row["reason"] == "Customer sent 48k, not 50k"
    assert row["funding_account_id"] == str(funding_account_id)
    assert row["attachment_urls"] == ["https://files.example.com/proof.png"]
    # the actor comes from the token, not from the `creditedBy` the client sent
    assert row["staff"]["id"] == str(verified_superadmin.id)


def test_rejecting_an_intent_is_audited_with_its_reason(
    test_client, verified_superadmin, core_backend
):
    txn_id = uuid.uuid4()

    assert _reject(test_client, verified_superadmin, txn_id, "Not on statement").status_code == 200

    (row,) = _listing(test_client, verified_superadmin)
    assert row["action"] == "REJECTED"
    assert row["transaction_id"] == str(txn_id)
    assert row["reason"] == "Not on statement"
    assert row["bank_reference"] is None
    assert row["override_amount"] is None


def test_attempts_the_core_backend_refuses_are_audited_as_failed(
    test_client, verified_superadmin, core_backend
):
    core_backend.error = HTTPException(status_code=409, detail="already settled")
    complete_id, reject_id = uuid.uuid4(), uuid.uuid4()

    # the caller still gets the core backend's error, unchanged
    complete = _complete(test_client, verified_superadmin, complete_id, bankReference="NIP/9")
    assert complete.status_code == 409
    assert complete.json()["detail"] == "already settled"
    assert _reject(test_client, verified_superadmin, reject_id).status_code == 409

    rows = {r["transaction_id"]: r for r in _listing(test_client, verified_superadmin)}
    assert len(rows) == 2

    failed_complete = rows[str(complete_id)]
    assert failed_complete["status"] == "FAILED"
    assert failed_complete["action"] == "COMPLETED"
    assert failed_complete["failure_reason"] == "409: already settled"
    assert failed_complete["bank_reference"] == "NIP/9"
    assert failed_complete["staff"]["id"] == str(verified_superadmin.id)

    failed_reject = rows[str(reject_id)]
    assert failed_reject["status"] == "FAILED"
    assert failed_reject["action"] == "REJECTED"
    assert failed_reject["failure_reason"] == "409: already settled"


def test_an_unexpected_error_is_audited_as_a_500(
    test_client, verified_superadmin, core_backend
):
    core_backend.error = RuntimeError("boom")

    assert _reject(test_client, verified_superadmin, uuid.uuid4()).status_code == 500

    (row,) = _listing(test_client, verified_superadmin)
    assert row["status"] == "FAILED"
    assert row["failure_reason"] == "500: boom"


def test_listing_filters_by_status(test_client, verified_superadmin, core_backend):
    ok_id, failed_id = uuid.uuid4(), uuid.uuid4()
    _reject(test_client, verified_superadmin, ok_id)
    core_backend.error = HTTPException(status_code=409, detail="already settled")
    _reject(test_client, verified_superadmin, failed_id)

    only_ok = _listing(test_client, verified_superadmin, status="SUCCESS")
    assert [r["transaction_id"] for r in only_ok] == [str(ok_id)]
    assert only_ok[0]["failure_reason"] is None

    only_failed = _listing(test_client, verified_superadmin, status="FAILED")
    assert [r["transaction_id"] for r in only_failed] == [str(failed_id)]


@pytest.mark.parametrize(
    "response",
    [{"duplicate": True}, {"data": {"duplicate": True}}],
)
def test_a_retried_completion_is_not_audited_twice(
    test_client, verified_superadmin, core_backend, response
):
    txn_id = uuid.uuid4()
    assert _complete(test_client, verified_superadmin, txn_id).status_code == 200

    core_backend.response = response
    retry = _complete(test_client, verified_superadmin, txn_id)

    assert retry.status_code == 200
    assert retry.json() == response
    assert len(_listing(test_client, verified_superadmin)) == 1


def test_a_failed_audit_write_does_not_mask_the_core_backend_error(
    test_client, verified_superadmin, core_backend, monkeypatch
):
    core_backend.error = HTTPException(status_code=409, detail="already settled")
    original_add = Session.add

    def failing_add(self, instance, *args, **kwargs):
        if isinstance(instance, FundingIntentLog):
            raise SQLAlchemyError("db down")
        return original_add(self, instance, *args, **kwargs)

    monkeypatch.setattr(Session, "add", failing_add)

    response = _reject(test_client, verified_superadmin, uuid.uuid4())

    # still the 409 the staff member needs to see, not a 500 from the audit write
    assert response.status_code == 409


def test_a_failed_audit_write_does_not_fail_the_action(
    test_client, verified_superadmin, core_backend, monkeypatch
):
    original_add = Session.add

    def failing_add(self, instance, *args, **kwargs):
        if isinstance(instance, FundingIntentLog):
            raise SQLAlchemyError("db down")
        return original_add(self, instance, *args, **kwargs)

    monkeypatch.setattr(Session, "add", failing_add)

    response = _complete(test_client, verified_superadmin, uuid.uuid4())

    # the wallet was already credited upstream; the staff member still gets the result
    assert response.status_code == 200
    assert response.json() == core_backend.response


def test_listing_filters_by_action_and_search(
    test_client, verified_superadmin, core_backend
):
    completed_id, rejected_id = uuid.uuid4(), uuid.uuid4()
    _complete(test_client, verified_superadmin, completed_id, bankReference="NIP/ABC")
    _reject(test_client, verified_superadmin, rejected_id)

    only_rejected = _listing(test_client, verified_superadmin, action="REJECTED")
    assert [r["transaction_id"] for r in only_rejected] == [str(rejected_id)]

    by_reference = _listing(test_client, verified_superadmin, search="nip/abc")
    assert [r["transaction_id"] for r in by_reference] == [str(completed_id)]

    by_staff_code = _listing(
        test_client, verified_superadmin, search=verified_superadmin.staff_code
    )
    assert len(by_staff_code) == 2

    assert _listing(test_client, verified_superadmin, search="nobody") == []


def test_listing_is_newest_first_and_paginated(
    test_client, verified_superadmin, core_backend
):
    ids = [uuid.uuid4() for _ in range(3)]
    for txn_id in ids:
        _reject(test_client, verified_superadmin, txn_id)

    first_page = _listing(test_client, verified_superadmin, limit=2, page=1)
    second_page = _listing(test_client, verified_superadmin, limit=2, page=2)

    assert len(first_page) == 2
    assert len(second_page) == 1
    seen = [r["transaction_id"] for r in first_page + second_page]
    assert sorted(seen) == sorted(str(i) for i in ids)


def test_listing_requires_view_audit_logs_permission(test_client, db_session):
    role = Role(name="NoPerms")
    db_session.add(role)
    db_session.commit()
    staff = ERPUser(
        first_name="Test",
        last_name="Staff",
        email="noperm-fi@example.com",
        hashed_password=Hasher.get_password_hash("@Password123"),
        verified=True,
        role_id=role.id,
    )
    db_session.add(staff)
    db_session.commit()

    denied = test_client.get("/api/audit/funding-intents", headers=_headers(staff))
    assert denied.status_code == 403
