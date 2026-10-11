import re
import secrets
import unicodedata


def slugify(text: str) -> str:
    """ "Air Zoom Pegasus 41" -> "air-zoom-pegasus-41"."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-") or "item"


def unique_slug(text: str) -> str:
    """A slug with a short random suffix, for names that can repeat."""
    return f"{slugify(text)}-{secrets.token_hex(3)}"
