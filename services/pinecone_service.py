import os
from dotenv import load_dotenv
from pinecone import Pinecone


load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

def store_chunks(document_id: str, chunks: list[str], embeddings: list[list[float]]) -> list[str]:
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
                "content": chunk
            }
        })
        pinecone_ids.append(pinecone_id)

    index.upsert(vectors=vectors)
    return pinecone_ids

def search_chunks(query_embedding: list[float], document_id: str, top_k: int = 5) -> list[str]:
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        filter={"document_id": {"$eq": document_id}},
        include_metadata=True
    )

    chunks = []
    for match in results.matches:
        if match.metadata and "content" in match.metadata:
            chunks.append(match.metadata["content"])

    return chunks