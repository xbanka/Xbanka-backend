import pytest

from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.role import Role

URL = "/api/staff/all"


def _staff(db_session, role: Role, first: str, last: str, email: str) -> ERPUser:
    member = ERPUser(
        first_name=first,
        last_name=last,
        email=email,
        role_id=role.id,
        hashed_password=Hasher.get_password_hash("@Password123"),
        verified=True,
    )
    db_session.add(member)
    db_session.commit()
    return member


@pytest.fixture
def roster(db_session):
    support = Role(name="Support")
    compliance = Role(name="Compliance")
    db_session.add_all([support, compliance])
    db_session.commit()

    _staff(db_session, support, "Jane", "Doe", "jane.doe@xbankang.com")
    _staff(db_session, support, "John", "Smith", "john.smith@xbankang.com")
    _staff(db_session, compliance, "Janet", "Okoro", "janet@partner.io")


def _emails(response) -> set[str]:
    assert response.status_code == 200
    return {member["email"] for member in response.json()["staff"]}


def test_no_search_returns_all_staff_except_super_admin(super_client, roster):
    response = super_client.get(URL)

    assert _emails(response) == {
        "jane.doe@xbankang.com",
        "john.smith@xbankang.com",
        "janet@partner.io",
    }
    assert response.json()["count"] == 3


def test_search_matches_first_name_case_insensitive_substring(super_client, roster):
    assert _emails(super_client.get(URL, params={"search": "JAN"})) == {
        "jane.doe@xbankang.com",
        "janet@partner.io",
    }


def test_search_matches_last_name(super_client, roster):
    assert _emails(super_client.get(URL, params={"search": "smith"})) == {
        "john.smith@xbankang.com"
    }


def test_search_matches_full_name(super_client, roster):
    assert _emails(super_client.get(URL, params={"search": "jane doe"})) == {
        "jane.doe@xbankang.com"
    }


def test_search_matches_email(super_client, roster):
    assert _emails(super_client.get(URL, params={"search": "@partner.io"})) == {
        "janet@partner.io"
    }


def test_search_does_not_match_role_names(super_client, roster):
    # "supp" / "compliance" appear only in role names, never in a name or email
    assert _emails(super_client.get(URL, params={"search": "supp"})) == set()
    assert _emails(super_client.get(URL, params={"search": "compliance"})) == set()


def test_search_matches_name_or_email_for_different_staff(
    super_client, db_session, roster
):
    support = db_session.query(Role).filter_by(name="Support").one()
    _staff(db_session, support, "Carl", "Okoro", "carl@elsewhere.org")  # by name
    _staff(db_session, support, "Dana", "Lee", "okoro.dana@elsewhere.org")  # by email

    response = super_client.get(URL, params={"search": "okoro"})

    assert _emails(response) == {
        "janet@partner.io",  # by last name
        "carl@elsewhere.org",  # by last name
        "okoro.dana@elsewhere.org",  # by email
    }


def test_filter_by_role_is_case_insensitive_exact(super_client, roster):
    assert _emails(super_client.get(URL, params={"role": "support"})) == {
        "jane.doe@xbankang.com",
        "john.smith@xbankang.com",
    }
    # exact, not substring
    assert _emails(super_client.get(URL, params={"role": "Supp"})) == set()


def test_search_and_role_combine_with_and(super_client, roster):
    response = super_client.get(URL, params={"search": "jan", "role": "Compliance"})

    assert _emails(response) == {"janet@partner.io"}
    assert response.json()["count"] == 1

    # john is in Support, so adding role=Compliance leaves nobody
    assert _emails(
        super_client.get(URL, params={"search": "john", "role": "Compliance"})
    ) == set()


def test_blank_filters_are_ignored(super_client, roster):
    assert super_client.get(URL, params={"search": "  "}).json()["count"] == 3
    assert super_client.get(URL, params={"search": "", "role": ""}).json()["count"] == 3


def test_search_with_no_match_returns_empty_list(super_client, roster):
    response = super_client.get(URL, params={"search": "nobody"})

    assert response.status_code == 200
    assert response.json() == {"staff": [], "count": 0}


def test_like_wildcards_are_matched_literally(super_client, roster):
    assert _emails(super_client.get(URL, params={"search": "%"})) == set()
    assert _emails(super_client.get(URL, params={"search": "_"})) == set()


def test_super_admin_is_never_returned(super_client, roster):
    response = super_client.get(URL, params={"role": "Super Admin"})

    assert response.status_code == 200
    assert response.json() == {"staff": [], "count": 0}
