import pytest

from app.rag.chunking import Page, chunk_pages, nice_section
from app.rag.embeddings import HashingEmbedder, cosine
from app.rag.ingest import classify, extract_structured
from app.rag.retriever import HybridRetriever, RetrievalFilters


def test_chunking_tracks_sections_and_pages():
    pages = [Page(4, "SECTION 4 — COLLISION COVERAGE\nWe will pay for loss. " * 3), Page(5, "More collision text.")]
    chunks = chunk_pages(pages)
    assert chunks[0].section == "Section 4 — Collision Coverage"
    assert chunks[0].page == 4
    assert chunks[-1].section == "Section 4 — Collision Coverage"  # section carries across pages
    assert chunks[-1].page == 5


def test_nice_section_keeps_codes():
    assert nice_section("ENDORSEMENT HO-WB — WATER BACKUP AND SUMP") == "Endorsement HO-WB — Water Backup and Sump"


def test_hashing_embedder_similarity():
    e = HashingEmbedder(384)
    a, b, c = e.embed(["collision deductible", "deductible for collision", "pet wellness exam"])
    assert cosine(a, b) > cosine(a, c)


def test_classify_and_extract():
    doc_type, conf = classify("EXPLANATION OF BENEFITS. This is not a bill. Allowed amount $4,300. Plan paid $1,540.")
    assert doc_type == "eob" and conf in ("high", "moderate")
    ex = extract_structured("Amount due $2,760.00. Please pay by March 3, 2026. You must submit proof within 60 days.")
    assert 2760.0 in ex["monetary_amounts"]
    assert ex["action_items"]


@pytest.mark.parametrize("query,expected", [
    ("collision deductible", "Collision Coverage"),
    ("water backup through drains endorsement", "HO-WB"),
    ("MRI prior authorization", "Prior Authorization"),
    ("contingent beneficiary probate", "Beneficiaries"),
])
def test_hybrid_retrieval_top_hit(db, demo_user_id, query, expected):
    hits = HybridRetriever(db).search(query, RetrievalFilters(user_id=demo_user_id), top_k=3)
    assert hits, "no results"
    assert expected in hits[0].citation().label


def test_retrieval_respects_user_isolation(db):
    assert HybridRetriever(db).search("collision", RetrievalFilters(user_id="someone-else")) == []


def test_metadata_filter_by_category(db, demo_user_id):
    hits = HybridRetriever(db).search("deductible", RetrievalFilters(user_id=demo_user_id, categories=["health"]), top_k=5)
    assert hits and all(h.chunk.meta.get("category") == "health" for h in hits)
