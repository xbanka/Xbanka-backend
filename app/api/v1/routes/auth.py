from fastapi import (
    APIRouter,
    status,
    Depends,
    Response,
    Request,
    HTTPException,
    BackgroundTasks,
)
from sqlalchemy.orm import Session
from app.schemas.user import (
    RegisterBase,
    RegisterResponse,
    LoginBase,
    LoginResponse,
    LogoutResponse,
    VerifyResponse,
)
from app.services.auth import AuthService
from app.services.user import UserService
from app.db.database import get_db
from app.utils.settings import settings
from app.core.email import send_mail
from app.models.affiliate import Affiliate


auth = APIRouter(prefix="/auth", tags=["Auth"])

FRONTEND_URL = settings.FRONTEND_URL
JWT_REFRESH_EXPIRY = settings.JWT_REFRESH_EXPIRY


@auth.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(create_request: LoginBase, response: Response, db: Session = Depends(get_db)):
    user = AuthService.authenticate_user(
        db, create_request.email, create_request.password
    )

    access_token = AuthService.create_access_token(data={"sub": str(user.id)})
    refresh_token = AuthService.create_refresh_token(data={"sub": str(user.id)})

    # Add refresh token to cookies
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=JWT_REFRESH_EXPIRY * 24 * 60 * 60,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@auth.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    login_request: RegisterBase,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = UserService.create(db, login_request)

    token = AuthService.create_magic_link_token(data={"sub": str(user.id)})
    url = f"{FRONTEND_URL}/verify?token={token}"

    await send_mail(
        recipient=login_request.email,
        first_name=str(user.first_name),
        last_name=str(user.last_name),
        verification_url=url,
        background_tasks=background_tasks,
    )

    return {
        "message": "User creation successful. Verification email sent",
        "user": user,
    }


@auth.post("/refresh", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def refresh_token(request: Request, response: Response):
    # Retrieve refresh token from cookies
    current_refresh_token = request.cookies.get("refresh_token")
    if not current_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )

    access_token, refresh_token = AuthService.refresh_access_token(
        current_refresh_token
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

    return {"access_token": access_token, "token_type": "bearer"}


@auth.post("/verify", response_model=VerifyResponse)
def verify_magic_link(token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401, detail="Magic token expired/invalid"
    )

    affiliate: Affiliate = AuthService.verify_magic_link(db, token, credentials_exception)
    if affiliate.verified:
        return {"message": "This user is already verified"}

    affiliate.verified = True
    db.commit()

    return {"message": "Affiliate verified successfully"}


@auth.post("/logout", response_model=LogoutResponse)
def logout(response: Response):
    response.delete_cookie(
        key="refresh_token", path="/", secure=True, httponly=True, samesite="none"
    )

    return {"success": True, "message": "Logged out successfully"}
