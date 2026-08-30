"""Consistent, namespaced error schema for the whole API.

Every error response has the shape:
    { "error_code": "...", "message": "...", "details": {...} }

Error codes are namespaced per the platform's own design spec (thesis section 12.2):
AUTH_*, VALIDATION_*, SME_*, INVESTMENT_*, RISK_MODEL_*, SYSTEM_*.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, error_code: str, message: str, http_status: int = 400, details: dict | None = None):
        self.error_code = error_code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        super().__init__(message)


# --- convenience constructors, grouped by namespace -----------------------

def auth_error(code: str, message: str, details: dict | None = None) -> AppError:
    return AppError(f"AUTH_{code}", message, status.HTTP_401_UNAUTHORIZED, details)


def validation_error(code: str, message: str, details: dict | None = None) -> AppError:
    return AppError(f"VALIDATION_{code}", message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


def sme_error(code: str, message: str, http_status: int = status.HTTP_404_NOT_FOUND, details: dict | None = None) -> AppError:
    return AppError(f"SME_{code}", message, http_status, details)


def investment_error(code: str, message: str, http_status: int = status.HTTP_400_BAD_REQUEST, details: dict | None = None) -> AppError:
    return AppError(f"INVESTMENT_{code}", message, http_status, details)


def risk_model_error(code: str, message: str, details: dict | None = None) -> AppError:
    return AppError(f"RISK_MODEL_{code}", message, status.HTTP_200_OK, details)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.http_status,
            content={"error_code": exc.error_code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        code = "MISSING_FIELD" if first.get("type") == "missing" else "INVALID_INPUT"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": f"VALIDATION_{code}",
                "message": f"Invalid request: {field or 'payload'} ({first.get('msg', 'invalid')})",
                "details": {"errors": errors},
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "SYSTEM_UNAVAILABLE",
                "message": "Something went wrong on our side. Please try again shortly.",
                "details": {},
            },
        )
