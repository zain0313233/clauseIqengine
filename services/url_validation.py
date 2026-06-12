import ipaddress
import os
import socket
from urllib.parse import urlparse

MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024


def _allowed_hosts() -> set[str]:
    hosts: set[str] = set()
    explicit = os.environ.get("SUPABASE_STORAGE_HOST")
    if explicit:
        hosts.add(explicit.strip().lower())

    supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get(
        "NEXT_PUBLIC_SUPABASE_URL"
    )
    if supabase_url:
        try:
            hosts.add(urlparse(supabase_url).hostname.lower())
        except Exception:
            pass

    return hosts


def validate_file_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValueError("Only HTTPS file URLs are allowed")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("Invalid file URL host")

    allowed = _allowed_hosts()
    if not allowed:
        raise ValueError("SUPABASE_STORAGE_HOST or SUPABASE_URL must be configured")
    if hostname not in allowed:
        raise ValueError("File URL host is not allowed")

    try:
        for info in socket.getaddrinfo(hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if not ip.is_global:
                raise ValueError("File URL resolves to a non-public address")
    except socket.gaierror as exc:
        raise ValueError("Could not resolve file URL host") from exc
