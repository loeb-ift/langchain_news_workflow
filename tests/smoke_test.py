import json
import os
from click.testing import CliRunner

# Ensure import works when running from repo root
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline import app as typer_app, run_pipeline, OLLAMA_MOCK


def test_non_interactive_pipeline_mock_passes():
    os.environ["OLLAMA_MOCK"] = "true"
    out = run_pipeline(
        raw_data="這是一段用於測試的原始資料，內容超過五十個字以符合分析模組的需求，並且可以被 Alpha 處理。",
        news_type="財經",
        target_style="經濟日報",
        word_limit=700,
        tone="客觀中性",
    )
    assert out.get("success") is True, out
    data = out.get("data") or {}
    assert isinstance(data.get("final_body"), str)
    assert isinstance(data.get("best_title"), str)


def test_cli_interactive_minimal_happy_path():
    os.environ["OLLAMA_MOCK"] = "true"
    runner = CliRunner()
    # Minimal choices per stage to progress:
    # Alpha: 1 (accept)
    # Beta: 1 (accept)
    # Gamma: 1 (choose news_type title)
    # Delta: Enter to skip edit, then y to accept
    user_input = "\n".join([
        "1",  # Alpha accept
        "1",  # Beta accept
        "1",  # Gamma choose news_type
        "",   # Delta skip edit
        "y",  # accept final
        ""
    ])
    result = runner.invoke(
        typer_app, 
        [
            "--raw-data",
            "這是一段用於互動測試的原始資料，模擬一段較長的新聞素材，以便 Alpha/Beta/Gamma/Delta 能順利進行。",
            "--news-type",
            "財經",
            "--target-style",
            "經濟日報",
            "--word-limit",
            "700",
            "--tone",
            "客觀中性",
            "--interactive",
        ],
        input=user_input,
        prog_name="pipeline",
    )
    assert result.exit_code == 0, result.output
    # The CLI prints final JSON at the end; ensure it's valid and success true
    try:
        last_brace = result.output.rfind("}")
        first_brace = result.output.find("{")
        payload = json.loads(result.output[first_brace:last_brace+1])
    except Exception:
        # If parsing straight fails, ensure at least the success true string appears
        assert "\"success\": true" in result.output.lower(), result.output
        return
    assert payload.get("success") is True, result.output
