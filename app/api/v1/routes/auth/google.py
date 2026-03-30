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
        "redirect_uri": request.url_for("auth_callback"),
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
    
    # user_info = await GoogleAuthService.fetch(request)

    # affiliate = AffiliateService.get_by_email(db, user_info.get("email"))
    # if not affiliate:
    #     print("No affiliate found with this email, creating a new one.")
    #     # create a new affiliate record if one doesn't exist
    #     affiliate = AffiliateService.create_from_google_user(db, user_info)

    # access_token = AuthService.create_access_token(
    #     data={"sub": str(affiliate.id), "role": "affiliate"}
    # )
    # refresh_token = AuthService.create_refresh_token(
    #     data={"sub": str(affiliate.id), "role": "affiliate"}
    # )

    # exchange code for token
    token_data = await GoogleAuthService.exchange_code(code)
    # Fetch user info from Google
    user_info = await GoogleAuthService.fetch_user_info(token_data["access_token"])

    print("Google user info:", user_info)

    google_id: str = user_info["sub"] # add google_id to user model and add
    email: str = user_info["email"]
    name: str = user_info.get("name", "")

    affiliate = AffiliateService.get_by_email(db, email)
    if not affiliate:
        print("No affiliate found with this email, creating a new one.")
        # create a new affiliate record if one doesn't exist
        affiliate = AffiliateService.create_from_google_user(db, user_info)

    access_token = AuthService.create_access_token(
        data={"sub": str(affiliate.id), "role": "affiliate"}
    )
    refresh_token = AuthService.create_refresh_token(
        data={"sub": str(affiliate.id), "role": "affiliate"}
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

    # Redirect to your frontend after successful login
    url = f"{AFFILIATE_FRONTEND_URL}/auth/callback?access_token={access_token}"
    return RedirectResponse(url=url)
