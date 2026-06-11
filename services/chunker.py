import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Legal document section patterns (ordered by priority)
# Use re.MULTILINE at call site — do not embed (?m) when patterns are joined with |
SECTION_PATTERNS = [
  r"^(?:ARTICLE|Article)\s+[IVXLC\d]+[\.\:\-\s]",
  r"^(?:SECTION|Section)\s+\d+[\.\:\-\s]",
  r"^(?:CLAUSE|Clause)\s+\d+[\.\:\-\s]",
  r"^\d+\.\d+\s+[A-Z]",           # 1.1 Definitions
  r"^\d+\.\s+[A-Z][A-Za-z]",      # 1. Definitions
  r"^(?:\([a-z]\)\s+)",           # (a) sub-clauses
  r"^(?:WHEREAS|NOW, THEREFORE)",
]

FALLBACK_SEPARATORS = [
  "\n\n",
  "\n",
  ". ",
  "; ",
  " ",
]

EXCLUSION_NOTE_RE = re.compile(r"^NOTE:\s*.+$", re.MULTILINE | re.IGNORECASE)

def _split_by_legal_sections(text: str) -> list[str]:
  """Split text at legal section boundaries when detectable."""
  combined = "|".join(f"(?:{p})" for p in SECTION_PATTERNS)
  parts = re.split(combined, text, flags=re.MULTILINE)
  sections = [p.strip() for p in parts if p and p.strip() and len(p.strip()) > 30]
  return sections if len(sections) > 1 else []


def _subsplit_large(section: str, chunk_size: int, chunk_overlap: int) -> list[str]:
  if len(section) <= chunk_size:
    return [section]

  splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap,
    separators=FALLBACK_SEPARATORS,
  )
  return [c.strip() for c in splitter.split_text(section) if c.strip()]


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[str]:
  """
  Legal-aware chunking:
  1. Try to split by section/clause headers first
  2. Sub-split large sections while preserving paragraph boundaries
  3. Prefix chunks with section context when available
  """
  normalized = re.sub(r"\r\n", "\n", text)
  normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()

  sections = _split_by_legal_sections(normalized)

  if not sections:
    splitter = RecursiveCharacterTextSplitter(
      chunk_size=chunk_size,
      chunk_overlap=chunk_overlap,
      separators=FALLBACK_SEPARATORS,
    )
    return _promote_exclusion_notes(
      [c.strip() for c in splitter.split_text(normalized) if c.strip()]
    )

  chunks: list[str] = []
  current_section_label = ""

  for section in sections:
    # Detect if this part is a section header line
    header_match = re.match(
      r"^((?:ARTICLE|Article|SECTION|Section|CLAUSE|Clause)\s+[\w\d\.]+[^\n]*)",
      section,
    )
    if header_match:
      current_section_label = header_match.group(1).strip()

    sub_chunks = _subsplit_large(section, chunk_size, chunk_overlap)

    for sub in sub_chunks:
      if current_section_label and not sub.startswith(current_section_label):
        chunks.append(f"[{current_section_label}]\n{sub}")
      else:
        chunks.append(sub)

  return _promote_exclusion_notes(chunks)


def _promote_exclusion_notes(chunks: list[str]) -> list[str]:
  """Duplicate explicit omission NOTE lines as dedicated chunks for better retrieval."""
  promoted: list[str] = []
  seen: set[str] = set()

  for chunk in chunks:
    for match in EXCLUSION_NOTE_RE.finditer(chunk):
      note = match.group(0).strip()
      if note not in seen:
        seen.add(note)
        promoted.append(f"[CLAUSE EXCLUSIONS — explicit omissions]\n{note}")

  return chunks + promoted
