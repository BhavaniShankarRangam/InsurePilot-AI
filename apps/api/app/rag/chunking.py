"""Section-aware chunking that preserves page numbers for citations."""

import re
from dataclasses import dataclass, field

from app.rag.text import approx_tokens

# A header is a short line written entirely in capitals, e.g. "SECTION 4 — COLLISION COVERAGE".
SECTION_HEADER = re.compile(r"^(?=[^a-z\n]{6,110}$)(?=[^\n]*[A-Z]{4})[A-Z0-9 —–\-:&,/().']+$", re.MULTILINE)
_KEEP_UPPER = re.compile(r"^(?:[IVX]+|[A-Z]|[A-Z]{1,3}-[A-Z]{1,3}|EOB|HMO|PPO|CPT|HO-\d)$")
_SMALL = {"and", "or", "of", "the", "to", "for", "an", "in", "on"}


def nice_section(header: str) -> str:
    words = header.split()
    out = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in _SMALL:
            out.append(w.lower())
        elif _KEEP_UPPER.match(w):
            out.append(w)
        else:
            out.append(w.capitalize())
    return " ".join(out)


@dataclass
class Page:
    number: int
    text: str


@dataclass
class Chunk:
    ordinal: int
    content: str
    page: int
    section: str | None
    meta: dict = field(default_factory=dict)

    @property
    def token_count(self) -> int:
        return approx_tokens(self.content)


def clean_text(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_pages(pages: list[Page], max_words: int = 170, overlap_words: int = 30) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_section: str | None = None

    for page in pages:
        text = clean_text(page.text)
        # Split the page into blocks that each start at a section header.
        blocks: list[tuple[str | None, str]] = []
        last = 0
        for m in SECTION_HEADER.finditer(text):
            if m.start() > last:
                blocks.append((current_section, text[last : m.start()]))
            current_section = nice_section(m.group(0).strip().rstrip(":"))
            last = m.start()
        blocks.append((current_section, text[last:]))

        for section, block in blocks:
            words = block.split()
            if not words:
                continue
            start = 0
            while start < len(words):
                window = words[start : start + max_words]
                chunks.append(Chunk(len(chunks), " ".join(window), page.number, section))
                if start + max_words >= len(words):
                    break
                start += max_words - overlap_words
    return chunks
