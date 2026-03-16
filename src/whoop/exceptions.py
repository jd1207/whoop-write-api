class WhoopAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class WhoopAuthError(WhoopAPIError):
    pass


class WhoopRateLimitError(WhoopAPIError):
    def __init__(self, retry_after: int, message: str = "rate limited"):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after
