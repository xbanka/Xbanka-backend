from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.core.enums import Permission
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notifications import Notification
from app.models.permission import Permission as PermissionModel
from app.models.rate_approval_request import RateApprovalRequest
from app.models.rate_change_log import RateChangeLog
from app.models.role import Role
from app.models.role_permissions import RolePermissions
from app.services.auth import AuthService


def _mock_response(status_code=200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else {}
    return response


@pytest.fixture(autouse=True)
def mock_rates_state_fetch(mocker):
    """Building a proposal snapshot always fetches current assets/segments from
    the internal rates API first; stub that out so no test needs network."""
    mocker.patch(
        "app.services.rates.requests.get",
        return_value=_mock_response(200, {"data": []}),
    )


def _make_role(db_session, name: str, allowed=()) -> Role:
    role = Role(name=name)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    for perm in allowed:
        db_session.add(RolePermissions(role_id=role.id, permission_id=perm.id, is_allowed=True))
    db_session.commit()
    return role


def _make_staff(db_session, role: Role, email: str) -> ERPUser:
    staff = ERPUser(
        first_name="Rates",
        last_name="Staff",
        email=email,
        hashed_password=Hasher.get_password_hash("@Password123"),
        verified=True,
        role_id=role.id,
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff


def _headers(staff: ERPUser) -> dict:
    token = AuthService.create_access_token(data={"sub": str(staff.id), "account_type": "erp"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def override_permission(db_session) -> PermissionModel:
    row = PermissionModel(
        name=Permission.RATE_CHANGE_OVERRIDE.value,
        category="rates",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


@pytest.fixture
def manager_without_override(db_session) -> ERPUser:
    role = _make_role(db_session, "Rates Manager")
    return _make_staff(db_session, role, "no.override@example.com")


@pytest.fixture
def manager_with_override(db_session, override_permission) -> ERPUser:
    role = _make_role(db_session, "Rates Admin", allowed=[override_permission])
    return _make_staff(db_session, role, "override@example.com")


# ---------------------------------------------------------------------------
# update_crypto_rate (PUT /rates/crypto/{rate_id})
# ---------------------------------------------------------------------------


def test_update_crypto_rate_without_override_creates_pending_proposal(
    mocker, test_client, db_session, manager_without_override
):
    mock_put = mocker.patch("app.services.rates.requests.put")

    response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 1.5, "sellFeeValue": 2.0},
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Rate change proposal submitted successfully."
    mock_put.assert_not_called()

    proposals = db_session.query(RateApprovalRequest).all()
    assert len(proposals) == 1
    assert proposals[0].status == "PENDING"
    assert db_session.query(RateChangeLog).count() == 0


def test_update_crypto_rate_with_override_applies_immediately(
    mocker, test_client, db_session, manager_with_override
):
    mock_put = mocker.patch(
        "app.services.rates.requests.put", return_value=_mock_response(200, {"ok": True})
    )

    response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 1.5, "sellFeeValue": 2.0},
        headers=_headers(manager_with_override),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Rate change applied successfully."
    mock_put.assert_called_once()

    proposals = db_session.query(RateApprovalRequest).all()
    assert len(proposals) == 1
    assert proposals[0].status == "APPROVED"
    assert db_session.query(RateChangeLog).count() == 1


def test_super_admin_bypasses_proposal_flow_without_explicit_permission(
    mocker, test_client, verified_superadmin
):
    mock_put = mocker.patch(
        "app.services.rates.requests.put", return_value=_mock_response(200, {"ok": True})
    )

    response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 1.0},
        headers=_headers(verified_superadmin),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Rate change applied successfully."
    mock_put.assert_called_once()


# ---------------------------------------------------------------------------
# bulk_update_segments (PUT /rates/segments/bulk)
# ---------------------------------------------------------------------------


def _segment_payload(segment_id):
    return {
        "segments": [
            {
                "id": str(segment_id),
                "name": "Tier 1",
                "isActive": True,
                "buyFeeType": "percentage",
                "buySpread": 1.0,
                "sellFeeType": "percentage",
                "sellSpread": 1.0,
            }
        ],
        "setupNote": "test",
    }


def test_bulk_update_segments_without_override_creates_proposal(
    mocker, test_client, db_session, manager_without_override
):
    mock_put = mocker.patch("app.services.rates.requests.put")

    response = test_client.put(
        "/api/rates/segments/bulk",
        json=_segment_payload(uuid4()),
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Segment change proposal submitted successfully."
    mock_put.assert_not_called()
    assert db_session.query(RateApprovalRequest).one().status == "PENDING"


def test_bulk_update_segments_with_override_applies_immediately(
    mocker, test_client, db_session, manager_with_override
):
    mock_put = mocker.patch(
        "app.services.rates.requests.put", return_value=_mock_response(200, {"ok": True})
    )

    response = test_client.put(
        "/api/rates/segments/bulk",
        json=_segment_payload(uuid4()),
        headers=_headers(manager_with_override),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Segment changes applied successfully."
    mock_put.assert_called_once()
    assert db_session.query(RateApprovalRequest).one().status == "APPROVED"
    assert db_session.query(RateChangeLog).count() == 1


# ---------------------------------------------------------------------------
# bulk_assign_to_segments (PUT /rates/segments/{segment_id}/bulk-assign)
# ---------------------------------------------------------------------------


def test_bulk_assign_to_segments_without_override_creates_proposal(
    mocker, test_client, db_session, manager_without_override
):
    mock_put = mocker.patch("app.services.rates.requests.put")

    response = test_client.put(
        f"/api/rates/segments/{uuid4()}/bulk-assign",
        json={"assetIds": [str(uuid4())], "setupNote": "reassign"},
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Rate change proposal submitted successfully."
    mock_put.assert_not_called()
    assert db_session.query(RateApprovalRequest).one().status == "PENDING"


def test_bulk_assign_to_segments_with_override_applies_immediately(
    mocker, test_client, db_session, manager_with_override
):
    mock_put = mocker.patch(
        "app.services.rates.requests.put", return_value=_mock_response(200, {"ok": True})
    )

    response = test_client.put(
        f"/api/rates/segments/{uuid4()}/bulk-assign",
        json={"assetIds": [str(uuid4())], "setupNote": "reassign"},
        headers=_headers(manager_with_override),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Rate change applied successfully."
    mock_put.assert_called_once()
    assert db_session.query(RateApprovalRequest).one().status == "APPROVED"
    assert db_session.query(RateChangeLog).count() == 1


# ---------------------------------------------------------------------------
# approve / reject proposal
# ---------------------------------------------------------------------------


def test_approve_proposal_applies_change_and_logs(
    mocker, test_client, db_session, manager_without_override, verified_superadmin
):
    mocker.patch("app.services.rates.requests.put")  # not called during proposal creation
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    proposal_id = str(db_session.query(RateApprovalRequest).one().id)

    mock_put = mocker.patch(
        "app.services.rates.requests.put", return_value=_mock_response(200, {"applied": True})
    )
    approve_response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/approve",
        headers=_headers(verified_superadmin),
    )

    assert approve_response.status_code == 200
    mock_put.assert_called_once()

    proposal = db_session.get(RateApprovalRequest, UUID(proposal_id))
    assert proposal.status == "APPROVED"
    assert db_session.query(RateChangeLog).count() == 1


def test_approve_already_processed_proposal_rejected(
    mocker, test_client, db_session, manager_without_override, verified_superadmin
):
    mocker.patch("app.services.rates.requests.put")
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    proposal_id = str(db_session.query(RateApprovalRequest).one().id)

    test_client.post(
        f"/api/rates/proposals/{proposal_id}/reject",
        headers=_headers(verified_superadmin),
    )

    second_response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/approve",
        headers=_headers(verified_superadmin),
    )

    assert second_response.status_code == 400


def test_reject_proposal(
    mocker, test_client, db_session, manager_without_override, verified_superadmin
):
    mocker.patch("app.services.rates.requests.put")
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    proposal_id = str(db_session.query(RateApprovalRequest).one().id)

    response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/reject",
        headers=_headers(verified_superadmin),
    )

    assert response.status_code == 200
    proposal = db_session.get(RateApprovalRequest, UUID(proposal_id))
    assert proposal.status == "REJECTED"


# ---------------------------------------------------------------------------
# approve / reject proposal notifies the requester only
# ---------------------------------------------------------------------------


def test_approve_proposal_notifies_requester_only(
    mocker, test_client, db_session, manager_without_override, verified_superadmin
):
    mocker.patch("app.services.rates.requests.put")
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    proposal_id = str(db_session.query(RateApprovalRequest).one().id)

    mock_notify = mocker.patch("app.services.rates.ERPService.new_notification")
    mocker.patch(
        "app.services.rates.requests.put", return_value=_mock_response(200, {"applied": True})
    )

    response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/approve",
        headers=_headers(verified_superadmin),
    )

    assert response.status_code == 200
    mock_notify.assert_called_once()
    assert [r.id for r in mock_notify.call_args.kwargs["recipients"]] == [manager_without_override.id]
    assert mock_notify.call_args.kwargs["reference_id"] == UUID(proposal_id)


def test_reject_proposal_notifies_requester_only(
    mocker, test_client, db_session, manager_without_override, verified_superadmin
):
    mocker.patch("app.services.rates.requests.put")
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    proposal_id = str(db_session.query(RateApprovalRequest).one().id)

    mock_notify = mocker.patch("app.services.rates.ERPService.new_notification")

    response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/reject",
        headers=_headers(verified_superadmin),
    )

    assert response.status_code == 200
    mock_notify.assert_called_once()
    assert [r.id for r in mock_notify.call_args.kwargs["recipients"]] == [manager_without_override.id]
    assert mock_notify.call_args.kwargs["reference_id"] == UUID(proposal_id)


def test_approve_own_proposal_sends_no_self_notification(
    mocker, test_client, db_session, manager_without_override
):
    """The approve route only gates on account type, so a requester who is
    also an approver can process their own proposal. They shouldn't get a
    notification about their own action."""
    mocker.patch("app.services.rates.requests.put")
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    proposal_id = str(db_session.query(RateApprovalRequest).one().id)

    mock_notify = mocker.patch("app.services.rates.ERPService.new_notification")
    mocker.patch(
        "app.services.rates.requests.put", return_value=_mock_response(200, {"applied": True})
    )

    response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/approve",
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 200
    mock_notify.assert_not_called()


def test_reject_own_proposal_sends_no_self_notification(
    mocker, test_client, db_session, manager_without_override
):
    mocker.patch("app.services.rates.requests.put")
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    proposal_id = str(db_session.query(RateApprovalRequest).one().id)

    mock_notify = mocker.patch("app.services.rates.ERPService.new_notification")

    response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/reject",
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 200
    mock_notify.assert_not_called()


# ---------------------------------------------------------------------------
# approve / reject proposal resolves every notification tied to it, so a
# reviewer who wasn't the one who acted doesn't keep seeing a stale prompt
# ---------------------------------------------------------------------------


@pytest.fixture
def approve_permission(db_session) -> PermissionModel:
    row = PermissionModel(name=Permission.APPROVE_RATE_CHANGES.value, category="rates")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


@pytest.fixture
def reviewer(db_session, approve_permission) -> ERPUser:
    role = _make_role(db_session, "Rates Reviewer", allowed=[approve_permission])
    return _make_staff(db_session, role, "reviewer@example.com")


def test_approve_proposal_resolves_other_reviewers_notifications(
    mocker, test_client, db_session, manager_without_override, reviewer, verified_superadmin
):
    mocker.patch("app.services.rates.requests.put")
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    assert create_response.status_code == 200
    proposal_id = db_session.query(RateApprovalRequest).one().id

    # the fan-out notification created for `reviewer` on submission starts ACTIVE
    reviewer_notif = db_session.query(Notification).filter_by(
        user_id=reviewer.id, reference_id=proposal_id
    ).one()
    assert reviewer_notif.status == "ACTIVE"

    mocker.patch(
        "app.services.rates.requests.put", return_value=_mock_response(200, {"applied": True})
    )
    approve_response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/approve",
        headers=_headers(verified_superadmin),
    )
    assert approve_response.status_code == 200

    db_session.expire_all()

    reviewer_notif = db_session.query(Notification).filter_by(
        user_id=reviewer.id, reference_id=proposal_id
    ).one()
    assert reviewer_notif.status == "RESOLVED"

    requester_notif = db_session.query(Notification).filter_by(
        user_id=manager_without_override.id, reference_id=proposal_id
    ).one()
    assert requester_notif.status == "RESOLVED"


