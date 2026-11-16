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


def test_no_filters_returns_all_staff_except_super_admin(super_client, roster):
    response = super_client.get(URL)

    assert _emails(response) == {
        "jane.doe@xbankang.com",
        "john.smith@xbankang.com",
        "janet@partner.io",
    }
    assert response.json()["count"] == 3


def test_filter_by_first_name_is_case_insensitive_substring(super_client, roster):
    assert _emails(super_client.get(URL, params={"name": "JAN"})) == {
        "jane.doe@xbankang.com",
        "janet@partner.io",
    }


def test_filter_by_last_name(super_client, roster):
    assert _emails(super_client.get(URL, params={"name": "smith"})) == {
        "john.smith@xbankang.com"
    }


def test_filter_by_full_name(super_client, roster):
    assert _emails(super_client.get(URL, params={"name": "jane doe"})) == {
        "jane.doe@xbankang.com"
    }


def test_filter_by_email(super_client, roster):
    assert _emails(super_client.get(URL, params={"email": "@partner.io"})) == {
        "janet@partner.io"
    }


def test_filter_by_role_is_case_insensitive_exact(super_client, roster):
    assert _emails(super_client.get(URL, params={"role": "support"})) == {
        "jane.doe@xbankang.com",
        "john.smith@xbankang.com",
    }
    # exact, not substring
    assert _emails(super_client.get(URL, params={"role": "Supp"})) == set()


def test_filters_combine_with_and(super_client, roster):
    response = super_client.get(URL, params={"name": "jan", "role": "Compliance"})

    assert _emails(response) == {"janet@partner.io"}
    assert response.json()["count"] == 1


def test_blank_filters_are_ignored(super_client, roster):
    response = super_client.get(URL, params={"name": "  ", "email": "", "role": ""})

    assert response.json()["count"] == 3


def test_like_wildcards_are_matched_literally(super_client, roster):
    assert _emails(super_client.get(URL, params={"name": "%"})) == set()
    assert _emails(super_client.get(URL, params={"email": "_"})) == set()


def test_super_admin_is_never_returned(super_client, roster):
    response = super_client.get(URL, params={"role": "Super Admin"})

    assert response.status_code == 200
    assert response.json() == {"staff": [], "count": 0}
