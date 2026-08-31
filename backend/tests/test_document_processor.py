from app.services import document_processor


class FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class NativeTextPage:
    def extract_text(self):
        return "Selectable PDF text"


class ScannedPage:
    def __init__(self):
        self.resolution = None
        self.original = object()

    def extract_text(self):
        return "   "

    def to_image(self, *, resolution):
        self.resolution = resolution
        return self


def test_pdf_uses_native_text_without_ocr(monkeypatch):
    ocr_calls = []
    monkeypatch.setattr(document_processor.pdfplumber, "open", lambda _: FakePdf([NativeTextPage()]))
    monkeypatch.setattr(
        document_processor.pytesseract,
        "image_to_string",
        lambda image: ocr_calls.append(image) or "unexpected OCR",
    )

    assert document_processor._extract_pdf("native.pdf") == "Selectable PDF text"
    assert ocr_calls == []


def test_pdf_uses_ocr_for_a_page_with_no_extractable_text(monkeypatch):
    page = ScannedPage()
    monkeypatch.setattr(document_processor.pdfplumber, "open", lambda _: FakePdf([page]))
    monkeypatch.setattr(document_processor.pytesseract, "image_to_string", lambda image: "Scanned page text")

    assert document_processor._extract_pdf("scanned.pdf") == "Scanned page text"
    assert page.resolution == 300
