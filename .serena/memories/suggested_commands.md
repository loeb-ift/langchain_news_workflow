# 开发和运行命令

## 安装依赖
```bash
# 安装主要依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r dev-requirements.txt
```

## 运行Web UI
```bash
# 启动Gradio Web界面
python gradio_app.py
```
启动后，可访问 http://localhost:7860 查看界面

## 命令行交互模式
```bash
# 使用pipeline.py进行交互式处理
python pipeline.py \
  --raw-data "$(cat article.txt)" \
  --news-type "財經" \
  --target-style "經濟日報" \
  --word-limit 800 \
  --tone "客觀中性"
```

## 批量处理模式
```bash
# 使用pipeline_log.py进行批量处理
python pipeline_log.py \
  --files ./folder_with_txts \
  --non-interactive \
  --log-csv ./logs/batch_log.csv

# 批量处理并输出详细日志
python pipeline_log.py \
  --files ./folder_with_txts \
  --non-interactive \
  --log-csv ./logs/batch_log.csv \
  --json-out-dir ./logs/details
```

## 启动后端服务
```bash
# 启动FastAPI后端服务
python server.py
```

## 测试命令
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/smoke_test.py

# 运行测试并生成覆盖率报告
pytest --cov
```

## 环境变量相关
```bash
# 复制环境变量示例文件
cp .env.example .env

# 使用环境变量设置Ollama服务地址
OLLAMA_BASE_URL=http://localhost:11434 python pipeline.py

# 使用模拟模式（不实际调用模型）
export OLLAMA_MOCK=true
python pipeline_log.py --files ./folder_with_txts --non-interactive
```

## 其他实用命令
```bash
# 查看可用的Ollama模型
curl http://localhost:11434/api/tags

# 查看日志文件
cat pipeline_log.csv

# 清理日志
rm -f pipeline_log.csv logs/*.csv logs/details/*.json
```

## 开发工作流
1. 安装依赖：`pip install -r requirements.txt -r dev-requirements.txt`
2. 运行测试：`pytest`
3. 修改代码
4. 运行测试确保功能正常
5. 运行应用测试：`python gradio_app.py` 或 `python pipeline.py`
6. 提交代码变更