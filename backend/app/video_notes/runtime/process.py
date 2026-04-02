import locale


def decode_process_output(data):
    if data is None:
        return ""
    if isinstance(data, str):
        return data

    candidates = []
    for encoding in ("utf-8", locale.getpreferredencoding(False), "gb18030", "gbk"):
        if encoding and encoding not in candidates:
            candidates.append(encoding)

    for encoding in candidates:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    fallback = candidates[0] if candidates else "utf-8"
    return data.decode(fallback, errors="replace")
