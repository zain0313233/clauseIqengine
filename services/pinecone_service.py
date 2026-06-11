import os
from dotenv import load_dotenv
from pinecone import Pinecone


load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))


def delete_document_vectors(document_id: str) -> None:
  index.delete(filter={"document_id": {"$eq": document_id}})


def store_chunks(document_id: str, chunks: list[str], embeddings: list[list[float]]) -> list[str]:
  delete_document_vectors(document_id)

  vectors = []
  pinecone_ids = []

  for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
    pinecone_id = f"{document_id}_chunk_{i}"
    vectors.append({
      "id": pinecone_id,
      "values": embedding,
      "metadata": {
        "document_id": document_id,
        "chunk_index": i,
        "content": chunk,
      },
    })
    pinecone_ids.append(pinecone_id)

  index.upsert(vectors=vectors)
  return pinecone_ids


def search_chunks(
  query_embedding: list[float],
  document_id: str,
  top_k: int = 6,
) -> list[dict]:
  """Return ranked chunks with metadata for citations."""
  results = index.query(
    vector=query_embedding,
    top_k=top_k,
    filter={"document_id": {"$eq": document_id}},
    include_metadata=True,
  )

  chunks: list[dict] = []
  for match in results.matches:
    if match.metadata and "content" in match.metadata:
      chunks.append({
        "content": match.metadata["content"],
        "chunk_index": int(match.metadata.get("chunk_index", 0)),
        "score": round(float(match.score or 0), 4),
      })

  return chunks


def search_chunks_portfolio(
  query_embedding: list[float],
  document_ids: list[str],
  top_k: int = 15,
) -> list[dict]:
  """Search across multiple documents for portfolio-level Q&A."""
  if not document_ids:
    return []

  results = index.query(
    vector=query_embedding,
    top_k=top_k,
    filter={"document_id": {"$in": document_ids}},
    include_metadata=True,
  )

  chunks: list[dict] = []
  for match in results.matches:
    if match.metadata and "content" in match.metadata:
      chunks.append({
        "content": match.metadata["content"],
        "chunk_index": int(match.metadata.get("chunk_index", 0)),
        "document_id": match.metadata.get("document_id", ""),
        "score": round(float(match.score or 0), 4),
      })

  return chunks
