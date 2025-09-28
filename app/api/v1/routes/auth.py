from fastapi import APIRouter, status, Depends, Response
from sqlalchemy.orm import Session
from app.schemas.user import RegisterBase, RegisterResponse, LoginBase, LoginResponse
from app.services.auth import AuthService
from app.services.user import UserService
from app.db.database import get_db
from app.utils.settings import settings

auth = APIRouter(prefix='/auth', tags=["Auth"])

@auth.post('/login', response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(create_request: LoginBase, response: Response, db: Session = Depends(get_db)):
    user = AuthService.authenticate_user(db, create_request.email, create_request.password)

    access_token = AuthService.create_access_token(data={'sub': str(user.id)})
    refresh_token = AuthService.create_access_token(data={'sub': str(user.id)})

    JWT_REFRESH_EXPIRY = settings.JWT_REFRESH_EXPIRY

    # Add refresh token to cookies
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=JWT_REFRESH_EXPIRY*24*60*60
    )

    return {
        'access_token': access_token,
        'token_type': 'bearer'
    }

@auth.post('/register', response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(login_request: RegisterBase, db: Session = Depends(get_db)):
    user = UserService.create(db, login_request)

    return {
        'message': 'User creation successful',
        'user': user
    }