import jwt
import requests
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from typing import Annotated
from app.core.base.services import Service
from app.core.hash import Hasher
from app.db.database import get_db
from app.models.affiliate import Affiliate
from app.schemas.user import (
    RegisterBase,
    TokenData,
    AccountVerificationRequest
)
from app.utils.settings import settings
from app.utils.validators import is_valid_email


ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
JWT_REFRESH_EXPIRY = settings.JWT_REFRESH_EXPIRY
ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

PAYSTACK_BASE_URL = "https://api.paystack.co"


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")


class AuthService(Service[Affiliate, RegisterBase]):
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
            expires = datetime.now() + timedelta(minutes=JWT_REFRESH_EXPIRY)

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
    def verify_magic_link(
        db: Session, magic_token: str, credentials_exception
    ) -> Affiliate:
        """Method to verify validity of magic token"""

        try:
            payload = jwt.decode(
                magic_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            affiliate_id = payload.get("sub")
            token_type = payload.get("type")

            if not affiliate_id:
                raise credentials_exception

            if token_type != "magic_link":
                raise HTTPException(detail="Invalid token type", status_code=400)

            affiliate = db.query(Affiliate).get(affiliate_id)
            if not affiliate:
                raise HTTPException(status_code=404, detail="affiliate not found")

            return affiliate
        
        except (ExpiredSignatureError, JWTError):
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

            new_access_token = AuthService.create_access_token(data={"sub": token.id})
            new_refresh_token = AuthService.create_refresh_token(data={"sub": token.id})

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
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address."
            )

        affiliate = db.query(Affiliate).filter_by(email=email).first()

        try:
            if not affiliate or not Hasher.verify_password(
                password, affiliate.hashed_password
            ):
                raise HTTPException(
                    status_code=401, detail="Invalid affiliate credentials"
                )
            
            if not affiliate.verified:
                raise HTTPException(
                    status_code=401, detail="User profile verification required"
                )

            return affiliate

        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",  # hide true error e.g invalid salt
            )

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
            affiliate_id: str = payload.get("sub")

            if affiliate_id is None:
                raise credentials_exception

            token_data = TokenData(id=affiliate_id)

        except InvalidTokenError:
            raise credentials_exception

        affiliate = db.query(Affiliate).filter(Affiliate.id == token_data.id).first()

        if affiliate is None:
            raise credentials_exception

        if not affiliate.verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User has not been verified",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return affiliate

    @staticmethod
    def verify_bank_information(request: AccountVerificationRequest):
        # Fetch banks from Paystack
        banks_url = f"{PAYSTACK_BASE_URL}/bank"
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

        banks_response = requests.get(banks_url, headers=headers)
        banks_data = banks_response.json()

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

        # Verify acc no
        resolve_url = f"{PAYSTACK_BASE_URL}/bank/resolve"
        params = {"account_number": request.account_number, "bank_code": bank_code}

        verify_response = requests.get(resolve_url, headers=headers, params=params)
        verify_data = verify_response.json()

        print(verify_data)

        if not verify_data.get("status"):
            raise HTTPException(status_code=400, detail="Unable to verify account")

        account_name: str = verify_data["data"]["account_name"].lower()

        # Compare names
        if (
            request.first_name.lower() in account_name.split()
            and request.last_name.lower() in account_name.split()
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
