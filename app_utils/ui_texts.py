import json
import os
from typing import List, Dict, Any

_UI_PATH = os.path.join(os.path.dirname(__file__), "ui_texts.json")

_DEFAULT_SNIPPETS: List[Dict[str, str]] = [
    {"name": "加強數據", "text": "請補充具體數據（百分比、金額、規模、區間），並標註資料期間與來源。"},
    {"name": "避免行話", "text": "將行話/內部術語改為通俗易懂的說法，並保持用詞一致。"},
    {"name": "補充具體時間點", "text": "加入確切時間（年月日/季度）與區間，避免模糊詞（近期、近日等）。"},
    {"name": "來源標註", "text": "補上資訊來源（公司公告、法說會、研究報告、官方數據）以提升可驗證性。"},
    {"name": "前後對比", "text": "補充同比/環比/歷史對比，呈現變化幅度與趨勢。"},
    {"name": "影響層面", "text": "描述對公司、供應鏈、客戶、市場價格與競爭格局的具體影響。"},
    {"name": "風險與限制", "text": "加入風險因子、限制條件與可能的反向指標，保持平衡。"},
    {"name": "結構優化", "text": "採倒金字塔結構：首段包含5W1H與最重要事實，後續補充細節與背景。"},
    {"name": "標題對齊", "text": "確保導言與標題要點一致，關鍵數字與主體對齊。"},
    {"name": "語氣中性", "text": "避免誇大與推測性語句，以客觀中性語氣陳述事實。"},
]

_cached: Dict[str, Any] | None = None


def _load() -> Dict[str, Any]:
    global _cached
    if _cached is not None:
        return _cached
    data: Dict[str, Any] = {}
    try:
        if os.path.exists(_UI_PATH):
            with open(_UI_PATH, "r", encoding="utf-8") as rf:
                data = json.load(rf)
    except Exception:
        data = {}
    _cached = data
    return data


def get_snippet_templates() -> List[Dict[str, str]]:
    data = _load()
    items = data.get("snippet_templates")
    if isinstance(items, list) and items:
        out: List[Dict[str, str]] = []
        for it in items:
            if isinstance(it, dict) and "text" in it:
                out.append({"name": it.get("name", "片段"), "text": str(it["text"])})
        if out:
            return out
    return _DEFAULT_SNIPPETS


def get_stage_tips(stage: str) -> List[str]:
    data = _load()
    tips = data.get("stage_tips", {}).get(stage.lower())
    if isinstance(tips, list):
        return [str(x) for x in tips]
    return []


def get_stage_menu(stage: str) -> str | None:
    data = _load()
    menus = data.get("menus", {})
    val = menus.get(stage.lower())
    if isinstance(val, str) and val.strip():
        return val
    return None


def get_param_summary(param_type: str, key: str) -> str | None:
    data = _load()
    summaries = data.get("param_summaries", {})
    val = summaries.get(param_type, {}).get(key)
    if isinstance(val, str) and val.strip():
        return val
    from .prompt_manager import DEFAULT_SUMMARIES
    return DEFAULT_SUMMARIES.get(param_type, {}).get(key)