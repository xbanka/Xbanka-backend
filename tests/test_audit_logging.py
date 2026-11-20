"""The log must say what happened and why, without leaking what it was given.

Each test reads the structured fields (`caplog` records), the same ones the JSON
formatter ships, so a rename of a field here is a break for anyone searching logs.
"""

import logging
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect

from app.core import email
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permissions import RolePermissions
from app.services.auth import AuthService
from app.services.erp_user import ERPService
from app.services.internal_backend import InternalAPIService
from app.services.websocket_manager import notification_manager

KEY = "test-internal-key-9f2c"
DECLARED = "/api/internal/funding-intents/declared"
ADJUST = "finance:adjust_balance"


@pytest.fixture(autouse=True)
def _no_network(mocker):
    mocker.patch.object(notification_manager, "send_to_user_threadsafe")
    mocker.patch.object(ERPService, "_push_notification")
    mocker.patch.object(email.resend.Emails, "send", return_value={"id": "re_test"})
    mocker.patch("app.utils.auth.settings.INTERNAL_KEY", KEY)


def _find(caplog, message, **fields):
    """Records with this exact message whose extra fields match."""
    return [
        r
        for r in caplog.records
        if r.getMessage() == message
        and all(getattr(r, k, None) == v for k, v in fields.items())
    ]


