"""Document upload edge cases: each failure must give the user an actionable, plain-English reason."""

import io
import os

from pypdf import PdfWriter


def _pdf(text_pdf: bool = True, password: str | None = None, pad_mb: int = 0) -> bytes:
    from pypdf.generic import DecodedStreamObject, NameObject

    w = PdfWriter()
    w.add_blank_page(612, 792)
    if pad_mb:
        pad = DecodedStreamObject()
        pad.set_data(os.urandom(pad_mb * 1024 * 1024))
        w._root_object[NameObject("/Padding")] = w._add_object(pad)
    if password:
        w.encrypt(password)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _upload(client, name: str, data: bytes, ctype: str = "application/pdf"):
    return client.post("/documents", files={"file": (name, data, ctype)})


def test_empty_file_is_rejected_with_explanation(authed):
    r = _upload(authed, "empty.pdf", b"")
    assert r.status_code == 400
    assert "empty (0 bytes)" in r.json()["detail"]


def test_damaged_pdf_explains_problem(authed):
    r = _upload(authed, "broken.pdf", b"%PDF-1.4 this is not really a pdf")
    doc = authed.get(f"/documents/{r.json()['id']}").json()
    assert doc["status"] == "failed"
    assert "damaged or incomplete" in doc["summary"]


def test_password_protected_pdf_explains_problem(authed):
    r = _upload(authed, "locked.pdf", _pdf(password="secret"))
    doc = authed.get(f"/documents/{r.json()['id']}").json()
    assert doc["status"] == "failed"
    assert "password-protected" in doc["summary"]


def test_pdf_without_text_explains_problem(authed):
    r = _upload(authed, "blank-scan.pdf", _pdf())
    doc = authed.get(f"/documents/{r.json()['id']}").json()
    assert doc["status"] == "failed"
    assert "No readable text" in doc["summary"]


def test_large_pdf_within_limit_is_accepted(authed):
    r = _upload(authed, "big.pdf", _pdf(pad_mb=12))
    assert r.status_code == 202
    assert r.json()["size_bytes"] > 12 * 1024 * 1024
