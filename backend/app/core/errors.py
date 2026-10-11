from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str, **extra: object) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class NotFound(AppError):
    status_code = 404


class Conflict(AppError):
    status_code = 409


class InsufficientStock(Conflict):
    def __init__(self, sku: str, available: int, requested: int) -> None:
        super().__init__(
            f"Only {available} unit(s) of {sku} available, {requested} requested.",
            sku=sku,
            available=available,
        )


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse({"detail": exc.detail, **exc.extra}, status_code=exc.status_code)
