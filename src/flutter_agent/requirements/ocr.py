from dataclasses import dataclass
from pathlib import Path


class OcrRequiredError(RuntimeError):
    """Raised when a PDF has no usable text layer."""


@dataclass(frozen=True)
class PdfExtractionResult:
    text: str
    pages: int
    used_ocr: bool = False
    ocr_available: bool = False


def extract_pdf_text(path: Path, *, use_ocr: bool = False) -> PdfExtractionResult:
    """Extract text from a PDF, optionally using the local OCR toolchain.

    `pypdf` is optional so the core agent remains lightweight. OCR additionally
    requires `pdf2image` and `pytesseract` plus a local Tesseract installation.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF support requires optional dependency 'pypdf'") from exc

    reader = PdfReader(str(path))
    pages_text = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(item for item in pages_text if item)
    if text:
        return PdfExtractionResult(text, len(reader.pages), False, False)

    try:
        import pytesseract
        from pdf2image import convert_from_path
        ocr_available = True
    except ImportError:
        ocr_available = False
        pytesseract = None
        convert_from_path = None

    if not use_ocr:
        raise OcrRequiredError(
            f"{path.name} contains no extractable text. OCR is required; install optional OCR dependencies and retry with use_ocr=True."
        )
    if not ocr_available:
        raise OcrRequiredError("OCR requires optional dependencies 'pdf2image' and 'pytesseract'")

    images = convert_from_path(str(path))
    ocr_pages = [pytesseract.image_to_string(image).strip() for image in images]
    ocr_text = "\n\n".join(item for item in ocr_pages if item)
    if not ocr_text:
        raise OcrRequiredError(f"OCR produced no readable text for {path.name}")
    return PdfExtractionResult(ocr_text, len(reader.pages), True, True)
