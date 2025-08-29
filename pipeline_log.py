import json
import os
import csv
from datetime import datetime
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple, Union

import typer
from dotenv import load_dotenv

# Import the core functionality from the original script
from pipeline import (
    InputConfig,
    interactive_pipeline as original_interactive_pipeline,
)

# Load .env if present
load_dotenv()

app = typer.Typer(name="pipeline_log")

DEFAULT_LOG_FILE = os.getenv("PIPELINE_LOG_CSV", "pipeline_log.csv")

def write_consolidated_log_to_csv(
    session_id: str, 
    start_time: datetime, 
    end_time: datetime, 
    initial_input: str, 
    log_entries: List[Dict[str, Any]],
    final_result: Dict[str, Any],
    log_file: str,
    json_out_dir: Optional[str] = None,
):
    """Appends a single, consolidated log entry for a successful session to the CSV file."""
    file_exists = os.path.exists(log_file)
    
    # 1. Define the new, consolidated headers
    fieldnames = [
        'session_id', 'start_time', 'end_time', 'duration_seconds', 
        'initial_raw_data', 'alpha_decisions', 'beta_decisions', 
        'gamma_decisions', 'delta_decisions', 'final_headline', 'final_body'
    ]
    
    # 2. Process the log_entries to group decisions by stage
  
    decisions = {
        "Alpha": [],
        "Beta": [],
        "Gamma": [],
        "Delta": [],
        "Initial": []
    }
    for entry in log_entries:
        stage = entry.get("stage")
        if stage in decisions:
            decisions[stage].append({
                "action": entry.get("action"),
                "details": entry.get("details")
            })

    # 3. Construct the single row for the CSV
    duration = (end_time - start_time).total_seconds()
    final_data = final_result.get("data", {})
    
    # Truncate for readability in the CSV
    truncated_input = (initial_input[:250] + '...') if len(initial_input) > 250 else initial_input
    truncated_body = (final_data.get("final_body", "")[:250] + '...') if len(final_data.get("final_body", "")) > 250 else final_data.get("final_body", "")

    row_data = {
        "session_id": session_id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": f"{duration:.2f}",
        "initial_raw_data": truncated_input.replace('\n', '\\n'),
        "alpha_decisions": json.dumps(decisions["Alpha"], ensure_ascii=False),
        "beta_decisions": json.dumps(decisions["Beta"], ensure_ascii=False),
        "gamma_decisions": json.dumps(decisions["Gamma"], ensure_ascii=False),
        "delta_decisions": json.dumps(decisions["Delta"], ensure_ascii=False),
        "final_headline": final_data.get("best_title", ""),
        "final_body": truncated_body.replace('\n', '\\n')
    }

    # 4. JSON 詳細輸出（若指定目錄）
    if json_out_dir:
        try:
            os.makedirs(json_out_dir, exist_ok=True)
            detail = {
                "session_id": session_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "config": final_data,  # 最終 Delta 結果
                "log_entries": log_entries,
            }
            json_path = os.path.join(json_out_dir, f"{session_id}.json")
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(detail, jf, ensure_ascii=False, indent=2)
        except Exception as e:
            # JSON 輸出失敗不應影響 CSV 紀錄
            pass

    # 5. Write to the CSV file
    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row_data)

