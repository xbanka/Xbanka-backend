"""Staff are told when a customer declares a bank transfer ("I have sent").

Who is told is decided by permission (finance:adjust_balance,
finance:approve_payments, finance:reject_payments), the same way payout and
rate-change notifications already work.
"""

from uuid import uuid4

import pytest

from app.api.v1.routes import internal as internal_routes
from app.api.v1.routes import transaction as transaction_routes
from app.core import email, email_templates
from app.core.enums import NotificationReferenceTypeEnum, NotificationStatusEnum
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notifications import Notification
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permissions import RolePermissions
from app.models.user_permissions import UserPermissions
from app.services.erp_user import ERPService
from app.services.websocket_manager import notification_manager

KEY = "test-internal-key"
URL = "/api/internal/funding-intents/declared"
ADJUST = "finance:adjust_balance"
APPROVE = "finance:approve_payments"
REJECT = "finance:reject_payments"
UNRELATED = "transactions:view"


@pytest.fixture(autouse=True)
def _no_network(mocker):
    """No websocket push and no real email; capture what Resend would get."""
    mocker.patch.object(notification_manager, "send_to_user_threadsafe")
    mocker.patch.object(ERPService, "_push_notification")
    sent = []
    mocker.patch.object(
        email.resend.Emails,
        "send",
        side_effect=lambda params: sent.append(params) or {"id": "re_test"},
    )
    mocker.patch("app.utils.auth.settings.INTERNAL_KEY", KEY)
    return sent


@pytest.fixture
def sent(_no_network):
    return _no_network


@pytest.fixture
def permissions(db_session):
    perms = {}
    for name in (ADJUST, APPROVE, REJECT, UNRELATED):
        perm = Permission(name=name, category=name.split(":")[0])
        db_session.add(perm)
        perms[name] = perm
    db_session.commit()
    for perm in perms.values():
        db_session.refresh(perm)
    return perms


