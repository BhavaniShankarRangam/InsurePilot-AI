import re

_TOKEN = re.compile(r"[a-z0-9$]+(?:[.,][0-9]+)?")
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from has have how i if in is it its my of on or our "
    "that the their this to was we what when where which who why will with you your me am should".split()
)


def tokenize(text: str, drop_stopwords: bool = True) -> list[str]:
    tokens = _TOKEN.findall(text.lower())
    if drop_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return [_stem(t) for t in tokens]


def _stem(token: str) -> str:
    for suffix in ("ing", "ies", "es", "s", "ed"):
        if len(token) > 4 and token.endswith(suffix):
            return token[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return token


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(\"'])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)
