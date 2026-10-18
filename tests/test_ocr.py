import sys
import types

import pytest

from flutter_agent.requirements.ocr import OcrRequiredError, extract_pdf_text


def test_scanned_pdf_requires_ocr(monkeypatch, tmp_path):
    class Page:
        def extract_text(self):
            return ""

    class Reader:
        def __init__(self, path):
            self.pages = [Page()]

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=Reader))
    with pytest.raises(OcrRequiredError, match="OCR is required"):
        extract_pdf_text(tmp_path / "scan.pdf")


def test_text_pdf_is_returned_without_ocr(monkeypatch, tmp_path):
    class Page:
        def extract_text(self):
            return "Requirement one"

    class Reader:
        def __init__(self, path):
            self.pages = [Page()]

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=Reader))
    result = extract_pdf_text(tmp_path / "text.pdf")
    assert result.text == "Requirement one"
    assert not result.used_ocr
