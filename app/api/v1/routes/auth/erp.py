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
from app.schemas.erp.user import (
    RegisterBase, 
    RegisterResponse, 
    LoginBase, 
    LoginResponse, 
    LogoutResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    VerifyResponse
)
from app.core.email import send_verification_email, send_forgot_password_email
from app.core.enums import EmailTypeEnum
from app.db.database import get_db
from app.models.erp_user import ERPUser
from app.services.auth import AuthService
from app.services.erp_user import ERPService
from app.utils.settings import settings



erp = APIRouter(prefix='/erp')

ERP_FRONTEND_URL = settings.ERP_FRONTEND_URL
JWT_REFRESH_EXPIRY = settings.JWT_REFRESH_EXPIRY


@erp.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(create_request: LoginBase, response: Response, db: Session = Depends(get_db)):
    user = AuthService.authenticate_erpuser(
        db, create_request.email, create_request.password
    )

    access_token = AuthService.create_access_token(data={"sub": str(user.id), "role": "erp"})
    refresh_token = AuthService.create_refresh_token(data={"sub": str(user.id), "role": "erp"})

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


@erp.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    login_request: RegisterBase,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = ERPService.create(db, login_request)

    token = AuthService.create_magic_link_token(data={"sub": str(user.id)})
    url = f"{ERP_FRONTEND_URL}/erp/verify?token={token}"

    await send_verification_email(
        recipient=login_request.email,
        email_type=EmailTypeEnum.erp,
        first_name=str(user.first_name),
        last_name=str(user.last_name),
        verification_url=url,
        background_tasks=background_tasks,
    )

    return {
        "message": "Your profile has been created. Please check your email to verify your account.",
        "user": user,
    }


@erp.post("/refresh", response_model=LoginResponse, status_code=status.HTTP_200_OK)
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


@erp.post("/verify", response_model=VerifyResponse)
def verify_magic_link(token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401, detail="Magic token expired/invalid"
    )

    erpuser: ERPUser = AuthService.verify_magic_link(db, ERPUser, token, credentials_exception)
    if erpuser.verified:
        return {"message": "This user is already verified"}

    erpuser.verified = True
    db.commit()

    return {"message": "Account verified successfully"}


@erp.post("/logout", response_model=LogoutResponse)
def logout(response: Response):
    response.delete_cookie(
        key="refresh_token", path="/", secure=True, httponly=True, samesite="none"
    )

    return {"success": True, "message": "Logged out successfully"}



@erp.post('/forgot-password', response_model=ForgotPasswordResponse)
async def forgot_password(
    forgot_request: ForgotPasswordRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):  
    user = ERPService.get_user_by_mail(db, forgot_request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User with this email does not exist")
    
    token = AuthService.create_password_reset_token(data={"sub": str(user.id)})
    url = f"{ERP_FRONTEND_URL}/erp/reset-password?token={token}"

    await send_forgot_password_email(
        recipient=forgot_request.email,
        email_type=EmailTypeEnum.erp,
        first_name=str(user.first_name),
        last_name=str(user.last_name),
        reset_url=url,
        background_tasks=background_tasks,
    )

    return {"message": "Password reset instructions have been sent to your email."}

@erp.post('/reset-password', response_model=ForgotPasswordResponse)
def reset_password(reset_request: ResetPasswordRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401, detail="Password reset token expired/invalid"
    )
    
    user_token = AuthService.verify_password_reset_token(reset_request.token, credentials_exception)
    if not user_token:
        raise HTTPException(status_code=401, detail="Password reset token expired/invalid")
    
    AuthService.update_user_password(db, user_token, reset_request.new_password)
    
    return {"message": "Password has been reset successfully"}
