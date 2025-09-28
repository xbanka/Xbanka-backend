from datetime import datetime, timedelta
from fastapi import HTTPException, status
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.base.services import Service
from app.core.hash import Hasher
from app.models.user import User
from app.schemas.user import RegisterBase, TokenData
from app.services.user import UserService
from app.utils.settings import settings
from app.utils.validators import is_valid_email


ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
JWT_REFRESH_EXPIRY = settings.JWT_REFRESH_EXPIRY
ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY


class AuthService(Service[User, RegisterBase]):
    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta | None = None):
        """Method to create access token"""
        to_encode = data.copy()

        if expires_delta is not None:
            expires = datetime.now() + expires_delta
        else:
            expires = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({'exp': expires, 'type': 'access'})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)

        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
        """Method to create refresh token"""

        to_encode = data.copy()

        if expires_delta is not None:
            expires = datetime.now() + expires_delta
        else:
            expires = datetime.now() + timedelta(minutes=JWT_REFRESH_EXPIRY)

        to_encode.update({'exp': expires, 'type': 'refresh'})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)

        return encoded_jwt

    @staticmethod
    def verify_access_token(access_token: str, credentials_exception):
        """Method to verify validity of access token"""

        try:
            payload = jwt.decode(
                access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            token_type = payload.get("type")

            if not user_id:
                raise credentials_exception

            if token_type == "refresh":
                raise HTTPException(detail="Refresh token not allowed", status_code=400)

            token_data = TokenData(id=user_id)
            return token_data

        except JWTError:
            raise credentials_exception

    @staticmethod
    def verify_refresh_token(token: str, credentials_exception):
        """Method to verify validity of refresh token"""

        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            token_type = payload.get("type")

            if not user_id:
                raise credentials_exception

            if token_type == "access":
                raise HTTPException(detail="Access token not allowed", status_code=400)

            token_data = TokenData(id=user_id)
            return token_data

        except JWTError:
            raise credentials_exception

    @staticmethod
    def refresh_access_token(current_refresh_token: str):
        """Method to refresh access token with refresh token"""

        credentials_exception = HTTPException(
            status_code=401, detail="Refresh token expired"
        )

        try:
            token = AuthService.verify_refresh_token(
                current_refresh_token, credentials_exception
            )

            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )

            new_access_token = AuthService.create_access_token(data={'sub': token.id})
            new_refresh_token = AuthService.create_refresh_token(data={'sub': token.id})

            return new_access_token, new_refresh_token

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(
                status_code=500, detail="An error occured refreshing access token."
            ) from e

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str):
        """Function to authenticate a user"""

        if not is_valid_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid email address.'
            )

        user = db.query(User).filter_by(email=email).first()

        if not user or not Hasher.verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid user credentials")

        return user