def test_reject_proposal_resolves_other_reviewers_notifications(
    mocker, test_client, db_session, manager_without_override, reviewer, verified_superadmin
):
    mocker.patch("app.services.rates.requests.put")
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    assert create_response.status_code == 200
    proposal_id = db_session.query(RateApprovalRequest).one().id

    reviewer_notif = db_session.query(Notification).filter_by(
        user_id=reviewer.id, reference_id=proposal_id
    ).one()
    assert reviewer_notif.status == "ACTIVE"

    reject_response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/reject",
        headers=_headers(verified_superadmin),
    )
    assert reject_response.status_code == 200

    db_session.expire_all()

    reviewer_notif = db_session.query(Notification).filter_by(
        user_id=reviewer.id, reference_id=proposal_id
    ).one()
    assert reviewer_notif.status == "RESOLVED"

    requester_notif = db_session.query(Notification).filter_by(
        user_id=manager_without_override.id, reference_id=proposal_id
    ).one()
    assert requester_notif.status == "RESOLVED"


def test_approve_proposal_does_not_resolve_notifications_for_other_proposals(
    mocker, test_client, db_session, manager_without_override, reviewer, verified_superadmin
):
    mocker.patch("app.services.rates.requests.put")
    first_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    second_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 4.0},
        headers=_headers(manager_without_override),
    )
    assert first_response.status_code == 200
    assert second_response.status_code == 200

    proposals = db_session.query(RateApprovalRequest).order_by(
        RateApprovalRequest.created_at
    ).all()
    assert len(proposals) == 2
    first_id, second_id = proposals[0].id, proposals[1].id

    mocker.patch(
        "app.services.rates.requests.put", return_value=_mock_response(200, {"applied": True})
    )
    response = test_client.post(
        f"/api/rates/proposals/{first_id}/approve",
        headers=_headers(verified_superadmin),
    )
    assert response.status_code == 200

    db_session.expire_all()

    first_notif = db_session.query(Notification).filter_by(
        user_id=reviewer.id, reference_id=first_id
    ).one()
    second_notif = db_session.query(Notification).filter_by(
        user_id=reviewer.id, reference_id=second_id
    ).one()
    assert first_notif.status == "RESOLVED"
    assert second_notif.status == "ACTIVE"


