from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import pytest
from app.main import app 
from app.db.database import get_db 


@pytest.fixture
def mock_db_session():
    """
    Fixture to create a mock database session.
    This mock can be used to simulate database interactions during tests.
    """
    mock_session = MagicMock()
    yield mock_session
    mock_session.reset_mock()


@pytest.fixture
def test_client():
    """
    Fixture to create a TestClient for FastAPI app.
    This client can be used to make requests to the app during tests.
    """

    app.dependency_overrides[get_db] = lambda: mock_db_session
    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
