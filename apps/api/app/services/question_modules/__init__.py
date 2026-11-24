from app.services.question_modules.base import QuestionModule, QuestionValidationError
from app.services.question_modules.coding import CodingModule
from app.services.question_modules.descriptive import DescriptiveModule
from app.services.question_modules.file_upload import FileUploadModule
from app.services.question_modules.mcq import McqModule
from app.services.question_modules.multiple_select import MultipleSelectModule

MODULES: dict[str, QuestionModule] = {
    m.question_type: m
    for m in (
        McqModule(),
        MultipleSelectModule(),
        DescriptiveModule(),
        FileUploadModule(),
        CodingModule(),
    )
}


def get_module(question_type: str) -> QuestionModule:
    try:
        return MODULES[question_type]
    except KeyError as exc:
        raise QuestionValidationError(
            f"unknown question_type '{question_type}'; supported: {sorted(MODULES)}"
        ) from exc


__all__ = ["MODULES", "QuestionValidationError", "get_module"]
