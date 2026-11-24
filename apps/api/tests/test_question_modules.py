import pytest

from app.services.question_modules import MODULES, QuestionValidationError, get_module
from app.services.question_modules.file_upload import check_file_content


def test_registry_has_all_required_types():
    assert set(MODULES) == {"mcq", "multiple_select", "descriptive", "file_upload", "coding"}
    with pytest.raises(QuestionValidationError):
        get_module("essay")


def test_mcq_evaluation():
    m = get_module("mcq")
    assert m.evaluate({}, {"correct": "a"}, {"selected": "a"}, 2).score == 2
    assert m.evaluate({}, {"correct": "a"}, {"selected": "b"}, 2).score == 0


def test_multiple_select_exact_and_partial():
    m = get_module("multiple_select")
    exact = {"correct": ["a", "b"], "scoring": "exact"}
    assert m.evaluate({}, exact, {"selected": ["b", "a"]}, 4).score == 4
    assert m.evaluate({}, exact, {"selected": ["a"]}, 4).score == 0
    partial = {"correct": ["a", "b", "c", "d"], "scoring": "partial"}
    assert m.evaluate({}, partial, {"selected": ["a", "b"]}, 4).score == 2
    assert m.evaluate({}, partial, {"selected": ["a", "x"]}, 4).score == 0  # penalty floors at 0
    assert m.evaluate({}, partial, {"selected": []}, 4).score == 0


def test_descriptive_and_coding_are_pending():
    assert get_module("descriptive").evaluate({}, {}, {"text": "x"}, 5).status == "pending"
    assert get_module("coding").evaluate({}, {}, {}, 5).status == "pending"


def test_coding_response_validation():
    m = get_module("coding")
    prompt = {"languages": ["python3"]}
    assert m.validate_response(prompt, {"language": "python3", "source_code": "print(1)"})
    with pytest.raises(QuestionValidationError):
        m.validate_response(prompt, {"language": "java", "source_code": "x"})
    with pytest.raises(QuestionValidationError):
        m.validate_response(prompt, {"language": "python3", "source_code": "x" * (65 * 1024)})


def test_file_content_checks():
    check_file_content("txt", "héllo".encode())
    check_file_content("png", b"\x89PNG\r\n\x1a\n....")
    for ext, data in (
        ("png", b"MZ\x90\x00 executable pretending"),
        ("pdf", b"not a pdf"),
        ("txt", b"binary\x00data"),
        ("txt", b"\xff\xfe\xfa"),
        ("exe", b"MZ"),
    ):
        with pytest.raises(QuestionValidationError):
            check_file_content(ext, data)


def test_file_upload_module_rejects_inline_payloads():
    with pytest.raises(QuestionValidationError):
        get_module("file_upload").validate_response({}, {"file_id": "x"})
