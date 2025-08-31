import sys
import os
from click.testing import CliRunner

# 确保从正确的路径导入
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pipeline import app, run_pipeline

# 测试直接调用run_pipeline函数
def test_direct_run_pipeline():
    print("\n=== Testing direct run_pipeline call ===")
    os.environ["OLLAMA_MOCK"] = "true"
    try:
        out = run_pipeline(
            raw_data="这是一段用于测试的原始资料。",
            news_type="财经",
            target_style="经济日报",
            word_limit=700,
            tone="客观中性",
        )
        print(f"Success: {out.get('success')}")
        print("Direct call works!")
    except Exception as e:
        print(f"Direct call failed: {e}")

# 尝试使用不同的方式调用Typer应用
def test_different_app_calls():
    print("\n=== Testing different app calling methods ===")
    os.environ["OLLAMA_MOCK"] = "true"
    runner = CliRunner()
    
    # 方法1：直接使用app
    print("\nMethod 1: Direct app call")
    result1 = runner.invoke(
        app, 
        [
            "--raw-data",
            "这是一段用于测试的原始资料。",
            "--news-type",
            "财经",
            "--target-style",
            "经济日报",
            "--no-interactive",
        ],
        prog_name="pipeline"
    )
    print(f"Method 1 exit code: {result1.exit_code}")
    print(f"Method 1 output: {result1.output}")
    
    # 方法2：使用main函数
    print("\nMethod 2: Using app.main")
    try:
        if hasattr(app, 'main'):
            result2 = runner.invoke(
                app.main, 
                [
                    "--raw-data",
                    "这是一段用于测试的原始资料。",
                    "--news-type",
                    "财经",
                    "--target-style",
                    "经济日报",
                    "--no-interactive",
                ],
                prog_name="pipeline"
            )
            print(f"Method 2 exit code: {result2.exit_code}")
            print(f"Method 2 output: {result2.output}")
        else:
            print("app.main does not exist")
    except Exception as e:
        print(f"Method 2 failed: {e}")

    # 方法3：使用命令行字符串
    print("\nMethod 3: Using command string")
    try:
        cmd = [
            "pipeline",
            "--raw-data",
            "这是一段用于测试的原始资料。",
            "--news-type",
            "财经",
            "--target-style",
            "经济日报",
            "--no-interactive",
        ]
        result3 = runner.invoke(
            app, 
            cmd,
            prog_name="pipeline"
        )
        print(f"Method 3 exit code: {result3.exit_code}")
        print(f"Method 3 output: {result3.output}")
    except Exception as e:
        print(f"Method 3 failed: {e}")

if __name__ == "__main__":
    test_direct_run_pipeline()
    test_different_app_calls()
    print("\nTest completed!")