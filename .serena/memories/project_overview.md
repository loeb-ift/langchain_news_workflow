# AI 新闻稿自动生成工作流程 (LangChain 版本)

## 项目目的
本项目旨在提供一个自动化的新闻稿生成流程。它利用大型语言模型（LLM），将输入的原始资料，经过 Alpha、Beta、Gamma、Delta 四个阶段的处理，最终产出一篇结构完整、风格明确、品质优良的新闻稿。

整个流程支持高度互动，允许用户在每个阶段审核、修改、重试，以确保最终产出的品质符合期望。

## 功能特色

- **四阶段处理流程**：
  - **Alpha (信息架构师)**：将原始资料转为结构化的新闻初稿。
  - **Beta (风格塑造师)**：将初稿依据指定风格（如：经济日报、数位时代）进行改写。
  - **Gamma (标题策略师)**：产生多种类型（新闻型、数据型等）的标题选项。
  - **Delta (品质守门员)**：进行最终的品质审核、修正与定稿。
- **高度互动性**：用户可以在每个阶段后暂停，选择接受、重试、或修改内容。
- **可配置性**：支持通过命令列参数调整新闻类型、目标风格、语气、字数等。
- **本地模型支持**：使用 [Ollama](https://ollama.com/) 在本地端运行语言模型，无需依赖 OpenAI 等云端服务。
- **决策日志**：可选择性地将每次执行的决策过程记录下来，存成 `pipeline_log.csv` 文件，便于分析与追踪。
- **Web UI 界面**：透过 Gradio 提供友好的使用者界面，简化操作流程。
- **测试框架**：包含完整的单元测试和集成测试，确保程序稳定性。

## 技术栈
- Python 3.10+
- LangChain 框架 (langchain, langchain-core, langchain-community, langchain-ollama)
- 数据模型：Pydantic
- Web 框架：FastAPI, Uvicorn
- Web UI：Gradio
- 数据处理：Pandas
- 配置管理：python-dotenv, json5
- 命令行工具：Typer
- 测试：pytest, pytest-cov

## 项目结构
```
.
├── pipeline.py            # 主要的交互式新闻生成脚本
├── pipeline_log.py        # 带有日志记录功能的版本
├── gradio_app.py          # Gradio Web UI 界面
├── server.py              # 后端服务器启动脚本
├── app_utils/             # 共用工具模块
│   ├── json_utils.py      # JSON 处理工具
│   ├── ollama_utils.py    # Ollama 模型交互工具
│   ├── prompt_manager.py  # 提示词管理
│   ├── ui_texts.json      # UI 文字配置
│   └── ui_texts.py        # UI 文字管理
├── prompts/               # AI 提示词模板 (JSON 格式)
│   ├── alpha.json         # Alpha 阶段提示词
│   ├── beta.json          # Beta 阶段提示词
│   ├── delta.json         # Delta 阶段提示词
│   ├── gamma.json         # Gamma 阶段提示词
│   └── overrides/         # 提示词覆盖配置
├── tests/                 # 测试用例
├── requirements.txt       # Python 套件依赖
└── dev-requirements.txt   # 开发依赖
```