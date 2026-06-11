import fitz
import docx
import httpx
import io

from services.url_validation import MAX_DOWNLOAD_BYTES, validate_file_url

async def parse_document(file_url: str, file_type: str) -> str:
    validate_file_url(file_url)

    file_bytes = b""
    async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
        async with client.stream("GET", file_url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                file_bytes += chunk
                if len(file_bytes) > MAX_DOWNLOAD_BYTES:
                    raise ValueError("File exceeds maximum allowed size")

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
