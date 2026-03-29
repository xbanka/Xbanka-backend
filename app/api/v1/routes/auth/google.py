from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.integrations.oauth import oauth
from app.services.auth import AuthService
from app.services.affiliate import AffiliateService
from app.services.google import GoogleAuthService
from app.utils.settings import settings


GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
JWT_REFRESH_EXPIRY = settings.JWT_REFRESH_EXPIRY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

google = APIRouter(prefix="/google")



@google.get("")
async def google_login(request: Request):
    """Redirect the user to Google's OAuth consent screen."""
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@google.get("/callback")
async def auth_callback(request: Request, response: Response, db: Session = Depends(get_db)):
    """Handle the callback from Google after user authentication."""
    
    user_info = await GoogleAuthService.fetch(request)

    affiliate = AffiliateService.get_by_email(db, user_info.get("email"))
    if not affiliate:
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

    return {"access_token": access_token, "token_type": "bearer"}
