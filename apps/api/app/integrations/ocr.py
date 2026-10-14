"""OCR adapter. Uses Tesseract when installed; otherwise a mock that reports OCR is unavailable."""

import shutil
import subprocess
import tempfile
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

    def pdf_to_text(self, path: Path, max_pages: int = 30) -> list[str]:
        """OCR a scanned (image-only) PDF: render pages with poppler's pdftoppm, then read each with tesseract."""
        if not shutil.which("pdftoppm"):
            return [""]
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["pdftoppm", "-r", "200", "-png", "-l", str(max_pages), str(path), f"{tmp}/page"],
                           capture_output=True, timeout=300, check=False)
            images = sorted(Path(tmp).glob("page*.png"))
            return [self.image_to_text(img) for img in images] or [""]


class UnavailableOCR:
    name = "unavailable"

    def image_to_text(self, path: Path) -> str:
        return ""

    def pdf_to_text(self, path: Path) -> list[str]:
        return [""]


def get_ocr_engine() -> OCREngine:
    return TesseractOCR() if shutil.which("tesseract") else UnavailableOCR()
