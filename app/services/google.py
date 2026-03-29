from app.integrations.oauth import oauth
from fastapi import HTTPException, Request


class GoogleAuthService:
    @staticmethod
    def get_user_info(token: str):
        """Fetch user info from Google using the access token."""
        # This is a placeholder implementation. You would use the token to call Google's userinfo endpoint.
        # For example, you could use the `requests` library to make an HTTP request to Google's API.
        # Here's a simplified example:
        import requests

        response = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            raise Exception("Failed to fetch user info from Google")

        return response.json()

    @staticmethod
    async def fetch(request: Request):
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if (
            not user_info
            or not user_info.get("email")
            or not user_info.get("given_name")
            or not user_info.get("family_name")
        ):
            raise HTTPException(
                status_code=400, detail="Could not fetch user info from Google"
            )

        return user_info
