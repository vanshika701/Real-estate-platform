from app.core.errors import AppError


def detect_image_type(data: bytes) -> tuple[str, str]:
    """Return (content_type, extension) for JPEG, PNG or WebP data; raise 415 otherwise.

    The declared Content-Type comes from the client and can't be trusted, so the format is
    identified from the file's own first bytes (its "magic number").
    """
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    raise AppError("unsupported_media_type", "Only JPEG, PNG and WebP images are allowed", 415)
