from __future__ import annotations


class AppError(Exception):
    """Base application error mapped to HTTP responses."""

    def __init__(self, message: str, *, code: str = "error", status_code: int = 400) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class ResourceNotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", *, code: str = "not_found") -> None:
        super().__init__(message, code=code, status_code=404)


class ValidationAppError(AppError):
    def __init__(self, message: str, *, code: str = "validation_error") -> None:
        super().__init__(message, code=code, status_code=422)
