from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.core.enums import Permission
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
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
    proposal_id = create_response.json()["proposed_change"]["id"]

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
    proposal_id = create_response.json()["proposed_change"]["id"]

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
    proposal_id = create_response.json()["proposed_change"]["id"]

    response = test_client.post(
        f"/api/rates/proposals/{proposal_id}/reject",
        headers=_headers(verified_superadmin),
    )

    assert response.status_code == 200
    proposal = db_session.get(RateApprovalRequest, UUID(proposal_id))
    assert proposal.status == "REJECTED"
