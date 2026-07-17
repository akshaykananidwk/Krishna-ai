"""Domain exceptions and their mapping to HTTP responses.

Services raise these transport-agnostic errors; a single exception handler in
:mod:`app.main` translates them to JSON HTTP responses.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all expected application errors."""

    status_code: int = 400
    error_code: str = "app_error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.__doc__ or "Application error"
        super().__init__(self.detail)


class EmailAlreadyRegisteredError(AppError):
    """An account with this email already exists."""

    status_code = 409
    error_code = "email_already_registered"


class InvalidCredentialsError(AppError):
    """The email or password is incorrect."""

    status_code = 401
    error_code = "invalid_credentials"


class InactiveUserError(AppError):
    """This account has been deactivated."""

    status_code = 403
    error_code = "inactive_user"


class InvalidTokenError(AppError):
    """The provided token is invalid or has expired."""

    status_code = 401
    error_code = "invalid_token"
