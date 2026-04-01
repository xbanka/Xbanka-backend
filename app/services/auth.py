from datetime import datetime, timedelta
from typing import Annotated, Optional, Union

import jwt
import requests
import logging
from requests.exceptions import RequestException
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from app.core.base.services import Service
from app.core.enums import AuthProviderEnum
from app.core.hash import Hasher
from app.db.database import get_db
from app.models.affiliate import Affiliate
from app.models.erp_user import ERPUser
from app.schemas.user import AccountVerificationRequest, TokenData
from app.utils.schema import CurrentUser
from app.utils.settings import settings
from app.utils.validators import is_valid_email

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
JWT_REFRESH_EXPIRY = settings.JWT_REFRESH_EXPIRY
ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
NUBAN_SECRET_KEY = settings.NUBAN_SECRET_KEY

PAYSTACK_BASE_URL = "https://api.paystack.co"
NUBAN_BASE_URL = "https://app.nuban.com.ng/api"


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

logger = logging.getLogger(__name__)


class AuthService(Service):
    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta | None = None):
        """Method to create access token"""
        to_encode = data.copy()

        if expires_delta is not None:
            expires = datetime.now() + expires_delta
        else:
            expires = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expires, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)

        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
        """Method to create refresh token"""

        to_encode = data.copy()

        if expires_delta is not None:
            expires = datetime.now() + expires_delta
        else:
            expires = datetime.now() + timedelta(days=JWT_REFRESH_EXPIRY)

        to_encode.update({"exp": expires, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)

        return encoded_jwt

    @staticmethod
    def create_magic_link_token(data: dict, expires_delta: timedelta | None = None):
        """Method to create access token"""
        to_encode = data.copy()

        if expires_delta is not None:
            expires = datetime.now() + expires_delta
        else:
            expires = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expires, "type": "magic_link"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)

        return encoded_jwt

    @staticmethod
    def create_password_reset_token(data: dict, expires_delta: timedelta | None = None):
        """Method to create access token"""
        to_encode = data.copy()

        if expires_delta is not None:
            expires = datetime.now() + expires_delta
        else:
            expires = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expires, "type": "password_reset"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)

        return encoded_jwt

    @staticmethod
    def verify_magic_link(
        db: Session, model, magic_token: str, credentials_exception
    ) -> Affiliate:
        """Method to verify validity of magic token"""

        try:
            payload = jwt.decode(
                magic_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            token_type = payload.get("type")

            if not user_id:
                raise credentials_exception

            if token_type != "magic_link":
                raise HTTPException(detail="Invalid token type", status_code=400)

            user = db.query(model).get(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="user not found")

            return user

        except (ExpiredSignatureError, JWTError, DecodeError):
            raise credentials_exception

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

        except (JWTError, DecodeError, ExpiredSignatureError):
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

        except (ExpiredSignatureError, JWTError, DecodeError):
            raise credentials_exception

    @staticmethod
    def verify_password_reset_token(access_token: str, credentials_exception):
        """Method to verify validity of access token"""

        try:
            payload = jwt.decode(
                access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            token_type = payload.get("type")

            if not user_id:
                raise credentials_exception

            if token_type != "password_reset":
                raise HTTPException(detail="Invalid token", status_code=400)

            token_data = TokenData(id=user_id)
            return token_data

        except (JWTError, DecodeError, ExpiredSignatureError):
            raise credentials_exception

    @staticmethod
    def refresh_access_token(current_refresh_token: str, role: str):
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

            payload = {"sub": str(token.id), "role": role}

            new_access_token = AuthService.create_access_token(data=payload)
            new_refresh_token = AuthService.create_refresh_token(data=payload)

            return new_access_token, new_refresh_token

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred refreshing access token: {str(e)}",
            ) from e

    @staticmethod
    def authenticate_user(db: Session, model, email: str, password: str):
        """Function to authenticate a user"""

        if not is_valid_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address."
            )

        user: Optional[Union[ERPUser, Affiliate]] = (
            db.query(model).filter_by(email=email).first()
        )

        # check if auth provider is google and if so, prevent password login
        if model is Affiliate and user and user.auth_provider == AuthProviderEnum.google:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User registered with Google. Please use Google login.",
            )

        if user and not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User has no password set. Please use magic link to complete signup.",
            )

        if not user or not Hasher.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",  # hide true error e.g invalid salt
            )

        if not user.verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User profile verification required",
            )

        return user

    @staticmethod
    def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)
    ):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            user_role = payload.get("role")

            if user_id is None:
                raise credentials_exception

            token_data = TokenData(id=user_id)

        except (InvalidTokenError, ExpiredSignatureError, DecodeError):
            raise credentials_exception

        if user_role == "affiliate":
            user = db.query(Affiliate).filter(Affiliate.id == token_data.id).first()

            if user and not user.verified:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User has not been verified",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        elif user_role == "erp" or user_role == "super":
            user = db.query(ERPUser).filter_by(id=user_id).first()
        else:
            raise HTTPException(401, "Invalid user type")

        if user is None:
            raise credentials_exception

        return CurrentUser(user, user_role)

    @staticmethod
    def verify_bank_information(request: AccountVerificationRequest):
        # Fetch banks from Paystack
        banks_url = f"{PAYSTACK_BASE_URL}/bank"
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

        try:
            banks_response = requests.get(banks_url, headers=headers)
            banks_data = banks_response.json()
        except RequestException as e:
            logger.error(f"Error fetching banks list from Paystack: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to fetch banks list"
            ) from e

        if not banks_data.get("status"):
            raise HTTPException(status_code=500, detail="Failed to fetch banks list")

        # Match bank name to code
        bank = next(
            (
                b
                for b in banks_data["data"]
                if b["name"].lower() == request.bank_name.lower()
            ),
            None,
        )

        if not bank:
            raise HTTPException(status_code=400, detail="Bank not found")

        bank_code = bank["code"]

        # Verify acc no using NUBAN api
        resolve_url = f"{NUBAN_BASE_URL}/{NUBAN_SECRET_KEY}"
        params = {"acc_no": request.account_number, "bank_code": bank_code}

        try:
            verify_response = requests.get(resolve_url, headers=headers, params=params)
            verify_data = verify_response.json()
        except RequestException as e:
            logger.error(f"Error verifying account information with NUBAN: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to verify account information"
            ) from e

        if isinstance(verify_data, dict) and verify_data.get("error"):
            raise HTTPException(
                status_code=400,
                detail=f"Account verification failed: {verify_data.get('message', 'Unknown error')}",
            )

        if isinstance(verify_data, list):
            if not verify_data:
                raise HTTPException(
                    status_code=400,
                    detail="Account verification failed: No data returned from NUBAN",
                )
            verify_data = verify_data[0]

        if not verify_data.get("account_name"):
            raise HTTPException(
                status_code=400,
                detail="Account verification failed: No account name returned from NUBAN",
            )

        account_name: str = verify_data["account_name"]

        # Compare names
        if (
            request.first_name.lower() in account_name.lower().split()
            and request.last_name.lower() in account_name.lower().split()
        ):
            return {
                "status": "success",
                "message": "Account verified successfully",
                "verified_name": account_name,
                "bank": request.bank_name,
            }

        raise HTTPException(
            status_code=400,
            detail=f"Provided name '{request.last_name} {request.first_name}' does not match account name '{account_name}'",
        )

    @staticmethod
    def resend_verification_email(request: AccountVerificationRequest):
        # Logic to resend verification email
        # This is a placeholder implementation
        return {
            "message": f"Verification email resent to {request.first_name} {request.last_name}"
        }

    @staticmethod
    def update_user_password(
        db: Session, data: TokenData, new_password: str, user_service
    ):
        """Method to update user's password"""
        try:
            user = user_service.get_user_by_id(db, data.id)

            hashed_password = Hasher.get_password_hash(new_password)

            user.hashed_password = hashed_password
            db.commit()
            db.refresh(user)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"An error occurred updating password: {str(e)}"
            ) from e
