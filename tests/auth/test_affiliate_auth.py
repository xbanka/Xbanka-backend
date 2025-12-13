import secrets
from app import db
from app.core.hash import Hasher
from app.services.auth import AuthService

register_payload =  {
    "first_name": "Sophia",
    "last_name": "Johnson",
    "email": "sophia.johnson@example.co.uk",
    "username": "sophiee",
    "phone_no": "+447911223344",
    "bank": "Stanbic IBTC",
    "account_no": "3001239876",
    "password": "@Next23rd",
    "confirm_password": "@Next23rd"
}

login_payload = {
    "email": "sophia.johnson@example.co.uk",
    "password": "@Next23rd"
}

mock_token = "mocked_token"

ver_affiliate = {
    "verified": True
}

def test_affiliates_register(mocker, test_client):
    mock_send_email = mocker.patch(
        "app.api.v1.routes.auth.affiliate.send_verification_email")
    response = test_client.post("/api/auth/affiliates/register", json=register_payload)
    assert response.status_code == 201
    json = response.json()
    assert json["message"] == "Your profile has been created. Please check your email to verify your account."
    mock_send_email.assert_called_once()
    

def test_affiliates_login_unverified(test_client):
    test_client.post("/api/auth/affiliates/register", json=register_payload)
    response = test_client.post("/api/auth/affiliates/login", json=login_payload)
    json = response.json()
    assert json["detail"] == "User profile verification required"
    assert response.status_code == 401

def test_verify_affiliates(mocker, test_client, db_session):
    from app.models.affiliate import Affiliate
    affiliate = Affiliate(
        first_name="Sophia",
        last_name="Johnson",
        email="sophia.johnson@example.co.uk",
        username="sophiee",
        phone_no="+123456789",
        bank="United Bank",
        account_no="0123456",
        hashed_password=Hasher.get_password_hash("@Next23rd"),
        verified=False,
        ref_code=secrets.token_urlsafe(6)
    )
    db_session.add(affiliate)
    db_session.commit()
    db_session.refresh(affiliate)

    mock_verify_token = mocker.patch(
        "app.services.auth.AuthService.verify_magic_link", return_value=affiliate
    )

    mock_token = "mock_token"
    test_client.post(f"/api/auth/affiliates/verify?token={mock_token}")

    assert affiliate.verified == True