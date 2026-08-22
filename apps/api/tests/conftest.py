import pytest
from fastapi.testclient import TestClient

from intentfence_api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
