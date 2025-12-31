from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest
from app.main import app 
from app.db.database import get_db 
from app.services.auth import AuthService


def get_db_engine():
    DATABASE_URL = "sqlite:///./test.db"
        
    return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        
engine = get_db_engine()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """
    Override the get_db dependency to use a test database session.
    This function yields a database session connected to the test database.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """
    Fixture to set up and tear down the test database.
    Creates all tables before tests and drops them after tests.
    """
    from app.db.database import Base

    # Create the database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop the database tables
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_client():
    """
    Fixture to create a TestClient for FastAPI app.
    This client can be used to make requests to the app during tests.
    """

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture(scope="function")
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

# Affiliate authorization

@pytest.fixture
def verified_affiliate(db_session):
    from app.models.affiliate import Affiliate
    from app.core.hash import Hasher
    import secrets

    affiliate = Affiliate(
        first_name="Sophia",
        last_name="Johnson",
        email="sophia.johnson@example.co.uk",
        username="sophiee",
        phone_no="+123456789",
        bank="United Bank",
        account_no="0123456",
        hashed_password=Hasher.get_password_hash("@Next23rd"),
        verified=True,
        ref_code=secrets.token_urlsafe(6)
    )
    db_session.add(affiliate)
    db_session.commit()
    db_session.refresh(affiliate)
    return affiliate

@pytest.fixture
def affiliate_token(verified_affiliate):
    return AuthService.create_access_token(
        data={"sub": str(verified_affiliate.id), "role": "affiliate"}
    )

@pytest.fixture
def affiliate_client(test_client, affiliate_token):
    test_client.headers.update(
        {"Authorization": f"Bearer {affiliate_token}"}
    )
    return test_client



# ERP Authorization

@pytest.fixture
def verified_erp(db_session):
    from app.models.erp_user import ERPUser
    from app.core.hash import Hasher

    erp_user = ERPUser(
        first_name="Sophia",
        last_name="Johnson",
        email="sophia.johnson@example.co.uk",
        hashed_password=Hasher.get_password_hash("@Next23rd"),
        verified=False,
    )
    db_session.add(erp_user)
    db_session.commit()
    db_session.refresh(erp_user)
    return erp_user


@pytest.fixture
def erp_token(verified_erp):
    return AuthService.create_access_token(
        data={"sub": str(verified_erp.id), "role": "erp"}
    )

@pytest.fixture
def erp_client(test_client, erp_token):
    test_client.headers.update(
        {"Authorization": f"Bearer {erp_token}"}
    )
    return test_client