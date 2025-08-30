#!/usr/bin/env python3
"""
Gradio Web Interface for LangChain News Workflow
Provides a user-friendly web interface for the four-stage news generation pipeline.
"""

import gradio as gr
import json
import os
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from pipeline_log import write_consolidated_log_to_csv

# Import existing pipeline functionality
from pipeline import InputConfig, interactive_pipeline, OLLAMA_BASE_URL, MODEL_NAME
from app_utils.prompt_manager import PromptManager
from app_utils.ui_texts import get_snippet_templates, get_stage_tips
from app_utils.json_utils import robust_json_loads
from app_utils.ollama_utils import get_available_models

load_dotenv()

class GradioNewsWorkflow:
    """Gradio interface workflow manager"""
    
    def __init__(self):
        """Initialize the workflow"""
        self.pm = PromptManager()
        self.current_session_data = {}
    
    def _load_prompt_options(self):
        """从prompts文件夹加载选项配置"""
        options = {
            'news_types': [],
            'target_styles': [],
            'tones': []
        }
        
        try:
            # 加载新闻类型（alpha.json）
            alpha = self.pm.load_stage('alpha')
            options['news_types'] = list(alpha['by_news_type'].keys())
            
            # 加载目标媒体风格（beta.json）
            beta = self.pm.load_stage('beta')
            options['target_styles'] = list(beta['by_target_style'].keys())
            
            # 加载语气风格（alpha.json）
            options['tones'] = list(alpha['by_tone'].keys())
        except Exception as e:
            print(f"加载提示词选项失败: {e}")
            # 提供默认值作为后备
            options = {
                'news_types': ['財經', '科技', '產業', '事件', '政策'],
                'target_styles': ['經濟日報', '中央社', '數位時代', '券商研報'],
                'tones': ['客觀中性', '積極正面', '謹慎保守']
            }
        
        return options
    
    def process_news_article(
        self,
        raw_text: str,
        news_type: str,
        target_style: str,
        word_limit: int,
        tone: str,
        constraints: str,
        ollama_host: str,
        model_name: str,
        enable_debug: bool,
        progress=gr.Progress()
    ) -> Tuple[str, str, str, str, str]:
        """
        Process news article through the four-stage pipeline
        Returns: (final_title, final_content, quality_report, stage_logs, error_message)
        """
        try:
            # 重置当前会话数据
            self.current_session_data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'input_params': {
                    'raw_text': raw_text,
                    'news_type': news_type,
                    'target_style': target_style,
                    'word_limit': word_limit,
                    'tone': tone,
                    'constraints': constraints,
                    'ollama_host': ollama_host,
                    'model_name': model_name,
                    'enable_debug': enable_debug
                },
                'stages': {},
                'output': {}
            }
            
            # Validate input
            if not raw_text.strip():
                return "", "", "", "", "請輸入原始文章內容"
            
            progress(0, desc="準備處理...")
            
            # Prepare input config
            cfg = InputConfig(
                raw_data=raw_text,
                news_type=news_type,
                target_style=target_style,
                word_limit=word_limit,
                tone=tone,
                constraints=constraints
            )
            
            # Call pipeline with Ollama overrides
            override_base_url = ollama_host if ollama_host else None
            override_model = model_name if model_name else None
            
            progress(0.1, desc="開始處理...")
            result = interactive_pipeline(
                cfg, 
                interactive=True,
                override_base_url=override_base_url,
                override_model=override_model,
                enable_debug=enable_debug
            )
            
            # Handle result
            if result.get("success"):
                data = result["data"]
                
                # Format logs
                stage_logs = self._format_stage_logs(data.get("stage_logs", []))
                
                # Extract quality report
                quality_report = json.dumps(data.get("quality_report", {}), ensure_ascii=False, indent=2)
                
                # Update session data
                self.current_session_data['stages'] = data.get("stage_logs", [])
                self.current_session_data['output'] = {
                    'title': data.get("best_title", ""),
                    'content': data.get("final_body", ""),
                    'quality_report': data.get("quality_report", {})
                }
                
                return (
                    data.get("best_title", ""),
                    data.get("final_body", ""),
                    quality_report,
                    stage_logs,
                    ""
                )
            else:
                error_msg = result.get("message", "處理失敗")
                return "", "", "", "", error_msg
            
        except Exception as e:
            error_msg = f"處理過程中發生錯誤: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return "", "", "", "", error_msg
    
    def _format_stage_logs(self, logs: List[Dict[str, Any]]) -> str:
        """Format stage logs for display"""
        if not logs:
            return "無階段日誌"
        
        formatted_logs = []
        for log in logs:
            stage_name = log.get("stage", "未知階段")
            status = "成功" if log.get("success", False) else "失敗"
            duration = log.get("duration", "").split('.')[0] if log.get("duration") else "未知"
            
            entry = f"📋 {stage_name}: {status} ({duration})"
            
            # Add error message if any
            if not log.get("success") and log.get("error"):
                entry += f"\n  錯誤: {log.get('error')}"
            
            formatted_logs.append(entry)
        
        return "\n\n".join(formatted_logs)
    
    def export_session_data(self) -> str:
        """Export current session data as JSON and log user preferences"""
        if not self.current_session_data:
            return '{"error": "無可用的會話數據"}'
        
        try:
            # 生成会话ID和时间戳
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            timestamp = datetime.now()
            
            # 准备日志数据
            input_params = self.current_session_data.get('input_params', {})
            stage_logs = self.current_session_data.get('stages', [])
            output_data = self.current_session_data.get('output', {})
            
            # 构建日志条目
            log_entries = []
            
            # 添加初始配置信息
            if input_params:
                config_details = {k: v for k, v in input_params.items() if k != 'raw_text'}
                log_entries.append({"stage": "Initial", "action": "config", "details": config_details})
                log_entries.append({"stage": "Initial", "action": "source", "details": {"source": "WEB_INPUT", "text_len": len(input_params.get('raw_text', ''))}})
            
            # 添加阶段日志
            if stage_logs:
                log_entries.extend(stage_logs)
            
            # 构建最终结果
            final_result = {
                "success": True,
                "data": {
                    "best_title": output_data.get('title', ''),
                    "final_body": output_data.get('content', ''),
                    "quality_report": output_data.get('quality_report', {})
                }
            }
            
            # 调用日志记录函数
            write_consolidated_log_to_csv(
                session_id=session_id,
                start_time=timestamp,
                end_time=timestamp,
                initial_input=input_params.get('raw_text', ''),
                log_entries=log_entries,
                final_result=final_result,
                log_file="pipeline_log.csv",
                json_out_dir="logs/details"
            )
            
            # 返回JSON格式的会话数据
            return json.dumps(self.current_session_data, ensure_ascii=False, indent=2)
        except Exception as e:
            return f'{{"error": "數據導出失敗: {str(e)}"}}'
    
    def process_batch_files(
        self,
        files: List[gr.File],
        news_type: str,
        target_style: str,
        word_limit: int
    ) -> Tuple[str, str]:
        """
        Process multiple news articles in batch
        """
        try:
            if not files:
                return "", "請上傳文件"
            
            results = []
            
            for file in files:
                try:
                    # Read file content
                    with open(file.name, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Process each file
                    cfg = InputConfig(
                        raw_data=content,
                        news_type=news_type,
                        target_style=target_style,
                        word_limit=word_limit,
                        tone="客觀中性"
                    )
                    
                    result = interactive_pipeline(cfg, interactive=False)
                    
                    if result.get("success"):
                        data = result["data"]
                        results.append({
                            "filename": os.path.basename(file.name),
                            "status": "success",
                            "title": data.get("best_title", ""),
                            "content": data.get("final_body", ""),
                            "word_count": len(data.get("final_body", "")),
                            "publishable": data.get("publishable", False)
                        })
                    else:
                        results.append({
                            "filename": os.path.basename(file.name),
                            "status": "error",
                            "error": result.get("message", "處理失敗"),
                            "title": "",
                            "content": ""
                        })
                    
                except Exception as e:
                    results.append({
                        "filename": os.path.basename(file.name),
                        "status": "error",
                        "error": f"文件處理錯誤: {str(e)}",
                        "title": "",
                        "content": ""
                    })
            
            # Convert to CSV
            df = pd.DataFrame(results)
            csv_output = df.to_csv(index=False, encoding='utf-8')
            
            return csv_output, ""
            
        except Exception as e:
            return "", f"批次處理錯誤: {str(e)}"

# 刷新模型列表函数
def refresh_model_list(host, status_indicator):
    """刷新Ollama服务上的可用模型列表"""
    if not host:  # 如果用户没有输入地址，使用默认地址
        host = OLLAMA_BASE_URL
    
    try:
        # 显示加载状态
        status_indicator = gr.update(visible=True, value="正在連接Ollama服務...")
        
        # 调用ollama_utils中的函数获取模型列表
        models = get_available_models(host)
        
        # 提取模型名称列表
        model_names = [model["name"] for model in models]
        
        # 更新状态指示器
        status_indicator = gr.update(visible=True, value=f"成功連接到 {host}，找到 {len(model_names)} 個模型")
        
        # 返回更新后的下拉菜单
        return (
            gr.Dropdown(
                choices=model_names,
                value=model_names[0] if model_names else "",
                label="模型名稱"
            ),
            status_indicator
        )
    except Exception as e:
        error_msg = f"獲取模型列表失敗: {str(e)}"
        print(error_msg)
        # 更新状态指示器显示错误
        status_indicator = gr.update(visible=True, value=error_msg)
        # 返回空下拉菜单
        return (
            gr.Dropdown(choices=[], value="", label="模型名稱 (連接失敗)"),
            status_indicator
        )

# 重置状态指示器函数
def reset_status_indicator():
    return gr.update(visible=False, value="")

# 重置模型下拉菜单函数
def reset_model_dropdown():
    return gr.Dropdown(choices=[], value="", label="模型名稱")

# 提示词管理相关函数
def get_available_stages():
    """获取所有可用的提示词阶段"""
    pm = PromptManager()
    stages = []
    try:
        for file in os.listdir(pm.prompt_dir):
            if file.endswith(".json") and not file.startswith('__'):
                stage_name = file[:-5]  # 移除.json后缀
                stages.append(stage_name)
        return stages
    except Exception as e:
        print(f"获取可用阶段失败: {e}")
        return []

def load_stage_content(stage_name):
    """加载指定阶段的提示词内容（支持分字段编辑）"""
    pm = PromptManager()
    try:
        # 加载完整的阶段内容
        content = pm.load_stage(stage_name)
        
        # 提取基本提示词
        system = content.get('base', {}).get('system', '')
        user = content.get('base', {}).get('user', '')
        
        # 提取按类型/风格/语气配置的提示词
        news_type_config = json.dumps(content.get('by_news_type', {}), ensure_ascii=False, indent=2)
        target_style_config = json.dumps(content.get('by_target_style', {}), ensure_ascii=False, indent=2)
        tone_config = json.dumps(content.get('by_tone', {}), ensure_ascii=False, indent=2)
        
        return system, user, news_type_config, target_style_config, tone_config
    except Exception as e:
        print(f"加载阶段内容失败: {e}")
        # 如果出错，返回空值
        return "", "", "{}", "{}", "{}"

def save_stage_content(stage_name, system, user, news_type_config, target_style_config, tone_config):
    """保存提示词内容（支持分字段编辑）"""
    pm = PromptManager()
    try:
        # 构建完整的数据结构
        data = {
            "base": {
                "system": system,
                "user": user
            },
            "by_news_type": {},
            "by_target_style": {},
            "by_tone": {}
        }
        
        # 解析高级配置
        if news_type_config.strip():
            try:
                data["by_news_type"] = json.loads(news_type_config)
            except json.JSONDecodeError:
                return "新聞類型配置 JSON格式錯誤"
        
        if target_style_config.strip():
            try:
                data["by_target_style"] = json.loads(target_style_config)
            except json.JSONDecodeError:
                return "目標媒體風格配置 JSON格式錯誤"
        
        if tone_config.strip():
            try:
                data["by_tone"] = json.loads(tone_config)
            except json.JSONDecodeError:
                return "語氣配置 JSON格式錯誤"
        
        # 保存到文件
        file_path = os.path.join(pm.prompt_dir, f"{stage_name}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return "保存成功"
    except Exception as e:
        return f"保存失敗: {str(e)}"

def delete_stage(stage_name, confirm_text):
    """删除指定的提示词阶段（需要确认）"""
    pm = PromptManager()
    try:
        # 验证确认文本
        if confirm_text != "DELETE":
            return "請輸入 DELETE 以確認刪除"
            
        # 检查是否是系统关键阶段
        critical_stages = ['alpha', 'beta', 'gamma', 'delta']
        if stage_name in critical_stages:
            return "警告: 系統關鍵階段不能刪除"
        
        file_path = os.path.join(pm.prompt_dir, f"{stage_name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return f"階段 {stage_name} 已成功刪除"
        else:
            return f"階段 {stage_name} 不存在"
    except Exception as e:
        return f"刪除失敗: {str(e)}"

def create_new_stage(new_stage_name):
    """创建新的提示词阶段"""
    pm = PromptManager()
    try:
        # 验证阶段名
        if not new_stage_name or not new_stage_name.strip():
            return "階段名稱不能為空"
        
        # 检查是否已存在
        file_path = os.path.join(pm.prompt_dir, f"{new_stage_name}.json")
        if os.path.exists(file_path):
            return f"階段 {new_stage_name} 已存在"
        
        # 创建默认结构
        default_structure = {
            "base": {
                "system": "",
                "user": ""
            },
            "by_news_type": {},
            "by_target_style": {},
            "by_tone": {}
        }
        
        # 保存到文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_structure, f, ensure_ascii=False, indent=2)
        
        return f"階段 {new_stage_name} 已成功創建"
    except Exception as e:
        return f"創建失敗: {str(e)}"

# 覆盖提示词相关函数
def check_override_exist(stage_name):
    """检查是否有覆盖提示词"""
    pm = PromptManager()
    try:
        override_path = pm._override_path(stage_name)
        return os.path.exists(override_path)
    except Exception as e:
        print(f"检查覆盖文件失败: {e}")
        return False

def load_override_content(stage_name):
    """加载覆盖提示词内容（支持分字段编辑）"""
    pm = PromptManager()
    try:
        content = pm.load_override(stage_name)
        
        # 提取基本提示词
        system = content.get('base', {}).get('system', '')
        user = content.get('base', {}).get('user', '')
        
        # 提取按类型/风格/语气配置的提示词
        news_type_config = json.dumps(content.get('by_news_type', {}), ensure_ascii=False, indent=2)
        target_style_config = json.dumps(content.get('by_target_style', {}), ensure_ascii=False, indent=2)
        tone_config = json.dumps(content.get('by_tone', {}), ensure_ascii=False, indent=2)
        
        return system, user, news_type_config, target_style_config, tone_config
    except Exception as e:
        print(f"加载覆盖内容失败: {e}")
        # 如果出错，返回空值
        return "", "", "{}", "{}", "{}"

def save_override_content(stage_name, system, user, news_type_config, target_style_config, tone_config):
    """保存覆盖提示词内容（支持分字段编辑）"""
    pm = PromptManager()
    try:
        # 构建完整的数据结构
        data = {
            "base": {
                "system": system,
                "user": user
            },
            "by_news_type": {},
            "by_target_style": {},
            "by_tone": {}
        }
        
        # 解析高级配置
        if news_type_config.strip():
            try:
                data["by_news_type"] = json.loads(news_type_config)
            except json.JSONDecodeError:
                return "新聞類型配置 JSON格式錯誤"
        
        if target_style_config.strip():
            try:
                data["by_target_style"] = json.loads(target_style_config)
            except json.JSONDecodeError:
                return "目標媒體風格配置 JSON格式錯誤"
        
        if tone_config.strip():
            try:
                data["by_tone"] = json.loads(tone_config)
            except json.JSONDecodeError:
                return "語氣配置 JSON格式錯誤"
        
        # 保存覆盖文件
        pm.save_override(stage_name, data)
        
        return "保存成功"
    except Exception as e:
        return f"保存失敗: {str(e)}"

def delete_override(stage_name):
    """删除覆盖提示词"""
    pm = PromptManager()
    try:
        override_path = pm._override_path(stage_name)
        if os.path.exists(override_path):
            os.remove(override_path)
            return f"自定義配置已成功刪除"
        else:
            return f"自定義配置不存在"
    except Exception as e:
        return f"刪除失敗: {str(e)}"

def create_gradio_interface():
    """Create and configure the Gradio interface"""
    workflow = GradioNewsWorkflow()
    
    with gr.Blocks(
        title="LangChain 新聞工作流程",
        theme=gr.themes.Soft(),
        css="""
        .main-container { max-width: 1200px; margin: auto; }
        .stage-info { background: #f0f8ff; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .prompt-editor { height: 400px; }
        .prompt-section { margin-bottom: 20px; }
        """
    ) as interface:
        
        gr.Markdown("""
        # 🚀 LangChain 新聞工作流程
        
        歡迎使用 AI 驅動的新聞稿生成系統！本系統透過四個階段（Alpha、Beta、Gamma、Delta）
        將原始資料轉換為專業的新聞稿。
        
        ## 🔄 處理流程
        - **Alpha 階段**: 結構化草稿生成
        - **Beta 階段**: 風格適配
        - **Gamma 階段**: 標題生成
        - **Delta 階段**: 最終審核與定稿
        """)
        
        with gr.Tabs() as tabs:
            # Single article processing tab
            with gr.Tab("📝 單篇文章處理") as single_tab:
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("### 📋 輸入配置")
                        
                        raw_text = gr.Textbox(
                            label="原始文章內容",
                            placeholder="請貼上原始新聞資料...",
                            lines=8,
                            max_lines=15
                        )
                        
                        with gr.Row():
                            # 在create_gradio_interface函数中，创建UI组件前获取选项
                            options = workflow._load_prompt_options()
                        
                        news_type = gr.Dropdown(
                            label="新聞類型",
                            choices=options['news_types'],
                            value="財經" if "財經" in options['news_types'] else options['news_types'][0]
                        )
                        
                        target_style = gr.Dropdown(
                            label="目標媒體風格",
                            choices=options['target_styles'],
                            value="經濟日報" if "經濟日報" in options['target_styles'] else options['target_styles'][0]
                        )
                        
                        tone = gr.Dropdown(
                            label="語氣風格",
                            choices=options['tones'],
                            value="客觀中性" if "客觀中性" in options['tones'] else options['tones'][0]
                        )
                        
                        word_limit = gr.Slider(
                            label="目標字數",
                            minimum=200,
                            maximum=2000,
                            step=50,
                            value=800
                        )
                        
                        constraints = gr.Textbox(
                            label="特殊限制 (選填)",
                            placeholder="例如：避免使用特定詞彙、強調某些觀點等...",
                            lines=2
                        )
                        
                        with gr.Accordion("🔧 進階設定", open=False):
                            ollama_host = gr.Textbox(
                                label="Ollama 服務位址",
                                placeholder=f"預設: {OLLAMA_BASE_URL}",
                                value=""
                            )
                            
                            # 添加刷新按钮和模型下拉选择框
                            with gr.Row():
                                model_refresh_btn = gr.Button("🔄 刷新模型列表", size="sm")
                            
                            # Ollama模型选择器和刷新按钮
                            model_name = gr.Dropdown(
                                label="选择Ollama模型",
                                choices=["llama3:8b", "gemma:7b", "mistral:7b", "phi3:3.8b"],
                                value="llama3:8b",
                                interactive=True,
                                show_label=True,
                                allow_custom_value=True
                            )
                            
                            # 添加状态指示器
                            status_indicator = gr.Textbox(
                                label="Ollama 連接狀態",
                                value="",
                                interactive=False,
                                visible=False
                            )
                            
                            enable_debug = gr.Checkbox(
                                label="啟用除錯模式 (顯示提示詞)",
                                value=False
                            )
                        
                        process_btn = gr.Button("🚀 開始處理", variant="primary", size="lg")
                    
                    with gr.Column(scale=3):
                        gr.Markdown("### 📊 處理結果")
                        
                        with gr.Group():
                            final_title = gr.Textbox(
                                label="📰 最終標題",
                                lines=2,
                                interactive=True
                            )
                            
                            final_content = gr.Textbox(
                                label="📄 最終內容",
                                lines=15,
                                max_lines=25,
                                interactive=True
                            )
                        
                        with gr.Accordion("📈 品質報告", open=False):
                            quality_report = gr.Textbox(
                                label="品質分析",
                                lines=8,
                                interactive=False
                            )
                        
                        with gr.Accordion("📋 處理日誌", open=False):
                            stage_logs = gr.Textbox(
                                label="階段日誌",
                                lines=6,
                                interactive=False
                            )
                        
                        error_output = gr.Textbox(
                            label="錯誤訊息",
                            visible=False,
                            interactive=False
                        )
                        
                        with gr.Row():
                            export_btn = gr.Button("💾 匯出會話數據", size="sm")
                            session_data = gr.Textbox(
                                label="會話數據 (JSON)",
                                visible=False,
                                lines=10
                            )
                    
            # Batch processing tab
            with gr.Tab("📁 批量处理文件") as batch_tab:
                gr.Markdown("### 批量处理多份文章\n\n上传多个txt文件，一次性完成多篇文章的智能编辑，适合需要处理大量文档的用户。")
                
                with gr.Row():
                    with gr.Column():
                        file_upload = gr.Files(
                            label="上传文本文件 (.txt)",
                            file_types=[".txt"],
                            file_count="multiple"
                        )
                        
                        with gr.Row():
                            # 在create_gradio_interface函数中，创建UI组件前获取选项
                            batch_options = workflow._load_prompt_options()
                        
                        with gr.Row():
                            batch_news_type = gr.Dropdown(
                                label="文章类型",
                                choices=batch_options['news_types'],
                                value="財經" if "財經" in batch_options['news_types'] else batch_options['news_types'][0]
                            )
                            batch_target_style = gr.Dropdown(
                                label="风格类型",
                                choices=batch_options['target_styles'],
                                value="經濟日報" if "經濟日報" in batch_options['target_styles'] else batch_options['target_styles'][0]
                            )
                            batch_word_limit = gr.Slider(
                                label="目标字数",
                                minimum=200,
                                maximum=2000,
                                step=50,
                                value=800
                            )
                        
                        # 高级设置（可选）
                        with gr.Accordion("🔧 高级设置", open=False):
                            batch_ollama_host = gr.Textbox(
                                label="Ollama 服务地址",
                                placeholder=f"默认: {OLLAMA_BASE_URL}",
                                value=""
                            )
                            
                            # 添加刷新按钮和模型下拉选择框
                            with gr.Row():
                                batch_model_refresh_btn = gr.Button("🔄 刷新模型列表", size="sm")
                            
                            batch_model_name = gr.Dropdown(
                                label="选择AI模型",
                                choices=["llama3:8b", "gemma:7b", "mistral:7b", "phi3:3.8b"],
                                value="llama3:8b",
                                interactive=True,
                                show_label=True,
                                allow_custom_value=True
                            )
                            
                            # 添加状态指示器
                            batch_status_indicator = gr.Textbox(
                                label="AI服务连接状态",
                                value="",
                                interactive=False,
                                visible=False
                            )
                        
                        batch_process_btn = gr.Button("🔄 开始批量处理", variant="primary")
                    
                    with gr.Column():
                        batch_results = gr.Textbox(
                            label="📊 处理结果 (CSV格式)",
                            lines=15,
                            interactive=False
                        )
                        
                        batch_error = gr.Textbox(
                            label="错误信息",
                            visible=False,
                            interactive=False
                        )
                        
            # Prompt management tab
            with gr.Tab("🛠️ 提示词管理") as prompt_tab:
                gr.Markdown("""
                ### 📝 提示词管理工具
                在此頁面您可以查看、編輯、創建和管理提示词配置。
                """)
                
                with gr.Row():
                    with gr.Column(scale=1):
                        # 阶段选择和管理
                        gr.Markdown("#### 提示词階段管理")
                        
                        # 初始获取可用阶段
                        available_stages = get_available_stages()
                        
                        stage_selector = gr.Dropdown(
                            label="選擇提示词階段",
                            choices=available_stages,
                            value="alpha" if "alpha" in available_stages else (available_stages[0] if available_stages else ""),
                            interactive=True
                        )
                        
                        refresh_stages_btn = gr.Button("🔄 刷新階段列表", size="sm")
                        
                        with gr.Row():
                            save_stage_btn = gr.Button("💾 保存階段", size="sm")
                            delete_stage_btn = gr.Button("🗑️ 刪除階段", size="sm", variant="stop")
                            
                        gr.Markdown("**提示：** 选择阶段后会自动加载内容，修改后请点击保存按钮。")
                        
                        # 创建新阶段
                        with gr.Row() as new_stage_row:
                            new_stage_name = gr.Textbox(
                                label="新階段名稱",
                                placeholder="輸入新階段名稱",
                                lines=1,
                                scale=2
                            )
                            create_stage_btn = gr.Button("✨ 創建新階段", size="sm", scale=1)
                        
                        # 状态消息
                        prompt_status = gr.Textbox(
                            label="操作狀態",
                            value="",
                            interactive=False,
                            visible=False
                        )
                        
                        # 自定义配置管理
                        gr.Markdown("#### 自定義配置管理")
                        
                        gr.Markdown("""
                        **自定義配置**是一種特殊的配置保存方式，它允許您修改和保存特定階段的提示词，而不影響原始配置文件。
                        - 開啟此選項時，系統將使用您自定義的提示词配置
                        - 新建立階段時，此選項默認為關閉，使用原始配置
                        - 自定義配置保存在獨立的文件中，可隨時開啟/關閉或刪除
                        """)
                        
                        override_checkbox = gr.Checkbox(
                            label="使用自定義配置 (將使用您保存的自定義版本，而非原始配置)",
                            value=False
                        )
                        
                        with gr.Row():
                            save_override_btn = gr.Button("💾 另存為自定義配置", size="sm")
                            delete_override_btn = gr.Button("🗑️ 刪除自定義配置", size="sm", variant="stop")
                        
                        override_status = gr.Textbox(
                            label="自定義配置操作狀態",
                            value="",
                            interactive=False,
                            visible=False
                        )
                    
                    with gr.Column(scale=3):
                        gr.Markdown("#### 提示词內容編輯器")
                        
                        # 基础提示词编辑区域
                        gr.Markdown("**📋 基礎提示词**")
                        system_prompt = gr.Textbox(
                            label="System 提示词",
                            lines=5,
                            max_lines=10,
                            interactive=True
                        )
                        user_prompt = gr.Textbox(
                            label="User 提示词",
                            lines=8,
                            max_lines=15,
                            interactive=True
                        )
                        
                        # 特殊说明
                        gr.Markdown("""
                        **提示：** 提示词中可以使用 `{news_type}`, `{target_style}`, `{tone}`, `{word_limit}` 等佔位符，
                        在實際使用時將被替換為相應的值。
                        """)
                        
                        # 高级配置
                        with gr.Accordion("🔧 高级配置 (特定类型/风格/语气的追加提示词)", open=True):
                            gr.Markdown("**提示：** 所有配置通过下方表单进行，系统将自动生成所需的JSON格式，无需手动编辑。")
                            
                            # 按新闻类型配置
                            with gr.Row():
                                gr.Markdown("**📰 按新闻类型配置**")
                            
                            # 获取默认的新闻类型选项
                            default_news_types = list(DEFAULT_SUMMARIES["news_type"].keys()) if "DEFAULT_SUMMARIES" in globals() else ['財經', '科技', '產業', '事件', '政策']
                            
                            # 新闻类型配置的UI组件 - 调整顺序，先显示已配置列表
                            news_type_list = gr.Dataframe(
                                label="已配置的新聞類型",
                                headers=["類型", "提示词"],
                                datatype=["str", "str"],
                                interactive=False
                            )
                            

                            
                            with gr.Row():
                                news_type_selector = gr.Dropdown(
                                    label="選擇新聞類型",
                                    choices=default_news_types + ["自定義"],
                                    value="財經"
                                )
                                custom_news_type = gr.Textbox(
                                    label="自定義新聞類型",
                                    visible=False,
                                    placeholder="輸入自定義類型名稱"
                                )
                            
                            news_type_prompt = gr.Textbox(
                                label="编辑提示词",
                                lines=2,
                                placeholder="強調數據與市場影響",
                                interactive=True
                            )
                            
                            save_news_type_btn = gr.Button("💾 保存新聞類型配置")
                            
                            # 隐藏的JSON编辑器（用于内部数据交换）
                            news_type_editor = gr.Textbox(visible=False)
                            
                            # 分隔线
                            gr.Markdown("---")
                            
                            # 按目标风格配置
                            with gr.Row():
                                gr.Markdown("**🎨 按目标风格配置**")
                            
                            # 获取默认的目标风格选项
                            default_styles = list(DEFAULT_SUMMARIES["target_style"].keys()) if "DEFAULT_SUMMARIES" in globals() else ['經濟日報', '中央社', '數位時代', '券商研報']
                            
                            # 目标风格配置的UI组件
                            style_list = gr.Dataframe(
                                label="已配置的目標風格",
                                headers=["風格", "提示词"],
                                datatype=["str", "str"],
                                interactive=False
                            )
                            

                            
                            with gr.Row():
                                style_selector = gr.Dropdown(
                                    label="選擇目標風格",
                                    choices=default_styles + ["自定義"],
                                    value="經濟日報"
                                )
                                custom_style = gr.Textbox(
                                    label="自定義目標風格",
                                    visible=False,
                                    placeholder="輸入自定義風格名稱"
                                )
                            
                            style_prompt = gr.Textbox(
                                label="编辑提示词",
                                lines=2,
                                placeholder="倒金字塔結構，正式專業，財經術語適中",
                                interactive=True
                            )
                            
                            save_style_btn = gr.Button("💾 保存目標風格配置")
                            
                            # 隐藏的JSON编辑器（用于内部数据交换）
                            style_editor = gr.Textbox(visible=False)
                            
                            # 分隔线
                            gr.Markdown("---")
                            
                            # 按语气配置
                            with gr.Row():
                                gr.Markdown("**😊 按语气配置**")
                            
                            # 获取默认的语气选项
                            default_tones = list(DEFAULT_SUMMARIES["tone"].keys()) if "DEFAULT_SUMMARIES" in globals() else ['客觀中性', '積極正面', '謹慎保守']
                            
                            # 语气配置的UI组件
                            tone_list = gr.Dataframe(
                                label="已配置的語氣",
                                headers=["語氣", "提示词"],
                                datatype=["str", "str"],
                                interactive=False
                            )
                            

                            
                            with gr.Row():
                                tone_selector = gr.Dropdown(
                                    label="選擇語氣",
                                    choices=default_tones + ["自定義"],
                                    value="客觀中性"
                                )
                                custom_tone = gr.Textbox(
                                    label="自定義語氣",
                                    visible=False,
                                    placeholder="輸入自定義語氣名稱"
                                )
                            
                            tone_prompt = gr.Textbox(
                                label="编辑提示词",
                                lines=2,
                                placeholder="保持客觀描述，避免誇張與推測",
                                interactive=True
                            )
                            
                            save_tone_btn = gr.Button("💾 保存語氣配置")
                            
                            # 隐藏的JSON编辑器（用于内部数据交换）
                            tone_editor = gr.Textbox(visible=False)
                        
                        # 提示
                        gr.Markdown("**提示：** 所有配置將在保存階段時自動儲存。")
                        

                        


        # 初始化函数，用于加载配置到新UI
        def initialize_advanced_config(stage_name):
            if not stage_name:
                return gr.update(value=[]), gr.update(value=[]), gr.update(value=[]), "{}", "{}", "{}"

            # 加载阶段内容
            _, _, news_type_json, target_style_json, tone_json = load_stage_content(stage_name)

            try:
                # 解析JSON数据
                news_type_data = json.loads(news_type_json) if news_type_json.strip() else {}
                target_style_data = json.loads(target_style_json) if target_style_json.strip() else {}
                tone_data = json.loads(tone_json) if tone_json.strip() else {}

                # 转换为DataFrame格式
                news_type_df = [[k, v.get('user_append', '')] for k, v in news_type_data.items()]
                target_style_df = [[k, v.get('user_append', '')] for k, v in target_style_data.items()]
                tone_df = [[k, v.get('user_append', '')] for k, v in tone_data.items()]

                return (
                    gr.update(value=news_type_df),
                    gr.update(value=target_style_df),
                    gr.update(value=tone_df),
                    news_type_json,
                    target_style_json,
                    tone_json
                )
            except Exception as e:
                print(f"初始化高级配置失败: {e}")
                return gr.update(value=[]), gr.update(value=[]), gr.update(value=[]), "{}", "{}", "{}"

        # 更新JSON数据函数
        def update_json_data(config_type, action, key, value, current_json):
            try:
                data = json.loads(current_json) if current_json.strip() else {}

                if action == "add" or action == "update":
                    data[key] = {"user_append": value}

                return json.dumps(data, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"更新JSON数据失败: {e}")
                return current_json

        # 添加配置项函数
        def add_config_item(config_type, selector_value, custom_value, prompt, current_dataframe, current_json):
            # 确定配置项的键
            if selector_value == "自定義":
                if not custom_value or not custom_value.strip():
                    return current_dataframe, current_json, "自定義名稱不能為空"
                key = custom_value.strip()
            else:
                key = selector_value

            # 检查是否已存在
            if any(row[0] == key for row in current_dataframe):
                return current_dataframe, current_json, f"{key} 已存在"

            # 更新JSON数据
            new_json = update_json_data(config_type, "add", key, prompt, current_json)

            # 更新DataFrame
            new_dataframe = current_dataframe.copy()
            new_dataframe.append([key, prompt])

            return new_dataframe, new_json, f"成功添加 {key}"

        # 更新配置项函数
        def update_config_item(config_type, selector_value, custom_value, prompt, current_dataframe, current_json):
            # 确定配置项的键
            if selector_value == "自定義":
                if not custom_value or not custom_value.strip():
                    return current_dataframe, current_json, "自定義名稱不能為空"
                key = custom_value.strip()
            else:
                key = selector_value

            # 检查是否存在
            key_exists = any(row[0] == key for row in current_dataframe)
            if not key_exists:
                return current_dataframe, current_json, f"{key} 不存在"

            # 更新JSON数据
            new_json = update_json_data(config_type, "update", key, prompt, current_json)

            # 更新DataFrame
            new_dataframe = []
            for row in current_dataframe:
                if row[0] == key:
                    new_dataframe.append([key, prompt])
                else:
                    new_dataframe.append(row)

            return new_dataframe, new_json, f"成功更新 {key}"



        # 自定義选项显示切换
        def toggle_custom_input(selector_value, custom_input):
            return gr.update(visible=(selector_value == "自定義"))

        # 加载选择项的提示词
        def load_prompt_for_selection(selector_value, custom_value, list_df):
            # 确定配置项的键
            if selector_value == "自定義":
                key = custom_value.strip() if custom_value else ""
            else:
                key = selector_value

            # 1. 先在DataFrame中查找对应的提示词
            for row in list_df:
                if row[0] == key:
                    return row[1]  # 返回已配置的提示词

            # 2. 如果找不到已配置的提示词，从DEFAULT_SUMMARIES中获取默认提示词
            try:
                from app_utils.prompt_manager import DEFAULT_SUMMARIES
                if key and "DEFAULT_SUMMARIES" in globals() and key in DEFAULT_SUMMARIES.get("news_type", {}):
                    return DEFAULT_SUMMARIES["news_type"][key]
            except Exception as e:
                print(f"加载默认提示词失败: {e}")

            # 如果都找不到，返回空字符串
            return ""

        # 自定義选项事件绑定和加载提示词
        news_type_selector.change(
            fn=toggle_custom_input,
            inputs=[news_type_selector, custom_news_type],
            outputs=[custom_news_type]
        ).then(
            fn=load_prompt_for_selection,
            inputs=[news_type_selector, custom_news_type, news_type_list],
            outputs=[news_type_prompt]
        )
        
        # 目标风格的自定義选项事件绑定和加载提示词
        style_selector.change(
            fn=toggle_custom_input,
            inputs=[style_selector, custom_style],
            outputs=[custom_style]
        ).then(
            fn=load_prompt_for_selection,
            inputs=[style_selector, custom_style, style_list],
            outputs=[style_prompt]
        )
        
        # 语气的自定義选项事件绑定和加载提示词
        tone_selector.change(
            fn=toggle_custom_input,
            inputs=[tone_selector, custom_tone],
            outputs=[custom_tone]
        ).then(
            fn=load_prompt_for_selection,
            inputs=[tone_selector, custom_tone, tone_list],
            outputs=[tone_prompt]
        )

        # 创建包装函数来捕获常量值
        def wrap_save_config_item(config_type):
            def wrapper(selector, custom_input, prompt, list_df, editor):
                # 确定配置项的键
                if selector == "自定義":
                    if not custom_input or not custom_input.strip():
                        return list_df, editor, "自定義名稱不能為空"
                    key = custom_input.strip()
                else:
                    key = selector

                # 更新JSON数据
                new_json = update_json_data(config_type, "add", key, prompt, editor)

                # 更新DataFrame
                try:
                    current_data = json.loads(editor) if editor.strip() else {}
                except:
                    current_data = {}
                
                # 确保key存在于current_data中
                if key not in current_data:
                    current_data[key] = {}
                current_data[key]['user_append'] = prompt
                
                # 转换为DataFrame格式
                new_dataframe = [[k, v.get('user_append', '')] for k, v in current_data.items()]

                # 返回更新后的DataFrame和JSON
                return new_dataframe, new_json, f"成功保存 {key}"
            return wrapper



        # 新闻类型配置事件
        save_news_type_btn.click(
            fn=wrap_save_config_item("news_type"),
            inputs=[
                news_type_selector, custom_news_type, news_type_prompt,
                news_type_list, news_type_editor
            ],
            outputs=[news_type_list, news_type_editor, prompt_status]
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=[prompt_status]
        ).then(
            fn=lambda: gr.update(visible=False),
            outputs=[prompt_status],
            queue=False
        )
        
        # 目标风格配置事件
        save_style_btn.click(
            fn=wrap_save_config_item("target_style"),
            inputs=[
                style_selector, custom_style, style_prompt,
                style_list, style_editor
            ],
            outputs=[style_list, style_editor, prompt_status]
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=[prompt_status]
        ).then(
            fn=lambda: gr.update(visible=False),
            outputs=[prompt_status],
            queue=False
        )
        
        # 语气配置事件
        save_tone_btn.click(
            fn=wrap_save_config_item("tone"),
            inputs=[
                tone_selector, custom_tone, tone_prompt,
                tone_list, tone_editor
            ],
            outputs=[tone_list, tone_editor, prompt_status]
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=[prompt_status]
        ).then(
            fn=lambda: gr.update(visible=False),
            outputs=[prompt_status],
            queue=False
        )
        


        # 阶段选择器变更时自动加载内容
        stage_selector.change(
            fn=lambda stage: load_stage_content(stage) if stage else ("", "", "{}", "{}", ""),
            inputs=[stage_selector],
            outputs=[system_prompt, user_prompt, news_type_editor, style_editor, tone_editor]
        ).then(
            fn=lambda stage: initialize_advanced_config(stage),
            inputs=[stage_selector],
            outputs=[news_type_list, style_list, tone_list, news_type_editor, style_editor, tone_editor]
        ).then(
            fn=lambda stage: check_override_exist(stage) if stage else False,
            inputs=[stage_selector],
            outputs=[override_checkbox]
        )

        # 界面加载时自动加载默认阶段内容
        def load_initial_content():
            available_stages = get_available_stages()
            default_stage = "alpha" if "alpha" in available_stages else (available_stages[0] if available_stages else "")
            if default_stage:
                content = load_override_content(default_stage) if check_override_exist(default_stage) else load_stage_content(default_stage)
                # 返回需要的所有值
                return content[0], content[1], content[2], content[3], content[4]
            return "", "", "{}", "{}", "{}"

        # 在界面加载时触发
        interface.load(
            fn=load_initial_content,
            outputs=[system_prompt, user_prompt, news_type_editor, style_editor, tone_editor]
        ).then(
            fn=lambda: "alpha" if "alpha" in get_available_stages() else (get_available_stages()[0] if get_available_stages() else ""),
            outputs=[stage_selector]
        ).then(
            fn=lambda stage: initialize_advanced_config(stage),
            inputs=[stage_selector],
            outputs=[news_type_list, style_list, tone_list, news_type_editor, style_editor, tone_editor]
        ).then(
            fn=lambda stage: check_override_exist(stage) if stage else False,
            inputs=[stage_selector],
            outputs=[override_checkbox]
        )

        return interface

def main():
    """Main function to launch the Gradio interface"""
    interface = create_gradio_interface()
    
    # Launch the interface
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_api=False,
        inbrowser=True
    )

if __name__ == "__main__":
    main()