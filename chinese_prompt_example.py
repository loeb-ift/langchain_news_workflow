#!/usr/bin/env python3
"""
让语言模型输出中文的提示词示例

这个文件提供了几种让语言模型始终输出中文的提示方法和示例。
"""

# 方法1: 在系统提示中明确指定输出语言
SYSTEM_PROMPT_CN = """你是一个专业的中文助手，你的所有回答都必须使用中文。请确保输出内容流畅自然，符合中文表达习惯。"""

# 方法2: 在用户提示末尾添加强制要求
def add_chinese_requirement(prompt):
    """在提示末尾添加必须使用中文输出的要求"""
    return f"{prompt}\n\n请务必使用中文回答。"

# 方法3: 提供中文示例引导模型输出
EXAMPLE_PROMPT = """请总结以下内容的要点：

气候变化是全球面临的重大挑战之一，需要各国共同努力应对。减少碳排放、推广可再生能源、提高能源效率是应对气候变化的关键措施。

（示例格式要求：请用中文分点列出要点）
"""

# 方法4: 使用角色设定引导中文输出
ROLE_PROMPT = """假设你是一位中文教师，请用中文解释这个成语的含义和用法：一举两得
"""

# 方法5: 在多轮对话中保持中文语境
MULTITURN_PROMPT = [
    {"role": "system", "content": "请用中文回答用户的问题。"},
    {"role": "user", "content": "什么是机器学习？"},
    {"role": "assistant", "content": "机器学习是人工智能的一个分支，它允许计算机系统通过数据和经验自动学习和改进，而无需明确编程。"},
    {"role": "user", "content": "它有哪些主要应用领域？"}
]

# 示例用法
if __name__ == "__main__":
    print("=== 让语言模型输出中文的提示方法示例 ===\n")
    
    print("1. 系统提示指定输出语言:")
    print(SYSTEM_PROMPT_CN)
    print("\n" + "="*50 + "\n")
    
    print("2. 在提示末尾添加强制要求:")
    example_prompt = "请解释什么是人工智能"
    print(f"原始提示: {example_prompt}")
    print(f"添加中文要求后: {add_chinese_requirement(example_prompt)}")
    print("\n" + "="*50 + "\n")
    
    print("3. 提供中文示例引导:")
    print(EXAMPLE_PROMPT)
    print("\n" + "="*50 + "\n")
    
    print("4. 使用角色设定引导中文输出:")
    print(ROLE_PROMPT)
    print("\n" + "="*50 + "\n")
    
    print("5. 多轮对话中保持中文语境:")
    for turn in MULTITURN_PROMPT:
        print(f"{turn['role']}: {turn['content']}")