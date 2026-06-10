from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()

def embed_query(query: str) -> list[float]:
    embedding = model.encode([query], show_progress_bar=False)
    return embedding[0].tolist()