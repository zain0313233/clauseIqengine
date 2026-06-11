ALLOWED_MIMES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)


def detect_mime(file_bytes: bytes) -> str:
    if len(file_bytes) >= 5 and file_bytes[:5] == b"%PDF-":
        return "application/pdf"
    if len(file_bytes) >= 4 and file_bytes[:4] == b"PK\x03\x04":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    raise ValueError("Unsupported file type")


def assert_mime_matches(file_bytes: bytes, declared_type: str) -> str:
    if declared_type not in ALLOWED_MIMES:
        raise ValueError(f"Unsupported file type: {declared_type}")

    detected = detect_mime(file_bytes)
    if detected != declared_type:
        raise ValueError("Declared file type does not match file content")
    return detected
