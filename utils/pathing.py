import os
import re
from typing import Dict, Optional


def safe_name(name: Optional[str]) -> str:
    if not name:
        return ""
    # Replace forbidden chars and collapse whitespace
    s = re.sub(r"[\\/:*?\"<>|]", "_", name)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def render_path_template(template: str, mapping: Dict[str, str]) -> str:
    if not template:
        return ""
    leading = template.startswith("/")
    segments = [seg for seg in template.split("/") if seg != ""]
    out = []
    for seg in segments:
        fields = re.findall(r"{(\w+)}", seg)
        # If any placeholder is empty, drop the whole segment
        if fields and any((mapping.get(f, "") == "") for f in fields):
            continue
        seg_fmt = seg.format(**mapping)
        # Special-case save_root: treat as raw path, not sanitized
        if fields and len(fields) == 1 and fields[0] == "save_root":
            raw = os.path.normpath(seg_fmt)
            if raw.startswith("/"):
                leading = True
                raw = raw[1:]
            # extend by raw components
            for part in [p for p in raw.split("/") if p]:
                out.append(part)
            continue
        # Default behavior: sanitize the segment
        seg_fmt = safe_name(seg_fmt)
        if seg_fmt:
            out.append(seg_fmt)
    path = "/".join(out)
    if leading:
        path = "/" + path if not path.startswith("/") else path
    return os.path.normpath(path)
