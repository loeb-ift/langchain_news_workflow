import json
import os
from click.testing import CliRunner
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline import app as typer_app


def _parse_cli_json(output: str):
    first = output.find("{")
    last = output.rfind("}")
    assert first != -1 and last != -1, f"No JSON braces in output:\n{output}"
    return json.loads(output[first:last+1])


def test_pe_cancel_no_append_then_accept():
    os.environ["OLLAMA_MOCK"] = "true"
    runner = CliRunner()
    user_input = "\n".join([
        # Alpha
        "p",  # 進入提示詞編輯
        "1",  # 選臨時覆蓋
        "",   # 不輸入任何追加內容（直接存檔/退出的模擬，由於 editor 不會真開，CLI 會走多行輸入，空行結束）
        "1",  # 接受
        # Beta
        "1",  # 接受（Mock放寬）
        # Gamma
        "1",  # 選新聞型
        # Delta
        "",   # 跳過編輯
        "y",  # 接受
        "",
    ])
    result = runner.invoke(
        typer_app,
        [
            "--raw-data",
            "邊界情境：pe 不輸入追加內容的測試。" * 3,
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
    )
    assert result.exit_code == 0, result.output
    payload = _parse_cli_json(result.output)
    assert payload.get("success") is True, result.output


def test_ej_invalid_json_then_continue():
    os.environ["OLLAMA_MOCK"] = "true"
    runner = CliRunner()
    user_input = "\n".join([
        # Alpha
        "1",
        # Beta
        "1",
        # Gamma
        "ej",  # 編輯整組 JSON
        "{ invalid json }",  # 輸入不合法 JSON（CLI會嘗試解析，失敗後忽略）
        "",  # 再次顯示選單，直接接受
        # Delta
        "",
        "y",
        "",
    ])
    result = runner.invoke(
        typer_app,
        [
            "--raw-data",
            "邊界情境：ej 輸入不合法 JSON 的測試。" * 2,
            "--news-type",
            "財經",
            "--target-style",
            "數位時代",
            "--word-limit",
            "680",
            "--tone",
            "客觀中性",
            "--interactive",
        ],
        input=user_input,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    payload = _parse_cli_json(result.output)
    assert payload.get("success") is True, result.output
