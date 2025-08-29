import json
import os
from typing import Any, Dict, List, Optional

try:
    import json5
except Exception:
    json5 = None

DEFAULT_SUMMARIES = {
    "news_type": {
        "財經": "強調數據、法人觀點、市場影響與風險因子。",
        "科技": "聚焦技術趨勢、產品節點與產業鏈脈絡。",
        "產業": "供應鏈動態、產能、成本與毛利走勢。",
        "事件": "時間軸、關鍵當事人與影響評估。",
        "政策": "法規要求、適用範圍與產業影響。",
    },
    "target_style": {
        "經濟日報": "倒金字塔結構，正式專業，財經術語適中，聚焦數據與影響。",
        "中央社": "平實中性，重事實與來源，標準新聞結構。",
        "數位時代": "現代活潑，科技新詞，故事敘述，重趨勢與創新。",
        "券商研報": "分析導向，投資術語，邏輯推演，重投資價值。",
    },
    "tone": {
        "客觀中性": "保持客觀描述，避免誇張與推測。",
        "積極正面": "語氣偏正向，強調機會與利多面。",
        "謹慎保守": "語氣保守，提醒風險與限制。",
    },
}


class PromptManager:
    def __init__(self, prompt_dir: str = "prompts"):
        self.prompt_dir = prompt_dir
        self.override_dir = os.path.join(self.prompt_dir, "overrides")
        os.makedirs(self.override_dir, exist_ok=True)

    def _path(self, stage: str) -> str:
        return os.path.join(self.prompt_dir, f"{stage}.json")

    def has_stage(self, stage: str) -> bool:
        return os.path.exists(self._path(stage))

    def _override_path(self, stage: str) -> str:
        return os.path.join(self.override_dir, f"{stage}.json")

    def _deep_merge(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(a)
        for k, v in b.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = self._deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    def load_stage(self, stage: str) -> Dict[str, Any]:
        base_path = self._path(stage)
        base: Dict[str, Any] = {"base": {}, "by_news_type": {}, "by_target_style": {}, "by_tone": {}}
        if os.path.exists(base_path):
            with open(base_path, "r", encoding="utf-8") as rf:
                text = rf.read()
                try:
                    base = json.loads(text)
                except Exception:
                    if json5 is not None:
                        base = json5.loads(text)
                    else:
                        raise
        ov_path = self._override_path(stage)
        if os.path.exists(ov_path):
            with open(ov_path, "r", encoding="utf-8") as rf:
                text = rf.read()
                try:
                    override = json.loads(text)
                except Exception:
                    if json5 is not None:
                        override = json5.loads(text)
                    else:
                        raise
            base = self._deep_merge(base, override)
        return base

    def _safe_format(self, template: str, context: Dict[str, Any]) -> str:
        result = template
        for k, v in context.items():
            result = result.replace("{" + k + "}", str(v))
        return result

    def compose(self, stage: str, context: Dict[str, Any], *, news_type: Optional[str] = None, target_style: Optional[str] = None, tone: Optional[str] = None, session_append: str = "") -> Dict[str, str]:
        data = self.load_stage(stage)
        base = data.get("base", {})
        system = base.get("system", "")
        user = base.get("user", "")
        
        src_notes: list[str] = []
        if news_type:
            na = data.get("by_news_type", {}).get(news_type, {}).get("user_append", "")
            if na:
                user += "\n" + na
                src_notes.append(f"[來源: 類型={news_type}] {na}")
        if target_style:
            ta = data.get("by_target_style", {}).get(target_style, {}).get("user_append", "")
            if ta:
                user += "\n" + ta
                src_notes.append(f"[來源: 風格={target_style}] {ta}")
        if tone:
            to = data.get("by_tone", {}).get(tone, {}).get("user_append", "")
            if to:
                user += "\n" + to
                src_notes.append(f"[來源: 語氣={tone}] {to}")
        if src_notes:
            user += "\n\n# 設計依據\n" + "\n".join(src_notes)
        if session_append:
            user += "\n" + session_append
        
        system_f = self._safe_format(system, context)
        user_f = self._safe_format(user, context)
        return {"system": system_f, "user": user_f}

    def preview_for_choice(self, stage: str, *, news_type: Optional[str] = None, target_style: Optional[str] = None, tone: Optional[str] = None) -> List[str]:
        out: List[str] = []
        if news_type and news_type in DEFAULT_SUMMARIES["news_type"]:
            out.append(f"[類型] {news_type}: {DEFAULT_SUMMARIES['news_type'][news_type]}")
        if target_style and target_style in DEFAULT_SUMMARIES["target_style"]:
            out.append(f"[風格] {target_style}: {DEFAULT_SUMMARIES['target_style'][target_style]}")
        if tone and tone in DEFAULT_SUMMARIES["tone"]:
            out.append(f"[語氣] {tone}: {DEFAULT_SUMMARIES['tone'][tone]}")
        return out

    def show_full_prompt(self, stage: str, context: Dict[str, Any], *, news_type: Optional[str] = None, target_style: Optional[str] = None, tone: Optional[str] = None, session_append: str = "") -> str:
        msgs = self.compose(stage, context, news_type=news_type, target_style=target_style, tone=tone, session_append=session_append)
        return ("[SYSTEM]\n" + msgs["system"] + "\n\n[USER]\n" + msgs["user"]).strip()

    def save_override(self, stage: str, data: Dict[str, Any]) -> None:
        path = self._override_path(stage)
        with open(path, "w", encoding="utf-8") as wf:
            json.dump(data, wf, ensure_ascii=False, indent=2)

    def load_override(self, stage: str) -> Dict[str, Any]:
        path = self._override_path(stage)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as rf:
                return json.load(rf)
        return {}

    def remove_override(self, stage: str) -> None:
        path = self._override_path(stage)
        if os.path.exists(path):
            os.remove(path)