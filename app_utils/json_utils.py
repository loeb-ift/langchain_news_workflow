import json
import re
from typing import Any, Dict, Optional

try:
    import json5  # type: ignore
except Exception:  # pragma: no cover
    json5 = None

SMART_QUOTES = {
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
}


def _normalize_text(s: str) -> str:
    # Replace smart quotes
    for a, b in SMART_QUOTES.items():
        s = s.replace(a, b)
    # Normalize common booleans/None styles from Python to JSON
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    s = re.sub(r"\bNone\b", "null", s)
    return s


def _strip_non_json(s: str) -> Optional[str]:
    # Try to locate the first balanced JSON object in text
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def robust_json_loads(text: str, *, prefer_json5: bool = True) -> Dict[str, Any]:
    """Parse model output into JSON with multiple repair strategies.

    Order:
    1) Direct json.loads
    2) Normalize quotes/bools/None + json.loads
    3) Extract first JSON object and json.loads
    4) If json5 available, try json5 on the above candidates
    5) Heuristic trailing comma removal, then json/json5

    Raises ValueError if all strategies fail.
    """
    candidates = [text]
    norm = _normalize_text(text)
    if norm != text:
        candidates.append(norm)
    extracted = _strip_non_json(text)
    if extracted and extracted not in candidates:
        candidates.append(extracted)
    if extracted:
        extracted_norm = _normalize_text(extracted)
        if extracted_norm not in candidates:
            candidates.append(extracted_norm)

    errors = []
    for use_json5_first in (prefer_json5, not prefer_json5):
        for c in candidates:
            try:
                if use_json5_first and json5 is not None:
                    return json5.loads(c)
                return json.loads(c)
            except Exception as e:
                errors.append(("json5" if use_json5_first else "json", str(e)))

    # Trailing comma removal and retry
    def remove_trailing_commas(s: str) -> str:
        s = re.sub(r",\s*([}\]])", r"\1", s)
        return s

    for c in candidates:
        fixed = remove_trailing_commas(c)
        try:
            return json.loads(fixed)
        except Exception:
            if json5 is not None:
                try:
                    return json5.loads(fixed)
                except Exception as e:
                    errors.append(("json5_trailing", str(e)))
            else:
                errors.append(("json_trailing", "failed"))

    raise ValueError(f"Failed to parse JSON after repairs. errors={errors[:3]}")
