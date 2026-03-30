from fastapi import HTTPException, Request
import httpx

from app.integrations.oauth import oauth
from app.utils.settings import settings



GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI

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
    
    @staticmethod
    async def fetch_user_info(access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Google user info")
        return resp.json()
    
    @staticmethod
    async def exchange_code(code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange Google code")
        return resp.json()
