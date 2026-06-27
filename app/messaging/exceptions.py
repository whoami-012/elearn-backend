from typing import Any

from fastapi import HTTPException, status


def messaging_error(status_code: int, code: str, message: str, headers: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers=headers,
    )


def forbidden(code: str, message: str) -> HTTPException:
    return messaging_error(status.HTTP_403_FORBIDDEN, code, message)


def not_found(code: str, message: str) -> HTTPException:
    return messaging_error(status.HTTP_404_NOT_FOUND, code, message)


def unprocessable(code: str, message: str) -> HTTPException:
    return messaging_error(status.HTTP_422_UNPROCESSABLE_ENTITY, code, message)
