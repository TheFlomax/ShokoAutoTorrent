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
        if fields and any((mapping.get(f, "") == "") for f in fields):
            # Drop segment if it contains an empty placeholder
            continue
        seg_fmt = seg.format(**mapping)
        seg_fmt = safe_name(seg_fmt)
        if seg_fmt:
            out.append(seg_fmt)
    path = "/".join(out)
    if leading:
        path = "/" + path if not path.startswith("/") else path
    return os.path.normpath(path)