@app.command()
def main(
    raw_data: Optional[str] = typer.Option(None, "--raw-data", help="原始資料內容；與 --files 擇一必填"),
    files: Optional[List[str]] = typer.Option(None, "--files", help="要處理的檔案或資料夾路徑（可多個）；會讀取所有 .txt 檔"),
    news_type: str = typer.Option("財經", "--news-type"),
    target_style: str = typer.Option("經濟日報", "--target-style"),
    word_limit: int = typer.Option(800, "--word-limit"),
    constraints: Optional[str] = typer.Option(None, "--constraints"),
    tone: str = typer.Option("客觀中性", "--tone"),
    additional_answers_json: Optional[str] = typer.Option(None, "--additional-answers-json"),
    max_retries: int = typer.Option(2, "--max-retries"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="非互動模式：自動接受預設選項，用於批次處理"),
    log_csv: Optional[str] = typer.Option(None, "--log-csv", help="CSV 輸出路徑，預設讀取環境變數 PIPELINE_LOG_CSV 或 pipeline_log.csv"),
    json_out_dir: Optional[str] = typer.Option(None, "--json-out-dir", help="若提供則輸出每次完整 prompt/回覆到此目錄，檔名為 session_id.json"),
    show_prompts: bool = typer.Option(False, "--show-prompts", help="顯示 LLM 提示詞預覽 (除錯用)"),
    ollama_host: Optional[str] = typer.Option(None, "--ollamaHost", help="指定 Ollama 服務位址(含port)，覆蓋 OLLAMA_BASE_URL"),
    model: Optional[str] = typer.Option(None, "--model", help="指定模型名稱，覆蓋環境變數 OLLAMA_MODEL_NAME"),
):
    """Runs the interactive pipeline and logs the user's decisions to a CSV file."""
    
    if not raw_data and not files:
        raise typer.BadParameter("請提供 --raw-data 或 --files 其中之一")
    
    # 收集待處理的 (source_id, text) 清單
    tasks: List[Tuple[str, str]] = []
    if raw_data:
        tasks.append(("CLI_INPUT", raw_data))
    if files:
        for path in files:
            if not os.path.exists(path):
                typer.secho(f"⚠️ 路徑不存在：{path}", fg=typer.colors.YELLOW)
                continue
            if os.path.isdir(path):
                for root, _, fnames in os.walk(path):
                    for fn in fnames:
                        if fn.lower().endswith(".txt"):
                            full = os.path.join(root, fn)
                            try:
                                with open(full, "r", encoding="utf-8") as rf:
                                    content = rf.read()
                                tasks.append((full, content))
                            except Exception as e:
                                typer.secho(f"⚠️ 讀取檔案失敗：{full}，{e}", fg=typer.colors.YELLOW)
            else:
                if path.lower().endswith(".txt"):
                    try:
                        with open(path, "r", encoding="utf-8") as rf:
                            content = rf.read()
                        tasks.append((path, content))
                    except Exception as e:
                        typer.secho(f"⚠️ 讀取檔案失敗：{path}，{e}", fg=typer.colors.YELLOW)
                else:
                    typer.secho(f"⚠️ 非 .txt 檔略過：{path}", fg=typer.colors.YELLOW)

    if not tasks:
        typer.secho("沒有可處理的輸入。", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    out_csv = log_csv or DEFAULT_LOG_FILE

    for source_id, text in tasks:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        log_entries: List[Dict[str, Any]] = []
        
        additional_answers = json.loads(additional_answers_json) if additional_answers_json else None
        cfg = InputConfig(
            raw_data=text,
            news_type=news_type,
            target_style=target_style,
            word_limit=word_limit,
            constraints=constraints,
            tone=tone,
            additional_answers=additional_answers,
        )
        
        log_entries.append({"stage": "Initial", "action": "config", "details": {k: v for k, v in asdict(cfg).items() if k != 'raw_data' and k != 'additional_answers'}})
        log_entries.append({"stage": "Initial", "action": "source", "details": {"source": source_id, "text_len": len(text or "")}})

        # 呼叫 pipeline；非互動模式下自動接受預設選項
        result = original_interactive_pipeline(
            cfg,
            max_retries=max_retries,
            log_entries=log_entries,
            interactive=not non_interactive,
            show_prompts=show_prompts,
            override_base_url=ollama_host,
            override_model=model,
        )
        
        end_time = datetime.now()
        if result.get("success"):
            write_consolidated_log_to_csv(session_id, start_time, end_time, cfg.raw_data, log_entries, result, out_csv, json_out_dir=json_out_dir)
            typer.secho(f"\n✅ [{source_id}] Pipeline 完成，已寫入 {out_csv}", fg=typer.colors.GREEN)
        else:
            # 失敗/中止也落盤：記錄 stage 與訊息
            fail_row = {
                "session_id": session_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": f"{(end_time-start_time).total_seconds():.2f}",
                "initial_raw_data": (text[:250] + '...') if len(text) > 250 else text,
                "alpha_decisions": json.dumps([e for e in log_entries if e.get("stage")=="Alpha"], ensure_ascii=False),
                "beta_decisions": json.dumps([e for e in log_entries if e.get("stage")=="Beta"], ensure_ascii=False),
                "gamma_decisions": json.dumps([e for e in log_entries if e.get("stage")=="Gamma"], ensure_ascii=False),
                "delta_decisions": json.dumps([e for e in log_entries if e.get("stage")=="Delta"], ensure_ascii=False),
                "final_headline": "",
                "final_body": f"[FAILED] stage={result.get('stage')} message={result.get('message','')}",
            }
            # 確保 CSV 有標頭
            file_exists = os.path.exists(out_csv)
            with open(out_csv, 'a', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'session_id', 'start_time', 'end_time', 'duration_seconds', 
                    'initial_raw_data', 'alpha_decisions', 'beta_decisions', 
                    'gamma_decisions', 'delta_decisions', 'final_headline', 'final_body'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(fail_row)
            typer.secho(f"\n❌ [{source_id}] Pipeline 中止或失敗，已寫入 {out_csv}", fg=typer.colors.RED)

if __name__ == "__main__":
    app()
