from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from app.db.database import get_db
from app.services.auth import AuthService
from app.services.affiliate import AffiliateService
from app.services.google import GoogleAuthService
from app.utils.settings import settings


GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI
JWT_REFRESH_EXPIRY = settings.JWT_REFRESH_EXPIRY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
AFFILIATE_FRONTEND_URL = settings.AFFILIATE_FRONTEND_URL

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"

google = APIRouter(prefix="/google")


@google.get("")
async def google_login(request: Request):
    """Redirect the user to Google's OAuth consent screen."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "access_type": "offline",
        "prompt": "consent",
    }

    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


@google.get("/callback")
async def auth_callback(
    response: Response,
    code: str = Query(...),
    db: Session = Depends(get_db)
):
    """Handle the callback from Google after user authentication."""
    
    # exchange code for token and fetch user info from Google
    token_payload = await GoogleAuthService.exchange_code(code)

    user_info = await GoogleAuthService.fetch_user_info(token_payload["access_token"])

    email: str = user_info["email"]

    affiliate = AffiliateService.get_by_email(db, email)
    if not affiliate:
        # create a new affiliate record if one doesn't exist
        affiliate = AffiliateService.create_from_google_user(db, user_info)

    access_token = AuthService.create_access_token(
        data={"sub": str(affiliate.id), "account_type": "affiliate"}
    )
    refresh_token = AuthService.create_refresh_token(
        data={"sub": str(affiliate.id), "account_type": "affiliate"}
    )

    # Add refresh token to cookies
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=JWT_REFRESH_EXPIRY * 24 * 60 * 60,
    )

    # new update - add access token to cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    url = f"{AFFILIATE_FRONTEND_URL}/auth/callback?token={access_token}"
    return RedirectResponse(url=url)
