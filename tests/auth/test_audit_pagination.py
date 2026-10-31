import uuid
from datetime import datetime, timezone

import pytest

from app.core.enums import (
    FundingIntentActionEnum,
    FundingIntentLogStatusEnum,
    LoginStatusEnum,
    RoleChangeStatusEnum,
)
from app.models.funding_intent_log import FundingIntentLog
from app.models.login_log import LoginLog
from app.models.role_change_log import RoleChangeLog
from app.services.auth import AuthService

# Every seeded row shares one timestamp, as rows written in a single
# transaction do. Paging only stays stable if ordering falls back to the id.
SAME_TIME = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _headers(staff) -> dict:
    token = AuthService.create_access_token(
        data={"sub": str(staff.id), "account_type": "erp"}
    )
    return {"Authorization": f"Bearer {token}"}


def _alternating(i, first, second):
    return first if i % 2 == 0 else second


def _seed_logins(db, staff, n):
    db.add_all(
        LoginLog(
            attempted_email=f"user{i}@example.com",
            status=_alternating(i, LoginStatusEnum.SUCCESS, LoginStatusEnum.FAILED),
            created_at=SAME_TIME,
        )
        for i in range(n)
    )


def _seed_role_changes(db, staff, n):
    db.add_all(
        RoleChangeLog(
            staff_id=staff.id,
            requested_by_id=staff.id,
            previous_role="Viewer",
            new_role="Manager",
            status=_alternating(
                i, RoleChangeStatusEnum.CONFIRMED, RoleChangeStatusEnum.PENDING
            ),
            created_at=SAME_TIME,
        )
        for i in range(n)
    )


def _seed_funding_intents(db, staff, n):
    db.add_all(
        FundingIntentLog(
            staff_id=staff.id,
            transaction_id=uuid.uuid4(),
            action=_alternating(
                i, FundingIntentActionEnum.COMPLETED, FundingIntentActionEnum.REJECTED
            ),
            status=_alternating(
                i, FundingIntentLogStatusEnum.SUCCESS, FundingIntentLogStatusEnum.FAILED
            ),
            created_at=SAME_TIME,
        )
        for i in range(n)
    )


# (url, seeder, the `status` value that matches the even-indexed seeded rows)
ENDPOINTS = [
    pytest.param("/api/audit/logins", _seed_logins, "SUCCESS", id="logins"),
    pytest.param(
        "/api/audit/role-changes", _seed_role_changes, "CONFIRMED", id="role-changes"
    ),
    pytest.param(
        "/api/audit/funding-intents", _seed_funding_intents, "SUCCESS", id="funding-intents"
    ),
]


def _get(test_client, staff, url, **params):
    response = test_client.get(url, params=params, headers=_headers(staff))
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("url, seed, matching_status", ENDPOINTS)
def test_response_carries_page_limit_total_and_pages(
    test_client, db_session, verified_superadmin, url, seed, matching_status
):
    seed(db_session, verified_superadmin, 25)
    db_session.commit()

    first = _get(test_client, verified_superadmin, url, limit=10)
    assert {k: first[k] for k in ("page", "limit", "total", "pages")} == {
        "page": 1,
        "limit": 10,
        "total": 25,
        "pages": 3,
    }
    assert len(first["data"]) == 10

    last = _get(test_client, verified_superadmin, url, limit=10, page=3)
    assert last["page"] == 3
    assert len(last["data"]) == 5


@pytest.mark.parametrize("url, seed, matching_status", ENDPOINTS)
def test_page_past_the_end_is_empty_but_keeps_the_totals(
    test_client, db_session, verified_superadmin, url, seed, matching_status
):
    seed(db_session, verified_superadmin, 5)
    db_session.commit()

    past_end = _get(test_client, verified_superadmin, url, limit=10, page=4)

    assert past_end["data"] == []
    assert past_end["total"] == 5
    assert past_end["pages"] == 1


@pytest.mark.parametrize("url, seed, matching_status", ENDPOINTS)
def test_no_rows_gives_zero_total_and_pages(
    test_client, verified_superadmin, url, seed, matching_status
):
    body = _get(test_client, verified_superadmin, url)

    assert body["data"] == []
    assert (body["total"], body["pages"]) == (0, 0)


@pytest.mark.parametrize("url, seed, matching_status", ENDPOINTS)
def test_total_counts_rows_matching_the_filter_not_the_whole_table(
    test_client, db_session, verified_superadmin, url, seed, matching_status
):
    seed(db_session, verified_superadmin, 11)  # 6 even-indexed rows, 5 odd
    db_session.commit()

    everything = _get(test_client, verified_superadmin, url)
    filtered = _get(
        test_client, verified_superadmin, url, status=matching_status, limit=4
    )

    assert everything["total"] == 11
    assert filtered["total"] == 6
    assert filtered["pages"] == 2
    assert len(filtered["data"]) == 4


@pytest.mark.parametrize("url, seed, matching_status", ENDPOINTS)
def test_walking_every_page_returns_each_row_exactly_once(
    test_client, db_session, verified_superadmin, url, seed, matching_status
):
    seed(db_session, verified_superadmin, 8)
    db_session.commit()

    seen = []
    for page in range(1, 5):
        body = _get(test_client, verified_superadmin, url, limit=3, page=page)
        seen.extend(row["id"] for row in body["data"])

    assert len(seen) == 8
    assert len(set(seen)) == 8


@pytest.mark.parametrize(
    "url, seed, matching_status",
    [p for p in ENDPOINTS if p.id != "logins"],
)
def test_search_joined_on_staff_still_counts_each_row_once(
    test_client, db_session, verified_superadmin, url, seed, matching_status
):
    seed(db_session, verified_superadmin, 6)
    db_session.commit()

    body = _get(
        test_client,
        verified_superadmin,
        url,
        search=verified_superadmin.staff_code,
        limit=4,
    )

    assert body["total"] == 6
    assert body["pages"] == 2
    assert len(body["data"]) == 4


def test_login_search_counts_only_matching_emails(
    test_client, db_session, verified_superadmin
):
    _seed_logins(db_session, verified_superadmin, 12)
    db_session.commit()

    body = _get(
        test_client, verified_superadmin, "/api/audit/logins", search="user1", limit=5
    )

    # user1, user10, user11
    assert body["total"] == 3
    assert body["pages"] == 1
    assert len(body["data"]) == 3


@pytest.mark.parametrize("url, seed, matching_status", ENDPOINTS)
@pytest.mark.parametrize("params", [{"limit": 101}, {"limit": 0}, {"page": 0}])
def test_out_of_range_page_or_limit_is_rejected(
    test_client, verified_superadmin, url, seed, matching_status, params
):
    response = test_client.get(url, params=params, headers=_headers(verified_superadmin))
    assert response.status_code == 422
