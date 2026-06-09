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

invite_payload = {
  "email": "olotonjoshua@gmail.com",
  "role": "Admin",
  "permissions": [
   
  ]
}

# def test_uninitialized_erp_register(mocker, test_client):
#     response = test_client.post("/api/auth/erp/register", json=register_payload)
#     json = response.json()
#     assert response.status_code == 403
#     assert json["detail"] == "ERP user has not been initialized."

# def test_staff_invite(mocker, super_client):
#     mock_send_email = mocker.patch(
#         "app.api.v1.routes.staff.send_invite_email")
#     response = super_client.post("/api/staff/invite", json=invite_payload)
#     json = response.json()
#     assert response.status_code == 200
#     assert json["message"] == f"Staff member {invite_payload['email']} invited successfully."
#     mock_send_email.assert_called_once()


# def test_erp_register_success(mocker, test_client):
#     # Mock ERP initialization
#     mocker.patch('app.services.auth.AuthService.is_erp_initialized', return_value=True)
#     mocker.patch('app.services.auth.AuthService.register_erp_user', return_value={"id": 1, "email": "michael.adee@example.com"})
#     response = test_client.post("/api/auth/erp/register", json=register_payload)
#     assert response.status_code == 201
#     json = response.json()
#     assert json["email"] == "michael.adee@example.com"

# def test_erp_register_invalid_data(test_client):
#     invalid_payload = register_payload.copy()
#     invalid_payload["email"] = "invalid-email"
#     response = test_client.post("/api/auth/erp/register", json=invalid_payload)
#     assert response.status_code == 422  # Assuming validation error