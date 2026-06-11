import re

from services.embedder import embed_query
from services.pinecone_service import search_chunks

# Questions asking whether a clause exists or is included
_EXISTENCE_PATTERNS = [
  re.compile(p, re.IGNORECASE)
  for p in (
    r"\bis\s+there\s+(?:a|an)\s+.+",
    r"\bdoes\s+(?:the\s+)?(?:agreement|contract|document)\s+(?:have|include|contain)\s+",
    r"\b(?:have|has)\s+(?:a|an)\s+.+?\s+clause\b",
    r"\b(?:is|are)\s+.+\s+included\b",
  )
]

# Topics commonly asked about clause presence
_CLAUSE_TOPIC_RE = re.compile(
  r"(?:force\s+majeure|indemnif|liability\s+cap|limitation\s+of\s+liability|"
  r"arbitration|dispute\s+resolution|termination|confidentiality|"
  r"intellectual\s+property|data\s+processing|sla|service\s+level)",
  re.IGNORECASE,
)


def is_clause_existence_question(question: str) -> bool:
  q = question.strip()
  return any(p.search(q) for p in _EXISTENCE_PATTERNS)


def expand_existence_query(question: str) -> str:
  """Bias retrieval toward explicit inclusion / exclusion language."""
  topic = _CLAUSE_TOPIC_RE.search(question)
  topic_text = topic.group(0) if topic else question
  return (
    f"{question} {topic_text} clause included excluded "
    f"does not include not included absent omitted explicitly states"
  )


def _merge_chunks(primary: list[dict], secondary: list[dict], limit: int = 8) -> list[dict]:
  merged: dict[int, dict] = {}
  for chunk in primary + secondary:
    idx = int(chunk.get("chunk_index", 0))
    existing = merged.get(idx)
    if existing is None or chunk.get("score", 0) > existing.get("score", 0):
      merged[idx] = chunk

  ranked = sorted(merged.values(), key=lambda c: c.get("score", 0), reverse=True)
  return ranked[:limit]


def retrieve_document_chunks(question: str, document_id: str) -> list[dict]:
  """Semantic search with optional second pass for clause-existence questions."""
  primary = search_chunks(embed_query(question), document_id, top_k=6)

  if not is_clause_existence_question(question):
    return primary

  expanded = expand_existence_query(question)
  secondary = search_chunks(embed_query(expanded), document_id, top_k=6)
  return _merge_chunks(primary, secondary, limit=8)
