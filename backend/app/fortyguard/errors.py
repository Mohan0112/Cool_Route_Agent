class FortyGuardError(Exception):
    """Base error for anything that goes wrong talking to the FortyGuard API."""


class ValidationError(FortyGuardError):
    """Client-side validation failed before any network call was made."""


class FortyGuardApiError(FortyGuardError):
    def __init__(self, status_code: int, message: str, body: dict | None = None):
        super().__init__(f"FortyGuard API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.body = body or {}


class PlanRestrictedError(FortyGuardApiError):
    """Raised when the trial key doesn't have access to a Premium-tier endpoint (HTTP 403)."""
