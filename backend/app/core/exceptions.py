from typing import Optional

from fastapi import HTTPException


class TransactionAPIException(HTTPException):
    def __init__(
            self,
            status_code: int,
            detail: str,
            error_code: Optional[str] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class GmailAPIError(TransactionAPIException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="GMAIL_API_ERROR"
        )


class ClassificationError(TransactionAPIException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="CLASSIFICATION_ERROR"
        )
