#!/usr/bin/env python3
"""
确保语言模型输出中文的实用工具

这个脚本提供了在LangChain News Workflow项目中确保语言模型始终输出中文的方法和工具函数。
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional

# 项目根目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从app_utils导入prompt_manager
from app_utils.prompt_manager import PromptManager

class ChinesePromptEnhancer:
    """用于增强提示词以确保中文输出的工具类"""
    
    def __init__(self):
        self.prompt_manager = PromptManager()
        
        # 中文输出的强制要求模板
        self.chinese_requirement_template = """
【语言要求】
- 请务必使用中文撰写所有文字内容
- 保持中文表达的流畅性和自然度
- 避免使用任何英文或混合语言表达（专有名词除外）
"""
        
    def add_chinese_requirement(self, prompt_dict: Dict[str, str]) -> Dict[str, str]:
        """
        在提示词字典中添加中文输出要求
        
        Args:
            prompt_dict: 包含system和user键的提示词字典
            
        Returns:
            增强后的提示词字典
        """
        # 在system提示末尾添加中文要求
        if prompt_dict.get('system'):
            prompt_dict['system'] += '\n' + self.chinese_requirement_template
        else:
            prompt_dict['system'] = self.chinese_requirement_template
        
        return prompt_dict
    
    def modify_stage_prompt_for_chinese(self, stage: str) -> Dict[str, Any]:
        """
        修改特定阶段的提示词以确保中文输出
        
        Args:
            stage: 阶段名称（如'alpha', 'beta', 'gamma', 'delta'）
            
        Returns:
            修改后的提示词数据
        """
        # 加载现有提示词
        prompt_data = self.prompt_manager.load_stage(stage)
        
        # 在基础system提示中添加中文要求
        if 'base' in prompt_data and 'system' in prompt_data['base']:
            prompt_data['base']['system'] += '\n' + self.chinese_requirement_template
        else:
            if 'base' not in prompt_data:
                prompt_data['base'] = {}
            prompt_data['base']['system'] = self.chinese_requirement_template
        
        # 在用户提示中也添加中文要求，确保双重保险
        if 'base' in prompt_data and 'user' in prompt_data['base']:
            # 检查是否已经包含语言要求
            if '【語言要求】' not in prompt_data['base']['user'] and '【语言要求】' not in prompt_data['base']['user']:
                prompt_data['base']['user'] += '\n' + self.chinese_requirement_template
        
        return prompt_data
    
    def save_chinese_override(self, stage: str) -> None:
        """
        为特定阶段创建中文输出的覆盖文件
        
        Args:
            stage: 阶段名称
        """
        modified_data = self.modify_stage_prompt_for_chinese(stage)
        # 只保存我们修改的部分作为覆盖
        override_data = {
            'base': {
                'system': modified_data['base'].get('system', '')
            }
        }
        self.prompt_manager.save_override(stage, override_data)
        print(f"已保存{stage}阶段的中文输出覆盖文件")
    
    def check_chinese_requirement(self, stage: str) -> bool:
        """
        检查特定阶段的提示词是否已经包含中文输出要求
        
        Args:
            stage: 阶段名称
            
        Returns:
            是否包含中文要求
        """
        prompt_data = self.prompt_manager.load_stage(stage)
        system_prompt = prompt_data.get('base', {}).get('system', '')
        user_prompt = prompt_data.get('base', {}).get('user', '')
        
        # 检查是否包含中文要求关键词
        keywords = ['中文', '繁體中文', '简体中文', '語言要求']
        for keyword in keywords:
            if keyword in system_prompt or keyword in user_prompt:
                return True
        
        return False
    
    def ensure_all_stages_chinese(self, stages: List[str] = None) -> List[str]:
        """
        确保所有指定阶段的提示词都要求中文输出
        
        Args:
            stages: 要处理的阶段列表，如果为None则处理所有标准阶段
            
        Returns:
            已处理的阶段列表
        """
        if stages is None:
            stages = ['alpha', 'beta', 'gamma', 'delta']
        
        processed_stages = []
        for stage in stages:
            if self.prompt_manager.has_stage(stage):
                if not self.check_chinese_requirement(stage):
                    self.save_chinese_override(stage)
                    processed_stages.append(stage)
                else:
                    print(f"{stage}阶段的提示词已经包含中文输出要求")
            else:
                print(f"警告: 未找到{stage}阶段的提示词文件")
        
        return processed_stages
    
    def create_chinese_test_prompt(self, content: str) -> Dict[str, str]:
        """
        创建测试用的中文提示词
        
        Args:
            content: 要处理的内容
            
        Returns:
            包含system和user的提示词字典
        """
        return {
            'system': f"你是一位专业的中文内容处理助手。{self.chinese_requirement_template}",
            'user': f"请处理以下内容:\n{content}\n\n请用中文输出处理结果。"
        }

# 实用函数
def test_chinese_output():
    """
    测试中文输出功能
    """
    enhancer = ChinesePromptEnhancer()
    
    # 创建测试提示
    test_content = "气候变化是全球面临的重大挑战之一，需要各国共同努力应对。"
    test_prompt = enhancer.create_chinese_test_prompt(test_content)
    
    print("=== 测试中文输出提示词 ===")
    print("系统提示:")
    print(test_prompt['system'])
    print("\n用户提示:")
    print(test_prompt['user'])
    print("\n" + "="*50 + "\n")
    
    print("使用方法提示:")
    print("1. 在实际应用中，您可以将这些提示词传递给语言模型")
    print("2. 对于项目中的Pipeline，建议使用ensure_all_stages_chinese()函数")
    print("3. 您也可以针对特定阶段使用save_chinese_override(stage_name)函数")

if __name__ == "__main__":
    # 命令行使用示例
    print("=== LangChain News Workflow 中文输出增强工具 ===\n")
    
    # 创建增强器实例
    enhancer = ChinesePromptEnhancer()
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'check':
            # 检查特定阶段的中文要求
            stage = sys.argv[2] if len(sys.argv) > 2 else 'alpha'
            has_chinese = enhancer.check_chinese_requirement(stage)
            print(f"{stage}阶段{'已包含' if has_chinese else '未包含'}中文输出要求")
            
        elif command == 'add':
            # 为特定阶段添加中文要求
            stage = sys.argv[2] if len(sys.argv) > 2 else 'alpha'
            enhancer.save_chinese_override(stage)
            
        elif command == 'all':
            # 为所有阶段添加中文要求
            stages = enhancer.ensure_all_stages_chinese()
            if stages:
                print(f"已为以下阶段添加中文输出要求: {', '.join(stages)}")
            else:
                print("所有阶段都已经包含中文输出要求")
            
        elif command == 'test':
            # 测试中文输出
            test_chinese_output()
            
        else:
            print("用法:")
            print("  python ensure_chinese_output.py check [stage]   # 检查特定阶段是否包含中文要求")
            print("  python ensure_chinese_output.py add [stage]     # 为特定阶段添加中文要求")
            print("  python ensure_chinese_output.py all            # 为所有阶段添加中文要求")
            print("  python ensure_chinese_output.py test           # 测试中文输出功能")
    else:
        # 显示帮助信息
        print("用法:")
        print("  python ensure_chinese_output.py check [stage]   # 检查特定阶段是否包含中文要求")
        print("  python ensure_chinese_output.py add [stage]     # 为特定阶段添加中文要求")
        print("  python ensure_chinese_output.py all            # 为所有阶段添加中文要求")
        print("  python ensure_chinese_output.py test           # 测试中文输出功能")