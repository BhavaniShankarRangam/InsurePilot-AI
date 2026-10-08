"""OCR adapter. Uses Tesseract when installed; otherwise a mock that reports OCR is unavailable."""

import shutil
import subprocess
from pathlib import Path
from typing import Protocol


class OCREngine(Protocol):
    name: str

    def image_to_text(self, path: Path) -> str: ...

    def pdf_to_text(self, path: Path) -> list[str]: ...


class TesseractOCR:
    name = "tesseract"

    def image_to_text(self, path: Path) -> str:
        out = subprocess.run(["tesseract", str(path), "-", "--psm", "3"], capture_output=True, text=True, timeout=60)
        return out.stdout

    def pdf_to_text(self, path: Path) -> list[str]:
        # Rasterizing PDFs requires poppler; scanned PDFs fall back to empty pages without it.
        return [""]


class UnavailableOCR:
    name = "unavailable"

    def image_to_text(self, path: Path) -> str:
        return ""

    def pdf_to_text(self, path: Path) -> list[str]:
        return [""]


def get_ocr_engine() -> OCREngine:
    return TesseractOCR() if shutil.which("tesseract") else UnavailableOCR()