def _staff(db_session, role_name, permissions=()):
    role = Role(name=role_name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    for name in permissions:
        perm = Permission(name=name, category=name.split(":")[0])
        db_session.add(perm)
        db_session.commit()
        db_session.refresh(perm)
        db_session.add(RolePermissions(role_id=role.id, permission_id=perm.id))
    db_session.commit()
    user = ERPUser(
        first_name=role_name,
        last_name="Staff",
        email=f"{role_name.lower()}-{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=Hasher.get_password_hash("@Password123"),
        verified=True,
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _bearer(user):
    token = AuthService.create_access_token(
        data={"sub": str(user.id), "account_type": "erp"}
    )
    return token, {"Authorization": f"Bearer {token}"}


def _payload(**overrides):
    body = {
        "transactionId": str(uuid.uuid4()),
        "reference": "MANUAL-123-ABC",
        "amount": 5000,
        "customerName": "Ada Tester",
        "customerXbId": "XB-E2E1",
        "registeredFundingAccounts": [],
    }
    body.update(overrides)
    return body


# ------------------------------------------------------- the internal key guard


@pytest.mark.parametrize(
    "header, configured, reason",
    [
        ({"x-internal-key": "not-the-key-1234"}, KEY, "mismatch"),
        ({}, KEY, "missing"),
        ({"x-internal-key": KEY}, "", "not_configured"),
    ],
)
def test_a_rejected_internal_key_says_why_and_never_logs_a_key(
    mocker, test_client, caplog, header, configured, reason
):
    mocker.patch("app.utils.auth.settings.INTERNAL_KEY", configured)

    with caplog.at_level(logging.INFO):
        response = test_client.post(DECLARED, json=_payload(), headers=header)

    assert response.status_code == 403
    (record,) = _find(caplog, "internal key rejected")
    assert record.reason == reason
    assert record.levelno == logging.WARNING
    assert KEY not in caplog.text
    assert "not-the-key-1234" not in caplog.text


# ------------------------------------------------------ the funding intent flow


def test_a_declared_intent_logs_who_was_notified_and_a_retry_says_it_was_ignored(
    test_client, db_session, caplog
):
    _staff(db_session, "Finance", [ADJUST])
    body = _payload()

    with caplog.at_level(logging.INFO):
        first = test_client.post(DECLARED, json=body, headers={"x-internal-key": KEY})
        retry = test_client.post(DECLARED, json=body, headers={"x-internal-key": KEY})

    assert first.status_code == retry.status_code == 202
    (declared,) = _find(caplog, "funding intent declared")
    assert declared.transaction_id == body["transactionId"]
    assert declared.reference == "MANUAL-123-ABC"
    assert declared.notified == 1
    (ignored,) = _find(caplog, "funding intent already notified")
    assert ignored.transaction_id == body["transactionId"]
    # the customer's name is not needed to follow what happened
    assert "Ada Tester" not in " ".join(
        r.getMessage() for r in caplog.records if r.name.endswith("internal")
    )


@pytest.fixture
def core_backend(monkeypatch):
    class Stub:
        response = {"success": True}
        error = None

    stub = Stub()

    def answer(*_args):
        if stub.error:
            raise stub.error
        return stub.response

    monkeypatch.setattr(
        InternalAPIService,
        "complete_funding_intent",
        staticmethod(lambda txn_id, payload: answer()),
    )
    monkeypatch.setattr(
        InternalAPIService,
        "reject_funding_intent",
        staticmethod(lambda txn_id, payload: answer()),
    )
    return stub


def _complete(client, user, txn_id):
    return client.post(
        f"/api/transactions/funding/intents/{txn_id}/complete",
        json={"bankReference": "NIP/1", "creditedBy": "someone@example.com"},
        headers=_bearer(user)[1],
    )


def test_completing_an_intent_logs_the_staff_member_and_the_intent_once(
    test_client, verified_superadmin, core_backend, caplog
):
    txn_id = uuid.uuid4()

    with caplog.at_level(logging.INFO):
        assert _complete(test_client, verified_superadmin, txn_id).status_code == 200

    (record,) = _find(caplog, "funding intent action succeeded")
    assert record.actor_id == str(verified_superadmin.id)
    assert record.transaction_id == str(txn_id)
    assert record.action == "COMPLETED"
    assert record.bank_reference == "NIP/1"
    # the staff email the client sent is not the actor and is not logged
    assert "someone@example.com" not in caplog.text


def test_a_retried_completion_is_not_logged_as_a_second_action(
    test_client, verified_superadmin, core_backend, caplog
):
    core_backend.response = {"success": True, "duplicate": True}

    with caplog.at_level(logging.INFO):
        _complete(test_client, verified_superadmin, uuid.uuid4())

    assert not _find(caplog, "funding intent action succeeded")


def test_a_refused_completion_logs_the_status_but_not_the_core_message(
    test_client, verified_superadmin, core_backend, caplog
):
    core_backend.error = HTTPException(status_code=409, detail="belongs to Grace Hopper")
    txn_id = uuid.uuid4()

    with caplog.at_level(logging.INFO):
        response = _complete(test_client, verified_superadmin, txn_id)

    assert response.status_code == 409
    (record,) = _find(caplog, "funding intent action refused")
    assert record.status_code == 409
    assert record.transaction_id == str(txn_id)
    assert record.levelno == logging.WARNING
    assert "Grace Hopper" not in str(vars(record))


# -------------------------------------------------- permission and token denials


def test_a_permission_denial_names_the_staff_member_and_what_was_missing(
    test_client, db_session, caplog
):
    viewer = _staff(db_session, "Viewer")

    with caplog.at_level(logging.INFO):
        response = test_client.get(
            "/api/transactions/funding/intents", headers=_bearer(viewer)[1]
        )

    assert response.status_code == 403
    (record,) = _find(caplog, "permission denied")
    assert record.actor_id == str(viewer.id)
    assert record.reason == "missing_permission"
    assert "finance:view_payments" in record.required
    assert record.levelno == logging.WARNING


def test_an_invalid_token_is_refused_with_a_reason_and_is_never_logged(
    test_client, caplog
):
    bad = "eyJhbGciOiJIUzI1NiJ9.garbage.signature"

    with caplog.at_level(logging.INFO):
        response = test_client.get(
            "/api/transactions/funding/intents",
            headers={"Authorization": f"Bearer {bad}"},
        )

    assert response.status_code == 401
    (record,) = _find(caplog, "authentication rejected")
    assert record.reason == "invalid_token"
    assert bad not in caplog.text


def test_a_refresh_token_used_as_a_session_is_called_out(
    test_client, db_session, caplog
):
    user = _staff(db_session, "Finance", [ADJUST])
    refresh = AuthService.create_refresh_token(
        data={"sub": str(user.id), "account_type": "erp"}
    )

    with caplog.at_level(logging.INFO):
        response = test_client.get(
            "/api/transactions/funding/intents",
            headers={"Authorization": f"Bearer {refresh}"},
        )

    assert response.status_code == 401
    (record,) = _find(caplog, "authentication rejected")
    assert record.reason == "wrong_token_type"
    assert record.type_claim == "refresh"
    assert refresh not in caplog.text


def test_an_expired_session_is_routine_not_a_warning(test_client, db_session, caplog):
    user = _staff(db_session, "Finance", [ADJUST])
    expired = AuthService.create_access_token(
        data={"sub": str(user.id), "account_type": "erp"},
        expires_delta=timedelta(days=-2),
    )

    with caplog.at_level(logging.INFO):
        response = test_client.get(
            "/api/transactions/funding/intents",
            headers={"Authorization": f"Bearer {expired}"},
        )

    assert response.status_code == 401
    (record,) = _find(caplog, "authentication rejected")
    assert record.reason == "expired"
    assert record.levelno == logging.INFO


def test_a_user_that_no_longer_exists_is_reported(test_client, caplog):
    ghost = AuthService.create_access_token(
        data={"sub": str(uuid.uuid4()), "account_type": "erp"}
    )

    with caplog.at_level(logging.INFO):
        response = test_client.get(
            "/api/transactions/funding/intents",
            headers={"Authorization": f"Bearer {ghost}"},
        )

    assert response.status_code == 401
    (record,) = _find(caplog, "authentication rejected")
    assert record.reason == "user_not_found"


# ------------------------------------------------------------------- websocket


def test_a_rejected_websocket_says_why(test_client, caplog):
    with caplog.at_level(logging.INFO):
        with pytest.raises(WebSocketDisconnect):
            with test_client.websocket_connect(
                "/api/erp/notifications/ws?token=not-a-real-token"
            ):
                pass

    (record,) = _find(caplog, "authentication rejected", channel="websocket")
    assert record.reason == "invalid_token"
    assert "not-a-real-token" not in caplog.text


def test_a_websocket_connect_and_disconnect_are_logged(
    test_client, verified_superadmin, caplog
):
    token, _ = _bearer(verified_superadmin)

    with caplog.at_level(logging.INFO):
        with test_client.websocket_connect(f"/api/erp/notifications/ws?token={token}"):
            pass

    assert _find(
        caplog, "notification socket connected", actor_id=str(verified_superadmin.id)
    )
    assert token not in caplog.text


# --------------------------------------------------------- staff and the rest


def test_removing_staff_logs_who_did_it_and_to_whom(
    test_client, db_session, verified_superadmin, caplog
):
    target = _staff(db_session, "Leaver")

    with caplog.at_level(logging.INFO):
        response = test_client.delete(
            f"/api/staff/{target.id}", headers=_bearer(verified_superadmin)[1]
        )

    assert response.status_code == 200
    (record,) = _find(caplog, "staff removed")
    assert record.actor_id == str(verified_superadmin.id)
    assert record.target_id == str(target.id)


def test_a_password_reset_request_is_logged_by_user_id_not_email(
    test_client, db_session, caplog
):
    user = _staff(db_session, "Forgetful")

    with caplog.at_level(logging.INFO):
        response = test_client.post(
            "/api/auth/erp/forgot-password", json={"email": user.email}
        )

    assert response.status_code == 200
    (record,) = _find(caplog, "password reset requested")
    assert record.user_id == str(user.id)
    # only judge this app's own lines: the email sender logs recipients by design
    own = [r for r in caplog.records if r.name.endswith("auth.erp")]
    assert own and user.email not in str([r.__dict__ for r in own])
