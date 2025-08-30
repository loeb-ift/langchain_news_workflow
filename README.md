# AI 新聞稿自動生成工作流程 (LangChain 版本)

## 專案目的

本專案旨在提供一個自動化的新聞稿生成流程。它利用大型語言模型（LLM），將輸入的原始資料，經過 Alpha、Beta、Gamma、Delta 四個階段的處理，最終產出一篇結構完整、風格明確、品質優良的新聞稿。

整個流程支援高度互動，允許使用者在每個階段審核、修改、重試，以確保最終產出的品質符合期望。

## 功能特色

- **四階段處理流程**：
  - **Alpha (資訊架e構師)**：將原始資料轉為結構化的新聞初稿。
  - **Beta (風格塑造師)**：將初稿依據指定風格（如：經濟日報、數位時代）進行改寫。
  - **Gamma (標題策略師)**：產生多種類型（新聞型、數據型等）的標題選項。
  - **Delta (品質守門員)**：進行最終的品質審核、修正與定稿。
- **高度互動性**：使用者可以在每個階段後暫停，選擇接受、重試、或修改內容。
- **可配置性**：支援透過命令列參數調整新聞類型、目標風格、語氣、字數等。
- **本地模型支援**：使用 [Ollama](https://ollama.com/) 在本地端運行語言模型，無需依賴 OpenAI 等雲端服務。
- **決策日誌**：可選擇性地將每次執行的決策過程記錄下來，存成 `pipeline_log.csv` 檔案，便於分析與追蹤。

## 檔案結構

```
.
├── app_utils/          # 共用工具模組
│   ├── prompt_manager.py # 提示詞管理
│   └── ui_texts.py       # UI 文字管理
├── prompts/              # AI 提示詞模板 (JSON 格式)
├── article.txt           # 輸入的原始文章範例
├── pipeline.py           # 主要的互動式新聞生成腳本
├── pipeline_log.py       # 帶有日誌記錄功能的版本
├── pipeline_log.csv      # 儲存決策過程的日誌檔案
└── README.md             # 本說明檔案
```

## 環境設定

### 需求

- Python 3.10+
- 本地端已安裝並正在運行的 [Ollama](https://ollama.com/) 服務。
- 已下載所需的語言模型（預設為 `llama3:8b`）。

### 安裝步驟

1.  **安裝 Python 套件**：
    ```bash
    pip install -r requirements.txt
    ```

2.  **設定環境變數**：
    專案會讀取 `.env` 檔案中的環境變數。您可以複製 `.env.example` 來建立您的設定檔：
    ```bash
    cp .env.example .env
    ```
    然後修改 `.env` 檔案的內容：
    ```
    # 您本地 Ollama 服務的位址
    OLLAMA_BASE_URL="http://localhost:11434"
    # 您希望使用的模型名稱
    OLLAMA_MODEL_NAME="llama3:8b"
    ```

## 使用說明

本專案提供兩種執行模式：

### 1. 標準互動流程 (`pipeline.py`)

這是主要的執行腳本，提供完整的互動式體驗。

**執行指令範例：**

```bash
python pipeline.py \
  --raw-data "$(cat article.txt)" \
  --news-type "財經" \
  --target-style "經濟日報" \
  --word-limit 800 \
  --tone "客觀中性"
```

### 2. 帶日誌記錄與批次處理 (`pipeline_log.py`)

此腳本提供與 `pipeline.py` 相同的流程，並具備以下擴充：
- 將整個過程的決策摘要記錄到 CSV
- 支援批次處理多個 .txt 檔
- 支援非互動模式，便於大量檔案不中斷處理
- 可設定 CSV 路徑（環境變數或 CLI）

#### 常用範例

- 單次輸入文字（互動模式）
```bash
python pipeline_log.py \
  --raw-data "$(cat article.txt)" \
  --news-type "財經" \
  --target-style "經濟日報" \
  --word-limit 700
```

- 批次處理資料夾所有 .txt（非互動）
```bash
python pipeline_log.py \
  --files ./folder_with_txts \
  --non-interactive
```

- 指定輸出 CSV 路徑 + 輸出完整 JSON 詳細紀錄
```bash
python pipeline_log.py \
  --files ./folder_with_txts \
  --non-interactive \
  --log-csv ./logs/my_pipeline_log.csv \
  --json-out-dir ./logs/details
```

- 改用環境變數指定 CSV 路徑
```bash
export PIPELINE_LOG_CSV=./logs/batch_log.csv
python pipeline_log.py --files ./folder_with_txts --non-interactive
```

- 模擬模式（不呼叫模型）
```bash
export OLLAMA_MOCK=true
python pipeline_log.py --files ./folder_with_txts --non-interactive
```

#### 命令列參數說明（pipeline_log.py）

| 參數 | 說明 | 預設值 | 
| :--- | :--- | :--- | 
| `--raw-data` | 原始資料內容；與 `--files` 擇一必填 |  | 
| `--files` | 要處理的檔案或資料夾路徑（可多個）；資料夾會遞迴讀取所有 `.txt` 檔 |  | 
| `--news-type` | 新聞類型，會影響 AI 處理的側重點 | `財經` | 
| `--target-style` | 目標媒體風格，AI 會模仿其寫作風格 | `經濟日報` | 
| `--word-limit` | 希望的目標字數 | `800` | 
| `--tone` | 希望的語氣要求 | `客觀中性` | 
| `--constraints` | 其他特殊限制或要求 | `None` | 
| `--additional-answers-json` | JSON 字串形式的補充資訊 | `None` | 
| `--max-retries` | 各階段自動重試次數 | `2` | 
| `--non-interactive` | 非互動模式：自動接受預設選項 | `False` | 
| `--log-csv` | CSV 輸出路徑；若未提供，讀取環境變數 `PIPELINE_LOG_CSV`；再未提供則為 `pipeline_log.csv` |  | 
| `--ollamaHost` | 指定 Ollama 服務位址（含 port），覆蓋環境變數 `OLLAMA_BASE_URL` |  | 
| `--show-prompts` | 顯示 LLM 提示詞預覽（除錯用），預設不顯示 | `False` | 

#### 常見用法
- 單次文字 + 指定 CSV 與 JSON 詳錄（指定遠端 Ollama 主機）
```bash
python pipeline_log.py \
  --raw-data "$(cat article.txt)" \
  --log-csv ./logs/run.csv \
  --json-out-dir ./logs/details \
  --ollamaHost http://10.0.0.5:11434
```

- 批次處理資料夾所有 .txt（非互動）+ 指定 CSV 與 JSON 詳錄
```bash
python pipeline_log.py \
  --files ./folder_with_txts \
  --non-interactive \
  --log-csv ./logs/batch.csv \
  --json-out-dir ./logs/details
```

- 多個路徑混合（檔案與資料夾）
```bash
python pipeline_log.py \
  --files ./a.txt \
  --files ./folder_b \
  --non-interactive \
  --log-csv ./logs/mixed.csv
```

- 透過環境變數指定預設 CSV 路徑
```bash
export PIPELINE_LOG_CSV=./logs/default.csv
python pipeline_log.py --files ./folder --non-interactive
```

- 模擬模式（不呼叫模型）
```bash
export OLLAMA_MOCK=true
python pipeline_log.py --files ./folder --non-interactive
```

#### CSV 欄位說明（成功與失敗皆會寫入）
- `session_id`: 本次處理的唯一識別
- `start_time` / `end_time` / `duration_seconds`: 執行區間與耗時（秒）
- `initial_raw_data`: 初始輸入（為了可讀性已截斷至 250 字）
- `alpha_decisions` / `beta_decisions` / `gamma_decisions` / `delta_decisions`: 各階段的決策摘要（JSON）。若使用 `--json-out-dir`，每一筆 `log_entries` 會包含各階段完整 prompt 與模型回覆，存成一個 session_id.json。
- `final_headline`: 最終標題（成功時）
- `final_body`: 最終內文（成功時）或 `[FAILED] stage=... message=...`（失敗/中止時）

## 互動流程範例

### 重試行為說明
- Beta 階段：當你輸入 2 或 r 進行重試時，系統會先重新顯示三個選單，讓你重新選擇「新聞類型」、「目標媒體風格」、「語氣」，之後才會重新呼叫模型生成 Beta 結果。
- Delta 階段：當你輸入 n（或 r）不接受時，系統會先讓你輸入「本次修正方向」，並將此指令附加到提示詞（不改變事實與數據），再重新呼叫模型生成新版本。達到重試上限（預設 2）會自動採用最新版本。
- 提示：互動輸入支援全形數字/字母（會自動正規化），例如輸入「２」等同於「2」。

#### Delta 修正與 LOG 紀錄
- 修正方向：你在 Delta 輸入的「本次修正方向」會被加入提示詞的 session_append，作為本次重試的明確指令。
- LOG 條目：CSV 的 delta_decisions 會包含下列事件（JSON 陣列）：
  - raw_output：含本次 prompt（內含修正指令）與模型回覆
  - ai_result：本次 Delta 產出與 attempt 次數
  - lang_check：語言一致性檢查摘要
  - user_choice：使用者選擇（y/n/q）與 attempt 次數
  - parse_error（如有）：模型未輸出 JSON 時的原始回覆摘要
  - finalized / finalized_max_retries / finalized_default：流程結束原因與統計資訊

執行後，您會看到類似以下的互動介面：

```
=== Alpha（資訊架構師） ===
目的: 將原始資料轉為結構化初稿...
使用資料: {'news_type': '財經', 'word_limit': 800, 'tone': '客觀中性'}
...

Alpha 品質分數: 9/10，需要重試? False
Alpha 重點: ...

Alpha 操作：
  1) 接受並進入 Beta (a)
  2) 重試 (r)
  3) 退出 (q)
請輸入選項（數字或縮寫）： [1]:
```

您可以依照提示輸入數字或縮寫來進行下一步操作。