# ---------------------------------------------------------------------------
# get_proposal_by_id (GET /rates/proposals/{proposal_id})
# ---------------------------------------------------------------------------


def test_get_proposal_by_id_returns_proposal(
    mocker, test_client, db_session, manager_without_override
):
    mocker.patch("app.services.rates.requests.put")
    create_response = test_client.put(
        f"/api/rates/crypto/{uuid4()}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )
    proposal_id = str(db_session.query(RateApprovalRequest).one().id)

    response = test_client.get(
        f"/api/rates/proposals/{proposal_id}",
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 200
    proposal = response.json()["proposal"]
    assert proposal["id"] == proposal_id
    assert proposal["status"] == "PENDING"


def test_get_proposal_by_id_not_found(test_client, manager_without_override):
    response = test_client.get(
        f"/api/rates/proposals/{uuid4()}",
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# notification reference_id must point at the generated proposal, not the
# asset/segment being changed
# ---------------------------------------------------------------------------


def _segments_payload(*segment_ids):
    return {
        "segments": [
            {
                "id": str(segment_id),
                "name": f"Tier {i}",
                "isActive": True,
                "buyFeeType": "percentage",
                "buySpread": 1.0,
                "sellFeeType": "percentage",
                "sellSpread": 1.0,
            }
            for i, segment_id in enumerate(segment_ids, start=1)
        ],
        "setupNote": "test",
    }


def test_bulk_update_segments_sends_one_notification_per_proposal(
    mocker, test_client, db_session, manager_without_override
):
    mock_notify = mocker.patch("app.services.rates.ERPService.notify_permission_holders")

    response = test_client.put(
        "/api/rates/segments/bulk",
        json=_segments_payload(uuid4(), uuid4(), uuid4()),
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 200
    proposals = db_session.query(RateApprovalRequest).order_by(
        RateApprovalRequest.created_at
    ).all()
    assert len(proposals) == 3

    # one notification per proposal, not one summary notification for the batch
    assert mock_notify.call_count == 3
    notified_reference_ids = {
        call.kwargs["reference_id"] for call in mock_notify.call_args_list
    }
    assert notified_reference_ids == {p.id for p in proposals}


def test_bulk_assign_to_segments_sends_one_notification_per_proposal(
    mocker, test_client, db_session, manager_without_override
):
    mock_notify = mocker.patch("app.services.rates.ERPService.notify_permission_holders")

    segment_id = uuid4()
    response = test_client.put(
        f"/api/rates/segments/{segment_id}/bulk-assign",
        json={
            "assetIds": [str(uuid4()), str(uuid4())],
            "setupNote": "reassign",
        },
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 200
    proposals = db_session.query(RateApprovalRequest).order_by(
        RateApprovalRequest.created_at
    ).all()
    assert len(proposals) == 2

    assert mock_notify.call_count == 2
    notified_reference_ids = {
        call.kwargs["reference_id"] for call in mock_notify.call_args_list
    }
    assert notified_reference_ids == {p.id for p in proposals}
    assert segment_id not in notified_reference_ids


def test_update_crypto_rate_notification_references_created_proposal(
    mocker, test_client, db_session, manager_without_override
):
    mocker.patch("app.services.rates.requests.put")
    mock_notify = mocker.patch("app.services.rates.ERPService.notify_permission_holders")

    rate_id = uuid4()
    response = test_client.put(
        f"/api/rates/crypto/{rate_id}",
        json={"buyFeeValue": 3.0},
        headers=_headers(manager_without_override),
    )

    assert response.status_code == 200
    proposal = db_session.query(RateApprovalRequest).one()

    mock_notify.assert_called_once()
    reference_id = mock_notify.call_args.kwargs["reference_id"]
    assert reference_id == proposal.id
    assert reference_id != rate_id
