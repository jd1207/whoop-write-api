import pytest
import respx
import httpx

@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://api.prod.whoop.com") as respx_mock:
        yield respx_mock

@pytest.fixture
def mock_oauth():
    with respx.mock(base_url="https://api-7.whoop.com") as respx_mock:
        yield respx_mock

@pytest.fixture
def mock_cognito():
    with respx.mock(base_url="https://cognito-idp.us-west-2.amazonaws.com") as respx_mock:
        yield respx_mock

@pytest.fixture
def fake_token():
    return "fake-bearer-token-12345"
