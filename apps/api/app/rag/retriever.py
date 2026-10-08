"""Hybrid retrieval: metadata filter → vector + BM25 → RRF fusion → rerank → compression."""

import math
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.rag.embeddings import cosine, get_embedder
from app.rag.text import split_sentences, tokenize


@dataclass
class RetrievalFilters:
    user_id: str
    policy_id: str | None = None
    claim_id: str | None = None
    doc_types: list[str] | None = None
    categories: list[str] | None = None


@dataclass
class Citation:
    document_id: str
    document_title: str
    section: str | None
    page: int | None
    chunk_id: str
    snippet: str

    @property
    def label(self) -> str:
        parts = [self.document_title]
        if self.section:
            parts.append(self.section)
        if self.page:
            parts.append(f"Page {self.page}")
        return " · ".join(parts)

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "document_title": self.document_title,
            "section": self.section,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "snippet": self.snippet,
            "label": self.label,
        }


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    document: Document
    score: float
    vector_score: float
    bm25_score: float
    compressed: str = ""
    signals: dict = field(default_factory=dict)

    def citation(self) -> Citation:
        snippet = self.compressed or self.chunk.content[:280]
        return Citation(
            self.document.id, self.document.title, self.chunk.section, self.chunk.page, self.chunk.id, snippet
        )


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.4, b: float = 0.75) -> None:
        self.docs = docs
        self.k1, self.b = k1, b
        self.avgdl = sum(len(d) for d in docs) / max(1, len(docs))
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tfs = [Counter(d) for d in docs]

    def score(self, query: list[str], idx: int) -> float:
        tf, dl = self.tfs[idx], len(self.docs[idx])
        s = 0.0
        for t in query:
            if t not in tf:
                continue
            f = tf[t]
            s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s


class HybridRetriever:
    RRF_K = 60

    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedder = get_embedder()

    def _candidates(self, f: RetrievalFilters) -> list[tuple[DocumentChunk, Document]]:
        stmt = (
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.user_id == f.user_id, Document.status == "ready")
        )
        if f.policy_id:
            stmt = stmt.where(DocumentChunk.policy_id == f.policy_id)
        if f.claim_id:
            stmt = stmt.where(DocumentChunk.claim_id == f.claim_id)
        if f.doc_types:
            stmt = stmt.where(Document.doc_type.in_(f.doc_types))
        rows = self.db.execute(stmt).all()
        if f.categories:
            rows = [r for r in rows if r[0].meta.get("category") in f.categories]
        return [(r[0], r[1]) for r in rows]

    def _vector_ranking(self, query_vec: list[float], cands: list[tuple[DocumentChunk, Document]]) -> list[float]:
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql" and cands:
            ids = [c.id for c, _ in cands]
            from pgvector.sqlalchemy import Vector
            from sqlalchemy import Float, cast, literal

            # pgvector cosine distance operator; explicit cast because the column is a TypeDecorator.
            qv = cast(literal(str([round(x, 7) for x in query_vec])), Vector(len(query_vec)))
            dist = DocumentChunk.embedding.op("<=>", return_type=Float)(qv)
            rows = self.db.execute(select(DocumentChunk.id, dist).where(DocumentChunk.id.in_(ids))).all()
            by_id = {r[0]: 1 - float(r[1]) for r in rows}
            return [by_id.get(c.id, 0.0) for c, _ in cands]
        return [cosine(query_vec, c.embedding) if c.embedding else 0.0 for c, _ in cands]

    def search(self, query: str, filters: RetrievalFilters, top_k: int = 5, min_score: float = 0.0) -> list[RetrievedChunk]:
        cands = self._candidates(filters)
        if not cands:
            return []
        q_tokens = tokenize(query)
        q_vec = self.embedder.embed([query])[0]

        vec_scores = self._vector_ranking(q_vec, cands)
        bm25 = BM25([tokenize(f"{c.section or ''} {c.content}") for c, _ in cands])
        bm_scores = [bm25.score(q_tokens, i) for i in range(len(cands))]

        vec_rank = {i: r for r, i in enumerate(sorted(range(len(cands)), key=lambda i: -vec_scores[i]))}
        bm_rank = {i: r for r, i in enumerate(sorted(range(len(cands)), key=lambda i: -bm_scores[i]))}
        fused = [1 / (self.RRF_K + vec_rank[i]) + 1 / (self.RRF_K + bm_rank[i]) for i in range(len(cands))]

        pool = sorted(range(len(cands)), key=lambda i: -fused[i])[: max(top_k * 4, 12)]
        results: list[RetrievedChunk] = []
        q_set = set(q_tokens)
        hinted = self._category_hints(query) if not filters.categories else set()
        for i in pool:
            chunk, doc = cands[i]
            rerank = self._rerank_score(q_set, chunk)
            score = 0.45 * rerank + 0.35 * max(0.0, vec_scores[i]) + 0.20 * min(1.0, bm_scores[i] / 12)
            if hinted and chunk.meta.get("category") in hinted:
                score += 0.12  # soft metadata boost when the query names an insurance line
            if bm_scores[i] == 0 and vec_scores[i] < 0.12:
                continue
            results.append(
                RetrievedChunk(chunk, doc, score, vec_scores[i], bm_scores[i], signals={"rerank": round(rerank, 3)})
            )
        results.sort(key=lambda r: -r.score)
        results = [r for r in results if r.score >= min_score][:top_k]
        for r in results:
            r.compressed = self.compress(query, r.chunk.content)
        return results

    @staticmethod
    def _category_hints(query: str) -> set[str]:
        from app.ai.agents.intent import CATEGORY_TERMS

        lower = query.lower()
        return {cat for cat, terms in CATEGORY_TERMS.items() if any(t in lower for t in terms)}

    @staticmethod
    def _rerank_score(q_set: set[str], chunk: DocumentChunk) -> float:
        """Lightweight cross-feature reranker: term coverage + section-title match.

        Pluggable: replace with a cross-encoder / Cohere Rerank in production.
        """
        if not q_set:
            return 0.0
        body = set(tokenize(chunk.content))
        title = set(tokenize(chunk.section or ""))
        coverage = len(q_set & body) / len(q_set)
        title_hit = len(q_set & title) / len(q_set)
        return min(1.0, 0.75 * coverage + 0.5 * title_hit)

    @staticmethod
    def compress(query: str, content: str, max_sentences: int = 3) -> str:
        q = set(tokenize(query))
        sentences = split_sentences(content)
        if len(sentences) <= max_sentences:
            return content
        scored = sorted(
            range(len(sentences)), key=lambda i: -len(q & set(tokenize(sentences[i])))
        )[:max_sentences]
        return " ".join(sentences[i] for i in sorted(scored))
