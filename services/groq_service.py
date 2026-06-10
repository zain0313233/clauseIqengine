import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_answer(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)

    prompt = f"""You are a legal document assistant. Use the following context from a legal document to answer the question accurately.

Context:
{context}

Question: {question}

Answer based only on the context provided. If the answer is not in the context, say "I could not find this information in the document." Be precise and cite relevant clauses when possible."""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024,
    )

    return response.choices[0].message.content