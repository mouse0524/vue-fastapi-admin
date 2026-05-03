from __future__ import annotations


FILE_SIGNATURES: dict[str, list[bytes]] = {
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF87a", b"GIF89a"],
    "zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    "rar": [b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00"],
}


def normalize_ext(filename: str) -> str:
    if not filename:
        return ""
    dot = filename.rfind(".")
    if dot < 0:
        return ""
    return filename[dot + 1 :].strip().lower()


def detect_file_type(data: bytes) -> str | None:
    for ext, signatures in FILE_SIGNATURES.items():
        if any(data.startswith(signature) for signature in signatures):
            return ext

    # WEBP magic: RIFF....WEBP
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"

    return None
