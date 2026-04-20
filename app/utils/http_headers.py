import re
from urllib.parse import quote


def build_download_content_disposition(filename: str) -> str:
    raw_name = (filename or "").replace("\r", "").replace("\n", "").strip() or "download"
    encoded_name = quote(raw_name, safe="")

    ascii_name = raw_name.encode("ascii", errors="ignore").decode("ascii")
    ascii_name = ascii_name.replace('"', "'").replace("\\", "_")
    ascii_name = re.sub(r"[;\r\n]", "_", ascii_name).strip()
    if not ascii_name or ascii_name in {".", ".."}:
        ascii_name = "download"

    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded_name}"
