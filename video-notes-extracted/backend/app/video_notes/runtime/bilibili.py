import re


BV_PATTERN = re.compile(r"/video/(BV[0-9A-Za-z]+)")


def extract_bvid(source_url):
    match = BV_PATTERN.search(source_url or "")
    if not match:
        raise ValueError("Unable to extract BVID from source URL")
    return match.group(1)


def resolve_video_title(raw_title, bvid, source_url):
    normalized = (raw_title or "").strip()
    if normalized:
        return normalized
    return f"{bvid} - {source_url}"
