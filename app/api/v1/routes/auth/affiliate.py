from fastapi import (
    APIRouter,
    status,
    Depends,
    Response,
    Request,
    HTTPException,
    BackgroundTasks,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.schemas.user import (
    RegisterBase,
    RegisterResponse,
    LoginBase,
    LoginResponse,
    LogoutResponse,
    VerifyResponse,
    AccountVerificationRequest,
    AccountVerificationResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest
)
from app.services.auth import AuthService
from app.services.affiliate import AffiliateService
from app.db.database import get_db
from app.utils.settings import settings
from app.core.email import send_verification_email, send_forgot_password_email
from app.models.affiliate import Affiliate
from app.models.erp_user import ERPUser
from app.core.enums import EmailTypeEnum


affiliate = APIRouter(prefix="/affiliates")

AFFILIATE_FRONTEND_URL = settings.AFFILIATE_FRONTEND_URL
JWT_REFRESH_EXPIRY = settings.JWT_REFRESH_EXPIRY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


@affiliate.post("/token")
async def swagger_authenticate(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = AuthService.authenticate_user(
        db, ERPUser, form_data.username, form_data.password
    )
    access_token = AuthService.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}



@affiliate.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(create_request: LoginBase, response: Response, db: Session = Depends(get_db)):
    user = AuthService.authenticate_user(
        db, Affiliate, create_request.email, create_request.password
    )

    access_token = AuthService.create_access_token(data={"sub": str(user.id), "role": "affiliate"})
    refresh_token = AuthService.create_refresh_token(data={"sub": str(user.id), "role": "affiliate"})

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


@affiliate.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    login_request: RegisterBase,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = AffiliateService.create(db, login_request)

    token = AuthService.create_magic_link_token(data={"sub": str(user.id)})
    url = f"{AFFILIATE_FRONTEND_URL}/affiliate/verify?token={token}"

    await send_verification_email(
        recipient=login_request.email,
        email_type=EmailTypeEnum.affiliate,
        first_name=str(user.first_name),
        last_name=str(user.last_name),
        verification_url=url,
        background_tasks=background_tasks,
    )

    return {
        "message": "Your profile has been created. Please check your email to verify your account.",
        "user": user,
    }


@affiliate.post("/refresh", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def refresh_token(request: Request, response: Response):
    # Retrieve refresh token from cookies
    current_refresh_token = request.cookies.get("refresh_token")
    if not current_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )

    access_token, refresh_token = AuthService.refresh_access_token(
        current_refresh_token,
        "affiliate"
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


@affiliate.post("/verify", response_model=VerifyResponse)
def verify_magic_link(token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401, detail="Magic token expired/invalid"
    )

    affiliate: Affiliate = AuthService.verify_magic_link(db, Affiliate, token, credentials_exception)
    if affiliate.verified:
        return {"message": "This user is already verified"}

    affiliate.verified = True
    db.commit()

    return {"message": "Affiliate verified successfully"}


@affiliate.post("/logout", response_model=LogoutResponse)
def logout(response: Response):
    response.delete_cookie(
        key="refresh_token", path="/", secure=True, httponly=True, samesite="none"
    )
    response.delete_cookie(
        key="access_token", path="/", secure=True, httponly=True, samesite="none"
    )

    return {"success": True, "message": "Logged out successfully"}


@affiliate.post('/verify-account', response_model=AccountVerificationResponse)
def verify_bank_information(request: AccountVerificationRequest):
    return AuthService.verify_bank_information(request)


@affiliate.post('/resend-verification', response_model=VerifyResponse)
def resend_verification(request: AccountVerificationRequest):
    return AuthService.resend_verification_email(request)


@affiliate.post('/forgot-password', response_model=ForgotPasswordResponse)
async def forgot_password(
    forgot_request: ForgotPasswordRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):  
    user = AffiliateService.get_user_by_mail(db, forgot_request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User with this email does not exist")
    
    token = AuthService.create_password_reset_token(data={"sub": str(user.id)})
    url = f"{AFFILIATE_FRONTEND_URL}/affiliate/reset-password?token={token}"

    await send_forgot_password_email(
        recipient=forgot_request.email,
        email_type=EmailTypeEnum.affiliate,
        first_name=str(user.first_name),
        last_name=str(user.last_name),
        reset_url=url,
        background_tasks=background_tasks,
    )

    return {"message": "Password reset instructions have been sent to your email."}

@affiliate.post('/reset-password', response_model=ForgotPasswordResponse)
def reset_password(reset_request: ResetPasswordRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401, detail="Password reset token expired/invalid"
    )
    
    user_token = AuthService.verify_password_reset_token(reset_request.token, credentials_exception)
    if not user_token:
        raise HTTPException(status_code=401, detail="Password reset token expired/invalid")
    
    AuthService.update_user_password(db, user_token, reset_request.new_password, AffiliateService)
    
    return {"message": "Password has been reset successfully"}
