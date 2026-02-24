#!/usr/bin/env python3
"""
中文文档翻译脚本
将 /docs/source/zh 目录下的所有 Markdown 文件翻译成英文，保存到 /docs/source/en 目录
保持原有的文件结构和命名
"""

import os
import sys
from pathlib import Path
from typing import Optional

# 添加项目路径到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def translate_text(text: str, api_key: Optional[str] = None) -> str:
    """
    使用大模型 API 翻译文本
    
    Args:
        text: 要翻译的中文文本
        api_key: API 密钥（可选，如果设置了环境变量）
    
    Returns:
        翻译后的英文文本
    """
    # 优先使用环境变量中的 API 密钥
    api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    
    if not api_key:
        raise ValueError(
            "请提供 API 密钥。可以通过以下方式设置:\n"
            "1. 设置环境变量: export OPENAI_API_KEY='your-key'\n"
            "2. 设置环境变量: export DASHSCOPE_API_KEY='your-key'\n"
            "3. 在脚本中直接传入 api_key 参数"
        )
    
    # 检测 API 类型
    if "sk-" in api_key and len(api_key) > 40:
        # OpenAI API
        return translate_with_openai(text, api_key)
    else:
        # 默认使用 DashScope (阿里云)
        return translate_with_dashscope(text, api_key)


def translate_with_openai(text: str, api_key: str) -> str:
    """使用 OpenAI API 翻译"""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("请安装 openai: pip install openai")
    
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 或其他可用模型
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional technical translator. "
                    "Translate the following Chinese Markdown documentation to English. "
                    "Requirements:\n"
                    "1. Keep all Markdown syntax unchanged (headers, code blocks, links, etc.)\n"
                    "2. Keep all code snippets unchanged\n"
                    "3. Keep all file paths, variable names, and technical terms unchanged\n"
                    "4. Translate naturally and professionally\n"
                    "5. Maintain the original document structure and formatting"
                )
            },
            {
                "role": "user",
                "content": text
            }
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content


def translate_with_dashscope(text: str, api_key: str) -> str:
    """使用 DashScope (阿里云) API 翻译"""
    try:
        import dashscope
    except ImportError:
        raise ImportError("请安装 dashscope: pip install dashscope")
    
    dashscope.api_key = api_key
    
    from dashscope import Generation
    
    response = Generation.call(
        model="qwen-turbo",  # 或其他可用模型如 qwen-plus, qwen-max
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional technical translator. "
                    "Translate the following Chinese Markdown documentation to English. "
                    "Requirements:\n"
                    "1. Keep all Markdown syntax unchanged (headers, code blocks, links, etc.)\n"
                    "2. Keep all code snippets unchanged\n"
                    "3. Keep all file paths, variable names, and technical terms unchanged\n"
                    "4. Translate naturally and professionally\n"
                    "5. Maintain the original document structure and formatting"
                )
            },
            {
                "role": "user",
                "content": text
            }
        ],
        result_format="message"
    )
    
    if response.status_code == 200:
        return response.output.choices[0].message.content
    else:
        raise Exception(f"Translation failed: {response.message}")


def translate_file(src_file: Path, dest_file: Path, api_key: Optional[str] = None) -> None:
    """
    翻译单个文件
    
    Args:
        src_file: 源文件路径
        dest_file: 目标文件路径
        api_key: API 密钥
    """
    print(f"Translating: {src_file}")
    
    # 读取源文件
    with open(src_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 翻译内容
    translated = translate_text(content, api_key)
    
    # 确保目标目录存在
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入翻译后的内容
    with open(dest_file, 'w', encoding='utf-8') as f:
        f.write(translated)
    
    print(f"Saved to: {dest_file}")


def main():
    """主函数"""
    # 设置路径 - 修正为 source/zh 和 source/en
    docs_dir = Path(__file__).parent
    zh_dir = docs_dir / "source" / "zh"
    en_dir = docs_dir / "source" / "en"
    
    # 检查中文文档目录是否存在
    if not zh_dir.exists():
        print(f"Error: Chinese docs directory not found: {zh_dir}")
        sys.exit(1)
    
    # 获取 API 密钥
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    
    if not api_key:
        print("Warning: No API key found in environment variables.")
        print("Please set OPENAI_API_KEY or DASHSCOPE_API_KEY environment variable.")
        print("")
        print("Example:")
        print("  export DASHSCOPE_API_KEY='your-dashscope-api-key'")
        print("  # or")
        print("  export OPENAI_API_KEY='your-openai-api-key'")
        print("")
        response = input("Do you want to enter API key manually? (y/n): ")
        if response.lower() == 'y':
            api_key = input("Enter API key: ").strip()
        else:
            print("Exiting...")
            sys.exit(1)
    
    # 统计文件数量
    md_files = list(zh_dir.rglob("*.md"))
    print(f"Found {len(md_files)} Markdown files to translate")
    print(f"Source: {zh_dir}")
    print(f"Target: {en_dir}")
    print("")
    
    # 翻译每个文件
    for i, src_file in enumerate(md_files, 1):
        # 计算相对路径
        rel_path = src_file.relative_to(zh_dir)
        dest_file = en_dir / rel_path
        
        print(f"[{i}/{len(md_files)}] ", end="")
        
        try:
            translate_file(src_file, dest_file, api_key)
        except Exception as e:
            print(f"Error translating {src_file}: {e}")
            continue
    
    print("")
    print("Translation completed!")
    print(f"English docs saved to: {en_dir}")


if __name__ == "__main__":
    main()
