import json
import os
from pipeline import run_pipeline


def test_pipeline_mock_alpha_to_delta(monkeypatch):
    monkeypatch.setenv("OLLAMA_MOCK", "true")
    out = run_pipeline(
        raw_data="台積電公布最新3奈米良率與先進封裝產能規劃……",
        news_type="財經",
        target_style="經濟日報",
        word_limit=800,
        tone="客觀中性",
    )
    assert out["success"] is True
    data = out["data"]
    assert "final_body" in data and data["final_body"]
    assert "best_title" in data and data["best_title"]
    assert isinstance(data.get("headline_options"), dict)
