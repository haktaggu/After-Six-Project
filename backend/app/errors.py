from app.schemas import FieldError


class ApiProblem(Exception):
    def __init__(self, status: int, code: str, message: str, fields: list[FieldError] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = [] if fields is None else fields


class ScaffoldPending(NotImplementedError):
    pass
