import fitz
import docx
import httpx
import io

async def parse_document(file_url: str, file_type: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(file_url)
        file_bytes = response.content

    if file_type == "application/pdf":
        return parse_pdf(file_bytes)
    elif "wordprocessingml" in file_type:
        return parse_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

def parse_pdf(file_bytes: bytes) -> str:
    text = ""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()

def parse_docx(file_bytes: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])