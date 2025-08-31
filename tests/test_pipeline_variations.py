import json
import os
from typing import List
from click.testing import CliRunner

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline import app as typer_app, run_pipeline

TARGET_STYLES: List[str] = ["經濟日報", "中央社", "數位時代", "券商研報"]
TONES: List[str] = ["客觀中性", "積極正面", "謹慎保守"]


def _parse_cli_json(output: str):
    first = output.find("{")
    last = output.rfind("}")
    assert first != -1 and last != -1, f"No JSON braces in output:\n{output}"
    payload = json.loads(output[first:last+1])
    return payload


def test_non_interactive_various_styles_and_lengths():
    os.environ["OLLAMA_MOCK"] = "true"
    bodies = []
    for style in TARGET_STYLES:
        out = run_pipeline(
            raw_data=("這是一段用於測試的原始資料，內容超過五十個字以符合分析模組的需求，" * 3),
            news_type="財經",
            target_style=style,
            word_limit=650,
            tone="客觀中性",
        )
        assert out.get("success") is True, out
        data = out.get("data")
        assert isinstance(data.get("final_body", ""), str)
        bodies.append(len(data.get("final_body", "")))
    # 至少有內容
    assert all(b > 0 for b in bodies)


def test_interactive_retry_paths_and_cancel_prompts():
    os.environ["OLLAMA_MOCK"] = "true"
    runner = CliRunner()
    # 覆蓋多種選項路徑（避免進入編輯器）：
    # Alpha: s -> p -> 4(cancel) -> r -> 1(accept)
    # Beta:  s -> p -> 4(cancel) -> r -> 1(accept)
    # Gamma: p -> 4(cancel) -> s -> 3(select trend_type) -> '' (accept)
    # Delta: s -> '' (skip edit) -> y
    user_input = "\n".join([
        "s",
        "p", "4",
        "r",
        "1",
        # Beta
        "s",
        "p", "4",
        "r",
        "1",
        # Gamma
        "p", "4",
        "s",
        "3",
        "",  # accept
        # Delta
        "s",
        "",  # skip edit
        "y",
        "",
    ])
    result = runner.invoke(
        typer_app,
        [
            "--raw-data",
            "這是一段用於互動測試的原始資料，模擬較長的新聞素材，以便 Alpha/Beta/Gamma/Delta 能順利進行。" * 2,
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
        catch_exceptions=False,
        prog_name="pipeline",
    )
    assert result.exit_code == 0, result.output
    payload = _parse_cli_json(result.output)
    assert payload.get("success") is True, result.output


def test_interactive_each_style_short_path():
    os.environ["OLLAMA_MOCK"] = "true"
    runner = CliRunner()
    for style in TARGET_STYLES:
        user_input = "\n".join([
            "1",  # alpha accept
            "1",  # beta accept
            "2",  # gamma choose data_type
            "",   # delta skip edit
            "y",  # accept final
            "",
        ])
        result = runner.invoke(
            typer_app,
            [
                "--raw-data",
                "互動短路徑測試用原始資料，供 Mock 流程使用。" * 2,
                "--news-type",
                "財經",
                "--target-style",
                style,
                "--word-limit",
                "680",
                "--tone",
                "客觀中性",
                "--interactive",
            ],
            input=user_input,
            catch_exceptions=False,
            prog_name="pipeline",
        )
        assert result.exit_code == 0, f"style={style}\n{result.output}"
        payload = _parse_cli_json(result.output)
        assert payload.get("success") is True, f"style={style}\n{result.output}"
