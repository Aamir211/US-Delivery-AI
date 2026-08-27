"""Deterministic retrieval over the supplied Markdown knowledge base only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[a-z0-9_]{3,}")
# Exact issue codes in the supplied documentation contain an underscore (for
# example, ERR_CONNECTION_TIMEOUT). Plain uppercase words such as API are not
# error evidence and must not make an unrelated document a known issue.
ERROR_PATTERN = re.compile(r"(?:\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b|\b\d{3}\s+Forbidden:\s+[a-z_]+\b)")
STOP_WORDS = {"about", "after", "also", "and", "are", "but", "can", "error", "for", "from", "have", "into", "issue", "its", "not", "our", "please", "reports", "the", "this", "that", "their", "they", "was", "with", "you", "your"}
GENERIC_HEADING_TOKENS = {"common", "core", "data", "faq", "guide", "guides", "module", "modules", "new", "overview", "product", "products", "recommended", "reference", "role", "roles", "scenario", "scenarios", "step", "steps", "support", "user", "users"}
PRODUCT_DOCUMENT_SLUGS = {
    "analyticshub": "analyticshub",
    "cloudsync": "cloudsync",
    "databridge pro": "databridge-pro",
    "securevault": "securevault",
    "workflowengine": "workflowengine",
}


@dataclass(frozen=True, slots=True)
class KnowledgeBaseChunk:
    document_path: str
    headings: tuple[str, ...]
    content: str


@dataclass(frozen=True, slots=True)
class RetrievalMatch:
    chunk: KnowledgeBaseChunk
    score: int


def _tokens(text: str) -> set[str]:
    return {token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOP_WORDS}


class KnowledgeBaseRetriever:
    """Simple lexical retriever sized for the supplied nine-document corpus."""

    def __init__(self, knowledge_base_directory: Path, project_root: Path) -> None:
        self._knowledge_base_directory = knowledge_base_directory
        self._project_root = project_root
        self._chunks = self._load_chunks()

    def _load_chunks(self) -> tuple[KnowledgeBaseChunk, ...]:
        chunks: list[KnowledgeBaseChunk] = []
        for path in sorted(self._knowledge_base_directory.rglob("*.md")):
            sections = path.read_text(encoding="utf-8").split("\n---\n")
            for section in sections:
                headings = tuple(line.lstrip("#").strip() for line in section.splitlines() if line.startswith("#"))
                content = section.strip()
                if content:
                    chunks.append(
                        KnowledgeBaseChunk(
                            document_path=path.relative_to(self._project_root).as_posix(),
                            headings=headings,
                            content=content,
                        )
                    )
        return tuple(chunks)

    def search(self, text: str, limit: int = 3) -> tuple[RetrievalMatch, ...]:
        query_tokens = _tokens(text)
        # Preserve case: upper-case identifiers are likely error codes, while
        # ordinary words must not be promoted to exact-code matches.
        query_errors = set(ERROR_PATTERN.findall(text))
        query_products = {slug for product, slug in PRODUCT_DOCUMENT_SLUGS.items() if product in text.lower()}
        matches: list[RetrievalMatch] = []
        for chunk in self._chunks:
            exact_error_count = len(query_errors & set(ERROR_PATTERN.findall(chunk.content)))
            heading_tokens = _tokens(" ".join(chunk.headings)) - GENERIC_HEADING_TOKENS
            heading_overlap = query_tokens & heading_tokens
            # A known issue must be anchored by an exact documented error code
            # or by multiple terms in a documented heading. Broad body overlap
            # alone is not sufficiently reliable to surface a document.
            if not exact_error_count and len(heading_overlap) < 2:
                continue
            # If the ticket names one of the supplied products, a non-error
            # match must come from that product's own reference. This prevents
            # a generic onboarding link to every product from becoming evidence.
            if not exact_error_count and query_products and not any(slug in chunk.document_path for slug in query_products):
                continue
            score = len(query_tokens & _tokens(chunk.content)) + 10 * exact_error_count + 3 * len(heading_overlap)
            if exact_error_count and "/troubleshooting/" in chunk.document_path:
                score += 5
            matches.append(RetrievalMatch(chunk=chunk, score=score))
        return tuple(sorted(matches, key=lambda match: (-match.score, match.chunk.document_path))[:limit])