def _role(db_session, permissions, name, granted):
    role = Role(name=name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    db_session.add_all(
        [RolePermissions(role_id=role.id, permission_id=permissions[p].id) for p in granted]
    )
    db_session.commit()
    return role


def _staff(db_session, role, first_name):
    user = ERPUser(
        first_name=first_name,
        last_name="Staff",
        email=f"{first_name.lower()}-{uuid4().hex[:6]}@example.com",
        hashed_password=Hasher.get_password_hash("@Password123"),
        verified=True,
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def team(db_session, permissions):
    """One person per interesting case."""
    finance = _role(db_session, permissions, "Finance", [ADJUST, APPROVE, REJECT])
    approver = _role(db_session, permissions, "Approver", [APPROVE])
    viewer = _role(db_session, permissions, "Viewer", [UNRELATED])
    super_admin = _role(db_session, permissions, "Super Admin", [])
    return {
        "finance": _staff(db_session, finance, "Fin"),  # holds all three
        "approver": _staff(db_session, approver, "Appr"),  # holds one
        "viewer": _staff(db_session, viewer, "View"),  # holds none of them
        "super": _staff(db_session, super_admin, "Boss"),
        "finance_role": finance,
    }


def _payload(**overrides):
    body = {
        "transactionId": str(uuid4()),
        "reference": "MANUAL-123-ABC",
        "amount": 5000,
        "customerName": "Ada Tester",
        "customerXbId": "XB-E2E1",
        "registeredFundingAccounts": [],
    }
    body.update(overrides)
    return body


def _post(client, body, key=KEY):
    headers = {"x-internal-key": key} if key is not None else {}
    return client.post(URL, json=body, headers=headers)


# ---------------------------------------------------------------- who is told


def test_any_of_the_permissions_qualifies_and_each_person_is_listed_once(
    db_session, team
):
    users = ERPService.get_users_with_any_permission(
        db_session, internal_routes.FUNDING_INTENT_PERMISSIONS
    )

    ids = [u.id for u in users]
    assert len(ids) == len(set(ids))  # Finance holds three, but appears once
    assert team["finance"].id in ids
    assert team["approver"].id in ids  # one of the three is enough
    assert team["super"].id in ids  # Super Admin holds everything
    assert team["viewer"].id not in ids


def test_a_per_user_deny_removes_someone_their_role_would_include(
    db_session, permissions, team
):
    db_session.add_all(
        [
            UserPermissions(user_id=team["approver"].id, permission_id=permissions[APPROVE].id, is_active=False),
        ]
    )
    db_session.commit()

    ids = [
        u.id
        for u in ERPService.get_users_with_any_permission(
            db_session, internal_routes.FUNDING_INTENT_PERMISSIONS
        )
    ]
    assert team["approver"].id not in ids


def test_a_per_user_grant_adds_someone_their_role_would_not(
    db_session, permissions, team
):
    db_session.add(
        UserPermissions(user_id=team["viewer"].id, permission_id=permissions[REJECT].id, is_active=True)
    )
    db_session.commit()

    ids = [
        u.id
        for u in ERPService.get_users_with_any_permission(
            db_session, internal_routes.FUNDING_INTENT_PERMISSIONS
        )
    ]
    assert team["viewer"].id in ids


# ----------------------------------------------------------------- endpoint


@pytest.mark.parametrize("key", [None, "", "wrong-key"])
def test_the_endpoint_rejects_a_missing_or_wrong_key(test_client, db_session, team, sent, key):
    response = _post(test_client, _payload(), key=key)

    assert response.status_code == 403
    assert db_session.query(Notification).count() == 0
    assert sent == []


def test_the_endpoint_is_closed_when_no_key_is_configured(mocker, test_client, db_session, team):
    mocker.patch("app.utils.auth.settings.INTERNAL_KEY", "")

    assert _post(test_client, _payload(), key="").status_code == 403
    assert db_session.query(Notification).count() == 0


def test_staff_with_the_permissions_get_an_in_app_notification(test_client, db_session, team):
    body = _payload()

    response = _post(test_client, body)

    assert response.status_code == 202
    assert response.json() == {"notified": 3, "duplicate": False}
    rows = db_session.query(Notification).all()
    assert {n.user_id for n in rows} == {team["finance"].id, team["approver"].id, team["super"].id}
    for n in rows:
        assert n.reference_type == NotificationReferenceTypeEnum.FUNDING_INTENT
        assert str(n.reference_id) == body["transactionId"]
        assert float(n.amount) == 5000
        assert len(n.message) <= 200
        assert "Ada Tester" in n.message


def test_they_are_also_emailed_and_nobody_else_is(test_client, team, sent):
    _post(test_client, _payload())

    addressed = {to for params in sent for to in params["to"]}
    assert team["finance"].email in addressed
    assert team["approver"].email in addressed
    assert team["viewer"].email not in addressed
    subjects = {params["subject"] for params in sent}
    assert subjects == {"Transfer to confirm: ₦5,000.00"}


def test_the_email_button_opens_the_funding_requests_tab(test_client, team, sent):
    _post(test_client, _payload())

    assert sent
    for params in sent:
        assert "/finance?tab=funding" in params["html"]
        assert "//finance" not in params["html"].replace("://", "")  # no doubled slash


def test_a_retried_call_does_not_notify_twice(test_client, db_session, team, sent):
    body = _payload()
    _post(test_client, body)
    emails_after_first = len(sent)

    again = _post(test_client, body)

    assert again.status_code == 202
    assert again.json() == {"notified": 0, "duplicate": True}
    assert db_session.query(Notification).count() == 3
    assert len(sent) == emails_after_first


def test_nobody_holding_the_permissions_is_not_an_error(test_client, db_session, permissions, sent):
    # roles exist but none grants the funding permissions
    response = _post(test_client, _payload())

    assert response.status_code == 202
    assert response.json() == {"notified": 0, "duplicate": False}
    assert db_session.query(Notification).count() == 0
    assert sent == []


def test_a_long_customer_name_cannot_overflow_the_message_column(test_client, db_session, team):
    response = _post(test_client, _payload(customerName="N" * 200))

    assert response.status_code == 202
    assert all(len(n.message) <= 200 for n in db_session.query(Notification))


@pytest.mark.parametrize("bad", [{"amount": 0}, {"amount": -5}, {"transactionId": "nope"}, {"reference": ""}])
def test_a_malformed_payload_is_rejected(test_client, team, bad):
    assert _post(test_client, _payload(**bad)).status_code == 422


# -------------------------------------------------------------------- email


def test_the_email_escapes_customer_supplied_text():
    html, text = email_templates.funding_intent_declared_email(
        staff_first_name="Fin",
        customer_name="<script>alert(1)</script>",
        customer_xb_id="XB-1",
        amount=1234.5,
        reference='"><img src=x>',
        review_url="https://erp.example.com",
    )

    assert "<script>" not in html
    assert "<img src=x>" not in html
    assert "&lt;script&gt;" in html
    assert "₦1,234.50" in html
    assert "₦1,234.50" in text
    assert "https://erp.example.com" in html


# ------------------------------------------------------------ clearing alert


def test_completing_or_rejecting_clears_the_alert(db_session, team):
    transaction_id = uuid4()
    ERPService.new_notification(
        db_session,
        recipients=[team["finance"]],
        message="waiting",
        reference_type=NotificationReferenceTypeEnum.FUNDING_INTENT,
        reference_id=transaction_id,
    )
    other = ERPService.new_notification(
        db_session,
        recipients=[team["finance"]],
        message="another intent",
        reference_type=NotificationReferenceTypeEnum.FUNDING_INTENT,
        reference_id=uuid4(),
    )

    transaction_routes._resolve_funding_intent_alert(db_session, transaction_id)

    by_ref = {n.reference_id: n.status for n in db_session.query(Notification)}
    assert by_ref[transaction_id] == NotificationStatusEnum.RESOLVED
    assert by_ref[other[0].reference_id] == NotificationStatusEnum.ACTIVE


def test_a_failure_clearing_the_alert_never_surfaces(mocker, db_session):
    mocker.patch.object(
        transaction_routes.ERPService,
        "resolve_notifications_for_reference",
        side_effect=RuntimeError("db hiccup"),
    )

    # the credit already happened; this must not raise
    transaction_routes._resolve_funding_intent_alert(db_session, uuid4())
