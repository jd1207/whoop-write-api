from whoop.exceptions import WhoopAuthError, WhoopAPIError, WhoopRateLimitError


def test_auth_error():
    err = WhoopAuthError("invalid token")
    assert str(err) == "invalid token"
    assert isinstance(err, WhoopAPIError)


def test_rate_limit_error():
    err = WhoopRateLimitError(retry_after=60)
    assert err.retry_after == 60
    assert isinstance(err, WhoopAPIError)


def test_api_error_with_status():
    err = WhoopAPIError("not found", status_code=404, response_body='{"error":"not found"}')
    assert err.status_code == 404
    assert err.response_body == '{"error":"not found"}'
