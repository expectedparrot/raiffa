from __future__ import annotations


class RaiffaError(Exception):
    exit_code = 1
    code = "raiffa_error"

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ProjectNotFound(RaiffaError):
    exit_code = 2
    code = "missing_project"


class InvalidProject(RaiffaError):
    exit_code = 2
    code = "invalid_project"


class UserError(RaiffaError):
    exit_code = 1
    code = "user_error"


class ValidationError(RaiffaError):
    exit_code = 3
    code = "validation_error"


class AnalysisError(RaiffaError):
    exit_code = 4
    code = "analysis_error"


class ImportModelError(RaiffaError):
    exit_code = 5
    code = "import_error"
