import secrets
from app import db
from app.core.hash import Hasher
from app.services.auth import AuthService

register_payload = {
    "first_name": "Michael",
    "last_name": "Adeyemi",
    "email": "michael.adee@example.com",
    "password": "@Password123",
    "confirm_password": "@Password123"
}

login_payload = {
    "email": "michael.adee@example.com",
    "password": "@Password123"
}

mock_token = "mocked_token"

ver_affiliate = {
    "verified": True
}

def test_erp_register(mocker, test_client):
    mock_send_email = mocker.patch(
        "app.api.v1.routes.auth.erp.send_verification_email")
    response = test_client.post("/api/auth/erp/register", json=register_payload)
    json = response.json()
    print(json)
    assert response.status_code == 201
    assert json["message"] == "Your profile has been created. Please check your email to verify your account."
    mock_send_email.assert_called_once()
    

def test_erp_login_unverified(test_client):
    test_client.post("/api/auth/erp/register", json=register_payload)
    response = test_client.post("/api/auth/erp/login", json=login_payload)
    json = response.json()
    assert json["detail"] == "User profile verification required"
    assert response.status_code == 401

def test_verify_erp(mocker, test_client, db_session):
    from app.models.erp_user import ERPUser
    erp_user = ERPUser(
        first_name="Sophia",
        last_name="Johnson",
        email="sophia.johnson@example.co.uk",
        hashed_password=Hasher.get_password_hash("@Next23rd"),
        verified=False,
    )
    db_session.add(erp_user)
    db_session.commit()
    db_session.refresh(erp_user)

    mock_verify_token = mocker.patch(
        "app.services.auth.AuthService.verify_magic_link", return_value=erp_user
    )

    mock_token = "mock_token"
    test_client.post(f"/api/auth/erp/verify?token={mock_token}")

    assert erp_user.verified == True