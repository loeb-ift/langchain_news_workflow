import gradio as gr
import json
import os
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import re
from datetime import datetime

from pipeline import InputConfig, interactive_pipeline

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GradioNewsWorkflow:
    def __init__(self):
        """初始化Gradio新聞工作流程"""
        # 加載環境變量
        from dotenv import load_dotenv
        load_dotenv()
        
        self.cfg = InputConfig(
            raw_data="",
            news_type="財經",
            target_style="經濟日報",
            word_limit=800,
            tone="客觀中性"
        )
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:20b")
        self.llm_client = self._setup_ollama_client()
        self.prompts = self.load_prompts()  # 添加這行來加載提示詞

    def _setup_ollama_client(self):
        """設置Ollama客戶端"""
        try:
            from ollama import Client
            print(f"🔗 連接到 Ollama: {self.ollama_base_url}")
            return Client(host=self.ollama_base_url)
        except ImportError:
            print("警告：無法導入ollama，將使用模擬客戶端")
            return None

    def update_config(self, new_base_url: str, new_model_name: str) -> str:
        """動態更新Ollama配置"""
        try:
            # 驗證URL格式
            if not new_base_url.startswith('http'):
                return "❌ 錯誤：URL必須以http://或https://開頭"
            
            # 更新配置
            self.ollama_base_url = new_base_url.rstrip('/')
            self.model_name = new_model_name
            
            # 重新初始化Ollama客戶端
            from ollama import Client
            self.llm_client = Client(host=self.ollama_base_url)
            
            # 測試連接
            try:
                self.llm_client.list()
                return f"✅ 配置更新成功！\nLLM提供商：{self.ollama_base_url}\n使用模型：{self.model_name}"
            except Exception as e:
                return f"⚠️ 配置已更新，但連接測試失敗：{str(e)}"
                
        except Exception as e:
            return f"❌ 配置更新失敗：{str(e)}"

    def get_available_models(self) -> list:
        """獲取可用的模型列表，返回列表格式"""
        try:
            models = self.llm_client.list()
            model_names = [model['name'] for model in models.get('models', [])]
            return model_names if model_names else [self.model_name]
        except Exception as e:
            print(f"獲取模型列表失敗：{str(e)}")
            return [self.model_name]
    
    def refresh_models_from_host(self, host_url: str) -> tuple:
        """從指定HOST刷新模型列表"""
        try:
            # 驗證URL格式
            if not host_url.startswith('http'):
                return [self.model_name], "❌ 錯誤：URL必須以http://或https://開頭"
            
            # 臨時創建客戶端獲取模型列表
            from ollama import Client
            temp_client = Client(host=host_url.rstrip('/'))
            
            # 獲取模型列表
            response = temp_client.list()
            
            # 根據Ollama API實際響應格式獲取模型名稱
            if isinstance(response, dict) and 'models' in response:
                model_names = [model['name'] for model in response['models']]
            elif isinstance(response, list):
                # 某些版本的Ollama直接返回列表
                model_names = [model['name'] for model in response]
            else:
                # 處理其他可能的響應格式
                model_names = [model['name'] for model in response.models]
            
            if model_names:
                return model_names, f"✅ 成功獲取 {len(model_names)} 個模型"
            else:
                return [self.model_name], "⚠️ 該HOST沒有可用模型"
                
        except Exception as e:
            return [self.model_name], f"❌ 獲取模型列表失敗：{str(e)}"
        print("✅ Gradio新聞工作流程初始化完成")
    
    def load_prompts(self):
        """加載所有提示詞模板"""
        prompts = {}
        prompts_dir = Path("prompts")
        
        # 確保提示詞目錄存在
        prompts_dir.mkdir(exist_ok=True)
        
        # 定義默認提示詞
        default_prompts = {
            "alpha": """你是新聞分析專家，請分析以下新聞內容並提取關鍵信息：

新聞內容：{content}

新聞類型：{news_type}
字數限制：{word_limit}
語氣風格：{tone}
目標媒體：{target_style}

請提供：
1. 主要事件摘要（100字內）
2. 關鍵人物和組織
3. 時間和地點
4. 潛在影響
5. 背景資訊

請用繁體中文回答，保持專業和客觀。""",
            
            "beta": """基於以下Alpha階段分析結果，請進行深度分析：

Alpha分析結果：{alpha_result}

新聞類型：{news_type}
字數限制：{word_limit}
語氣風格：{tone}
目標媒體：{target_style}

請提供：
1. 事件背後的深層原因
2. 可能的發展趨勢
3. 對相關產業的影響
4. 社會和經濟層面的分析
5. 專家觀點和預測

請用繁體中文回答，保持深度和洞察力。""",
            
            "gamma": """基於Alpha和Beta階段的分析，請創建一篇專業的新聞報導：

Alpha分析：{alpha_result}
Beta分析：{beta_result}

要求：
- 新聞類型：{news_type}
- 字數：{word_limit}字左右
- 語氣：{tone}
- 風格：{target_style}

請創建：
1. 吸引人的標題（20字內）
2. 引人入勝的導言
3. 結構清晰的主體內容
4. 有力的結論
5. 保持專業性和可讀性

請直接輸出完整的報導文章。""",
            
            "delta": """請對以下新聞報導進行最終審核和優化：

報導內容：{gamma_result}

審核標準：
- 目標媒體：{target_style}
- 字數要求：{word_limit}字
- 語氣風格：{tone}
- 新聞類型：{news_type}

請檢查：
1. 事實準確性
2. 語言流暢度
3. 結構完整性
4. 標題吸引力
5. 整體質量
6. 是否符合發布標準

請提供：
- 優化後的最終版本
- 簡要的審核意見
- 發布建議

使用繁體中文回答。"""
        }
        
        # 從文件加載提示詞，如果文件不存在則創建
        for stage, default_prompt in default_prompts.items():
            prompt_file = prompts_dir / f"{stage}_prompt.txt"
            
            if prompt_file.exists():
                try:
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        prompts[stage] = f.read()
                except Exception as e:
                    print(f"警告：無法讀取 {prompt_file}，使用默認提示詞: {e}")
                    prompts[stage] = default_prompt
            else:
                # 創建默認提示詞文件
                try:
                    with open(prompt_file, 'w', encoding='utf-8') as f:
                        f.write(default_prompt)
                    prompts[stage] = default_prompt
                    print(f"已創建 {prompt_file} 默認提示詞")
                except Exception as e:
                    print(f"警告：無法創建 {prompt_file}，使用內存提示詞: {e}")
                    prompts[stage] = default_prompt
        
        return prompts

    def process_single_article(self, content):
        """處理單篇文章的完整流程"""
        try:
            print(f"開始處理單篇文章，內容長度: {len(content)} 字符")
            
            # 初始化各階段結果
            alpha_result = ""
            beta_result = ""
            gamma_result = ""
            delta_result = ""
            
            # 執行Alpha階段 - 資訊架構師
            print("開始Alpha階段...")
            alpha_prompt = self.prompts.get("alpha", "").format(
                content=content,
                news_type=self.cfg.news_type,
                word_limit=self.cfg.word_limit,
                tone=self.cfg.tone,
                target_style=self.cfg.target_style
            )
            
            alpha_response = self.llm_client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": alpha_prompt}],
                stream=False
            )
            
            if hasattr(alpha_response, 'message'):
                alpha_result = alpha_response.message.content
            elif isinstance(alpha_response, dict) and 'message' in alpha_response:
                alpha_result = alpha_response['message']['content']
            else:
                alpha_result = str(alpha_response)
            
            print("Alpha階段完成")
            
            # 執行Beta階段 - 風格塑造師
            print("開始Beta階段...")
            beta_prompt = self.prompts.get("beta", "").format(
                alpha_result=alpha_result,
                news_type=self.cfg.news_type,
                word_limit=self.cfg.word_limit,
                tone=self.cfg.tone,
                target_style=self.cfg.target_style
            )
            
            beta_response = self.llm_client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": beta_prompt}],
                stream=False
            )
            
            if hasattr(beta_response, 'message'):
                beta_result = beta_response.message.content
            elif isinstance(beta_response, dict) and 'message' in beta_response:
                beta_result = beta_response['message']['content']
            else:
                beta_result = str(beta_response)
            
            print("Beta階段完成")
            
            # 執行Gamma階段 - 標題策略師
            print("開始Gamma階段...")
            gamma_prompt = self.prompts.get("gamma", "").format(
                alpha_result=alpha_result,
                beta_result=beta_result,
                news_type=self.cfg.news_type,
                word_limit=self.cfg.word_limit,
                tone=self.cfg.tone,
                target_style=self.cfg.target_style
            )
            
            gamma_response = self.llm_client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": gamma_prompt}],
                stream=False
            )
            
            if hasattr(gamma_response, 'message'):
                gamma_result = gamma_response.message.content
            elif isinstance(gamma_response, dict) and 'message' in gamma_response:
                gamma_result = gamma_response['message']['content']
            else:
                gamma_result = str(gamma_response)
            
            print("Gamma階段完成")
            
            # 提取標題（從Gamma結果中提取第一行作為標題）
            lines = gamma_result.strip().split('\n')
            selected_headline = lines[0] if lines else "無標題"
            
            # 執行Delta階段 - 品質守門員
            print("開始Delta階段...")
            delta_prompt = self.prompts.get("delta", "").format(
                gamma_result=gamma_result,
                news_type=self.cfg.news_type,
                word_limit=self.cfg.word_limit,
                tone=self.cfg.tone,
                target_style=self.cfg.target_style
            )
            
            delta_response = self.llm_client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": delta_prompt}],
                stream=False
            )
            
            if hasattr(delta_response, 'message'):
                delta_result = delta_response.message.content
            elif isinstance(delta_response, dict) and 'message' in delta_response:
                delta_result = delta_response['message']['content']
            else:
                delta_result = str(delta_response)
            
            print("Delta階段完成")
            
            # 構建完整的結果
            result = {
                "status": "success",
                "selected_headline": selected_headline,
                "final_content": gamma_result,
                "alpha_analysis": alpha_result,
                "beta_analysis": beta_result,
                "delta_review": delta_result,
                "stages_info": {
                    "alpha": {
                        "title": "Alpha（資訊架構師）",
                        "purpose": "將原始資料轉為結構化初稿（導言/主體/背景 + 資訊架構）",
                        "input_data": f"news_type: {self.cfg.news_type}, word_limit: {self.cfg.word_limit}, tone: {self.cfg.tone}",
                        "expected_output": ["draft_content", "key_points", "info_hierarchy", "completeness_score"],
                        "success_criteria": ["字數≥200", "具關鍵重點", "完整性≥6"]
                    },
                    "beta": {
                        "title": "Beta（風格塑造師）",
                        "purpose": "基於Alpha結果進行深度分析和風格優化",
                        "input_data": "Alpha分析結果",
                        "expected_output": ["deep_analysis", "trend_prediction", "impact_assessment"],
                        "success_criteria": ["分析深度≥7", "預測合理性≥6", "影響評估完整"]
                    },
                    "gamma": {
                        "title": "Gamma（標題策略師）",
                        "purpose": "創建專業新聞報導",
                        "input_data": "Alpha+Beta分析結果",
                        "expected_output": ["headline", "final_article", "quality_score"],
                        "success_criteria": ["標題吸引力≥8", "內容質量≥7", "字數達標"]
                    },
                    "delta": {
                        "title": "Delta（品質守門員）",
                        "purpose": "最終審核和優化",
                        "input_data": "完整報導",
                        "expected_output": ["final_review", "optimization_suggestions", "publish_recommendation"],
                        "success_criteria": ["準確性≥9", "語言流暢度≥8", "發布就緒度≥7"]
                    }
                }
            }
            
            print(f"處理完成，標題: {selected_headline}")
            return result
            
        except Exception as e:
            print(f"ERROR:__main__:處理文章時發生錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "selected_headline": "",
                "final_content": "",
                "alpha_analysis": "",
                "beta_analysis": "",
                "delta_review": ""
            }
    
    def _format_stage_output(self, stage_name: str, stage_info: Dict, result: Dict) -> str:
        """格式化階段輸出信息"""
        output = f"=== {stage_info['title']} ===\n"
        output += f"目的: {stage_info['purpose']}\n"
        output += f"使用資料: {json.dumps(stage_info['input_data'], ensure_ascii=False, indent=2)}\n"
        output += f"預期產出: {json.dumps(stage_info['expected_outputs'], ensure_ascii=False)}\n"
        output += f"成功標準: {json.dumps(stage_info['success_criteria'], ensure_ascii=False)}\n\n"
        
        if stage_name == "alpha":
            output += f"{stage_info['processing_message']}\n"
            output += f"{stage_info['result']}\n"
            if "key_points" in stage_info:
                output += f"{stage_name.capitalize()} 重點: {stage_info['key_points']}"
        else:
            output += f"{stage_info['processing_message']}\n"
            output += f"{stage_info['result']}"
        
        return output
    
    def create_interface(self):
        """創建Gradio界面"""
        
        def process_single_with_progress(content, news_type, target_style, tone, word_limit, special_limit):
            if not content.strip():
                return (
                    "請輸入新聞內容",
                    "",
                    "",
                    "Alpha 階段 AI 處理中，請稍候...",
                    "Beta 階段 AI 處理中，請稍候...",
                    "Gamma 階段 AI 處理中，請稍候...",
                    "Delta 階段 AI 處理中，請稍候..."
                )
            
            try:
                # 更新配置
                self.cfg.news_type = news_type
                self.cfg.target_style = target_style
                self.cfg.tone = tone
                self.cfg.word_limit = word_limit
                
                print(f"開始處理文章，參數: news_type={news_type}, target_style={target_style}, tone={tone}, word_limit={word_limit}")
                
                result = self.process_single_article(content)
                
                if isinstance(result, dict) and "error" in result:
                    error_msg = f"❌ 處理失敗: {result['error']}"
                    return (
                        error_msg,
                        "",
                        "",
                        f"{error_msg}\n\n=== Alpha（資訊架構師） ===\n目的: 將原始資料轉為結構化初稿\n狀態: 處理失敗",
                        f"{error_msg}\n\n=== Beta（風格塑造師） ===\n目的: 優化內容風格和結構\n狀態: 處理失敗",
                        f"{error_msg}\n\n=== Gamma（標題策略師） ===\n目的: 創建吸引人的標題\n狀態: 處理失敗",
                        f"{error_msg}\n\n=== Delta（品質守門員） ===\n目的: 最終審核和優化\n狀態: 處理失敗"
                    )
                
                # 獲取各階段的詳細信息
                stages_info = result.get("stages_info", {})
                
                # 構建每個階段的詳細輸出
                alpha_detail = f"=== Alpha（資訊架構師） ===\n"
                alpha_detail += f"目的: 將原始資料轉為結構化初稿（導言/主體/背景 + 資訊架構）\n"
                alpha_detail += f"使用資料: {{'news_type': '{news_type}', 'word_limit': {word_limit}, 'tone': '{tone}'}}\n"
                alpha_detail += f"預期產出: ['draft_content', 'key_points', 'info_hierarchy', 'completeness_score']\n"
                alpha_detail += f"成功標準: ['字數≥200', '具關鍵重點', '完整性≥6']\n\n"
                alpha_detail += result.get("alpha_analysis", "Alpha分析完成")
                
                beta_detail = f"=== Beta（風格塑造師） ===\n"
                beta_detail += f"目的: 基於Alpha結果進行深度分析和風格優化\n"
                beta_detail += f"使用資料: Alpha分析結果\n"
                beta_detail += f"預期產出: ['deep_analysis', 'trend_prediction', 'impact_assessment']\n"
                beta_detail += f"成功標準: ['分析深度≥7', '預測合理性≥6', '影響評估完整']\n\n"
                beta_detail += result.get("beta_analysis", "Beta分析完成")
                
                gamma_detail = f"=== Gamma（標題策略師） ===\n"
                gamma_detail += f"目的: 創建專業新聞報導\n"
                gamma_detail += f"使用資料: Alpha+Beta分析結果\n"
                gamma_detail += f"預期產出: ['headline', 'final_article', 'quality_score']\n"
                gamma_detail += f"成功標準: ['標題吸引力≥8', '內容質量≥7', '字數達標']\n\n"
                gamma_detail += result.get("final_content", "Gamma處理完成")
                
                delta_detail = f"=== Delta（品質守門員） ===\n"
                delta_detail += f"目的: 最終審核和優化\n"
                delta_detail += f"使用資料: 完整報導\n"
                delta_detail += f"預期產出: ['final_review', 'optimization_suggestions', 'publish_recommendation']\n"
                delta_detail += f"成功標準: ['準確性≥9', '語言流暢度≥8', '發布就緒度≥7']\n\n"
                delta_detail += result.get("delta_review", "Delta審核完成")
                
                return (
                    "✅ 處理完成！",
                    result.get("selected_headline", "無標題"),
                    result.get("final_content", ""),
                    alpha_detail,
                    beta_detail,
                    gamma_detail,
                    delta_detail
                )
                
            except Exception as e:
                error_msg = f"處理文章時發生錯誤: {str(e)}"
                print(f"ERROR:__main__:{error_msg}")
                import traceback
                traceback.print_exc()
                
                return (
                    f"❌ 處理失敗: {error_msg}",
                    "",
                    "",
                    f"=== Alpha（資訊架構師） ===\n目的: 將原始資料轉為結構化初稿\n狀態: 處理錯誤 - {str(e)}",
                    f"=== Beta（風格塑造師） ===\n目的: 優化內容風格和結構\n狀態: 處理錯誤 - {str(e)}",
                    f"=== Gamma（標題策略師） ===\n目的: 創建吸引人的標題\n狀態: 處理錯誤 - {str(e)}",
                    f"=== Delta（品質守門員） ===\n目的: 最終審核和優化\n狀態: 處理錯誤 - {str(e)}"
                )
        
        def process_batch_with_progress(file_obj, news_type, target_style, tone, word_limit, special_limit):
            if not file_obj:
                return "請上傳CSV文件"
            
            try:
                import pandas as pd
                df = pd.read_csv(file_obj.name)
                
                if 'content' not in df.columns:
                    return "CSV文件必須包含'content'列"
                
                # 更新配置
                self.cfg.news_type = news_type
                self.cfg.target_style = target_style
                self.cfg.tone = tone
                self.cfg.word_limit = word_limit
                
                results = []
                for idx, row in df.iterrows():
                    content = row['content']
                    if pd.notna(content) and content.strip():
                        result = self.process_single_article(content)
                        results.append(result)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                batch_filename = f"batch_results_{timestamp}.json"
                
                output_dir = Path("outputs")
                output_dir.mkdir(exist_ok=True)
                
                with open(output_dir / batch_filename, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                return f"✅ 批量處理完成！共處理 {len(results)} 篇文章，結果已保存到: {output_dir / batch_filename}"
                
            except Exception as e:
                return f"❌ 批量處理失敗: {str(e)}"
        
        def load_prompt_content(stage):
            """加載指定階段的提示詞內容"""
            prompts_dir = Path("prompts")
            prompt_file = prompts_dir / f"{stage.lower()}_prompt.txt"
            
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return f"未找到 {stage} 階段的提示詞文件"
        
        def save_prompt_content(stage, content):
            """保存指定階段的提示詞內容"""
            try:
                prompts_dir = Path("prompts")
                prompts_dir.mkdir(exist_ok=True)
                
                prompt_file = prompts_dir / f"{stage.lower()}_prompt.txt"
                with open(prompt_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 重新加載提示詞
                self.load_prompts()
                return f"✅ {stage} 階段提示詞已更新並保存"
            except Exception as e:
                return f"❌ 保存失敗: {str(e)}"
        
        def reset_prompt_to_default(stage):
            """重置為默認提示詞"""
            defaults = {
                "Alpha": """你是新聞分析專家，請分析以下新聞內容並提取關鍵信息：

新聞內容：{content}

請提供：
1. 主要事件摘要
2. 關鍵人物和組織
3. 時間和地點
4. 潛在影響

請用繁體中文回答，保持專業和客觀。""",
                
                "Beta": """基於以下Alpha階段分析結果，請進行深度分析：

Alpha分析：{alpha_result}

請提供：
1. 事件背後的深層原因
2. 可能的發展趨勢
3. 對相關產業的影響
4. 社會和經濟層面的分析

請用繁體中文回答，保持深度和洞察力。""",
                
                "Gamma": """基於Alpha和Beta階段的分析，請創建一篇專業的新聞報導：

Alpha分析：{alpha_result}
Beta分析：{beta_result}

要求：
1. 標題要吸引人且準確
2. 內容要有深度和廣度
3. 結構清晰，包含引言、主體、結論
4. 字數在{word_limit}字左右
5. 使用繁體中文
6. 保持{tone}的語調
7. 符合{target_style}的風格

請直接輸出完整的報導文章。""",
                
                "Delta": """請對以下新聞報導進行最終審核和優化：

報導內容：{gamma_result}

審核標準：
1. 事實準確性
2. 語言流暢度
3. 結構完整性
4. 標題吸引力
5. 整體質量
6. 是否符合{target_style}風格
7. 是否達到{word_limit}字要求

請提供：
- 優化後的最終版本
- 簡要的審核意見
- 是否適合發布的建議

使用繁體中文回答。"""
            }
            
            return defaults.get(stage, f"未找到 {stage} 的默認提示詞")
        
        # 創建界面
        with gr.Blocks(title="新聞智能分析系統", theme=gr.themes.Soft()) as app:
            gr.Markdown("# 📰 新聞智能分析系統")
            gr.Markdown("使用AI技術自動分析、創作和優化新聞內容")
            
            with gr.Tabs():
                # 單篇文章處理
                with gr.TabItem("單篇文章處理"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            # 配置區域
                            gr.Markdown("### ⚙️ 處理配置")
                            
                            news_type_dropdown = gr.Dropdown(
                                choices=["財經", "科技", "產業", "事件", "政策"],
                                value=self.cfg.news_type,
                                label="新聞類型"
                            )
                            
                            target_style_dropdown = gr.Dropdown(
                                choices=["經濟日報", "中央社", "數位時代", "券商研報"],
                                value=self.cfg.target_style,
                                label="目標媒體風格"
                            )
                            
                            tone_dropdown = gr.Dropdown(
                                choices=["客觀中性", "積極正面", "謹慎保守"],
                                value=self.cfg.tone,
                                label="語氣風格"
                            )
                            
                            word_limit_slider = gr.Slider(
                                minimum=200,
                                maximum=2000,
                                value=self.cfg.word_limit,
                                step=50,
                                label="目標字數"
                            )
                            
                            special_limit_text = gr.Textbox(
                                label="特殊限制 (可選填)",
                                placeholder="例如：避免使用專業術語、加入背景說明等...",
                                lines=2
                            )
                            
                            input_text = gr.Textbox(
                                label="新聞內容",
                                placeholder="請輸入需要分析的新聞內容...",
                                lines=10,
                                max_lines=20
                            )
                            process_btn = gr.Button("🚀 開始分析", variant="primary")
                        
                        with gr.Column(scale=3):
                            status_text = gr.Textbox(label="處理狀態", interactive=False)
                            title_output = gr.Textbox(label="文章標題", interactive=False)
                            content_output = gr.Textbox(label="最終報導", lines=15, interactive=False)
                    
                    with gr.Row():
                        with gr.Column():
                            alpha_output = gr.Textbox(
                                label="Alpha 分析階段 - 資訊架構師",
                                lines=12,
                                interactive=False,
                                value="等待分析..."
                            )
                        with gr.Column():
                            beta_output = gr.Textbox(
                                label="Beta 分析階段 - 風格塑造師",
                                lines=12,
                                interactive=False,
                                value="等待分析..."
                            )
                    
                    with gr.Row():
                        with gr.Column():
                            gamma_output = gr.Textbox(
                                label="Gamma 分析階段 - 標題策略師",
                                lines=12,
                                interactive=False,
                                value="等待分析..."
                            )
                        with gr.Column():
                            delta_output = gr.Textbox(
                                label="Delta 分析階段 - 品質守門員",
                                lines=12,
                                interactive=False,
                                value="等待分析..."
                            )
                
                # 批量處理
                with gr.TabItem("批量處理"):
                    gr.Markdown("### 📊 批量處理新聞文章")
                    gr.Markdown("上傳包含新聞內容的CSV文件（需包含'content'列）")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### 批量處理配置")
                            batch_news_type = gr.Dropdown(
                                choices=["財經", "科技", "產業", "事件", "政策"],
                                value=self.cfg.news_type,
                                label="新聞類型"
                            )
                            
                            batch_target_style = gr.Dropdown(
                                choices=["經濟日報", "中央社", "數位時代", "券商研報"],
                                value=self.cfg.target_style,
                                label="目標媒體風格"
                            )
                            
                            batch_tone = gr.Dropdown(
                                choices=["客觀中性", "積極正面", "謹慎保守"],
                                value=self.cfg.tone,
                                label="語氣風格"
                            )
                            
                            batch_word_limit = gr.Slider(
                                minimum=200,
                                maximum=2000,
                                value=self.cfg.word_limit,
                                step=50,
                                label="目標字數"
                            )
                            
                            batch_special_limit = gr.Textbox(
                                label="特殊限制 (可選填)",
                                placeholder="例如：避免使用專業術語、加入背景說明等...",
                                lines=2
                            )
                        
                        with gr.Column():
                            batch_file = gr.File(
                                label="上傳CSV文件",
                                file_types=[".csv"],
                                type="filepath"
                            )
                            batch_btn = gr.Button("🔄 開始批量處理", variant="primary")
                            batch_status = gr.Textbox(label="批量處理狀態", interactive=False)
                
                # 提示詞管理工具
                with gr.TabItem("📝 提示詞管理工具"):
                    gr.Markdown("## 📝 提示詞管理工具")
                    gr.Markdown("在此頁面您可以查看、編輯、創建和管理提示詞配置。")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### 📋 提示詞階段管理")
                            
                            stage_selector = gr.Dropdown(
                                choices=["Alpha", "Beta", "Gamma", "Delta"],
                                value="Alpha",
                                label="選擇提示詞階段"
                            )
                            
                            with gr.Row():
                                refresh_btn = gr.Button("🔄 刷新")
                                reset_btn = gr.Button("↩️ 重置為默認")
                            
                            save_btn = gr.Button("💾 保存修改", variant="primary")
                        
                        with gr.Column(scale=3):
                            gr.Markdown("### ✏️ 提示詞內容編輯器")
                            
                            prompt_editor = gr.Textbox(
                                label="提示詞內容",
                                lines=20,
                                max_lines=25,
                                interactive=True
                            )
                            
                            status_msg = gr.Textbox(
                                label="操作狀態",
                                interactive=False
                            )
                
                # 系統信息
                with gr.TabItem("ℹ️ 系統信息"):
                    gr.Markdown("### ℹ️ 系統信息")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### 系統配置")
                            llm_provider_text = gr.Textbox(
                                value=self.ollama_base_url,
                                label="LLM提供商",
                                interactive=True,
                                placeholder="例如：http://localhost:11434"
                            )
                            port_text = gr.Textbox(
                                value="7860",
                                label="服務端口",
                                interactive=True,
                                placeholder="例如：7860"
                            )
                            model_dropdown = gr.Dropdown(
                                choices=[self.model_name],
                                value=self.model_name,
                                label="使用模型",
                                interactive=True,
                                allow_custom_value=True
                            )
                            refresh_models_btn = gr.Button("🔄 刷新模型列表", size="sm")
                            update_config_btn = gr.Button("🔄 更新配置", variant="primary")
                            config_status_text = gr.Textbox(
                                label="配置狀態",
                                interactive=False,
                                value="配置就緒"
                            )
                        
                        with gr.Column():
                            gr.Markdown("#### 系統狀態")
                            system_status_text = gr.Textbox(
                                value="就緒",
                                label="系統狀態",
                                interactive=False
                            )
            
            # 設置事件處理
            process_btn.click(
                fn=process_single_with_progress,
                inputs=[
                    input_text,
                    news_type_dropdown,
                    target_style_dropdown,
                    tone_dropdown,
                    word_limit_slider,
                    special_limit_text
                ],
                outputs=[
                    status_text,
                    title_output,
                    content_output,
                    alpha_output,
                    beta_output,
                    gamma_output,
                    delta_output
                ]
            )
            
            batch_btn.click(
                fn=process_batch_with_progress,
                inputs=[
                    batch_file,
                    batch_news_type,
                    batch_target_style,
                    batch_tone,
                    batch_word_limit,
                    batch_special_limit
                ],
                outputs=[batch_status]
            )
            
            # 提示詞管理事件
            def load_selected_prompt(stage):
                content = load_prompt_content(stage)
                return content, f"✅ 已加載 {stage} 階段提示詞"
            
            def save_current_prompt(stage, content):
                result = save_prompt_content(stage, content)
                new_content = load_prompt_content(stage)
                return new_content, result
            
            def reset_to_default_prompt(stage):
                default_content = reset_prompt_to_default(stage)
                return default_content, f"✅ {stage} 階段已重置為默認提示詞"
            
            # 提示詞事件綁定
            stage_selector.change(
                fn=load_selected_prompt,
                inputs=[stage_selector],
                outputs=[prompt_editor, status_msg]
            )
            
            refresh_btn.click(
                fn=load_selected_prompt,
                inputs=[stage_selector],
                outputs=[prompt_editor, status_msg]
            )
            
            save_btn.click(
                fn=save_current_prompt,
                inputs=[stage_selector, prompt_editor],
                outputs=[prompt_editor, status_msg]
            )
            
            reset_btn.click(
                fn=reset_to_default_prompt,
                inputs=[stage_selector],
                outputs=[prompt_editor, status_msg]
            )
            
            # 配置更新事件
            def update_system_config(new_base_url, new_model_name):
                """更新系統配置"""
                status = self.update_config(new_base_url, new_model_name)
                # 更新模型下拉選單
                models, _ = self.refresh_models_from_host(new_base_url)
                return status, gr.Dropdown(choices=models, value=new_model_name)
            
            def refresh_models_list(host_url):
                """刷新模型列表"""
                models, status_msg = self.refresh_models_from_host(host_url)
                current_model = self.model_name if models and self.model_name in models else (models[0] if models else self.model_name)
                return gr.Dropdown(choices=models, value=current_model), status_msg
            
            # 配置更新和模型刷新事件
            update_config_btn.click(
                fn=update_system_config,
                inputs=[llm_provider_text, model_dropdown],
                outputs=[config_status_text, model_dropdown]
            )
            
            refresh_models_btn.click(
                fn=refresh_models_list,
                inputs=[llm_provider_text],
                outputs=[model_dropdown, config_status_text]
            )
            
            # 實時更新顯示值
            def refresh_config_display():
                """刷新配置顯示"""
                models = self.get_available_models()
                return self.ollama_base_url, gr.Dropdown(choices=models, value=self.model_name)
            
            # 頁面加載時刷新顯示
            app.load(
                fn=refresh_config_display,
                outputs=[llm_provider_text, model_dropdown]
            )
        
        return app

def main():
    """主函數"""
    try:
        print("🚀 啟動新聞智能分析系統...")
        
        # 創建應用實例
        app_instance = GradioNewsWorkflow()
        
        # 創建界面
        app = app_instance.create_interface()
        
        # 啟動應用
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            debug=True,
            show_error=True
        )
        
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        print("請確保：")
        print("1. Ollama 服務正在運行 (http://localhost:11434)")
        print("2. 已安裝所需的 Python 套件")
        print("3. 端口 7860 未被佔用")

if __name__ == "__main__":
    main()