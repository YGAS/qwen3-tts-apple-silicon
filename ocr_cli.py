#!/usr/bin/env python3
"""
OCR CLI 工具 - 图片转 Markdown
使用 DeepSeek-OCR-4bit 模型进行图像文字识别

用法:
    python ocr_cli.py <图片路径> [选项]
    python ocr_cli.py image.png
    python ocr_cli.py image.png --output result.md
    python ocr_cli.py image.png --prompt "Extract all text from this image"
    python ocr_cli.py folder/*.png --batch --output-dir ./results
"""
import os
import sys
import argparse
import re
from pathlib import Path
from typing import Optional, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.ocr import (
    image_to_markdown,
    batch_image_to_markdown,
    cleanup_grounding_tags,
    unload_ocr_model,
    DEFAULT_MODEL_PATH,
)


def save_markdown(content: str, output_path: str, extension: str = ".mmd") -> str:
    """
    保存 markdown 内容到文件
    
    Args:
        content: markdown 内容
        output_path: 输出路径
        extension: 文件扩展名（默认 .mmd 表示 multimodal markdown）
        
    Returns:
        str: 实际保存的文件路径
    """
    # 如果输出路径没有扩展名，添加默认扩展名
    if not Path(output_path).suffix:
        output_path = output_path + extension
    
    # 确保目录存在
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    # 写入文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="OCR 图片转 Markdown 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ocr_cli.py image.png
  python ocr_cli.py image.png -o output.md
  python ocr_cli.py image.png --prompt "Extract table data"
  python ocr_cli.py *.png --batch -d ./results
  python ocr_cli.py scan.pdf --max-tokens 8000
        """
    )
    
    parser.add_argument(
        "input",
        nargs="+",
        help="输入图片路径（支持多个文件）"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="输出文件路径（单文件模式）"
    )
    
    parser.add_argument(
        "-d", "--output-dir",
        type=str,
        default="./ocr_results",
        help="批量模式下的输出目录（默认: ./ocr_results）"
    )
    
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        default="只提取图片中的原始文字内容，不要添加任何描述或标题。",
        help="OCR 提示词"
    )
    
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4000,
        help="最大生成 token 数（默认: 4000）"
    )
    
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="温度参数（默认: 0.0）"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式"
    )
    
    parser.add_argument(
        "--keep-tags",
        action="store_true",
        help="保留 grounding tags（不清理坐标信息）"
    )
    
    parser.add_argument(
        "--model-path",
        type=str,
        default=DEFAULT_MODEL_PATH,
        help=f"模型路径（默认: {DEFAULT_MODEL_PATH}）"
    )
    
    parser.add_argument(
        "--unload",
        action="store_true",
        help="处理完成后卸载模型释放内存"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细信息"
    )
    
    args = parser.parse_args()
    
    # 验证模型路径
    if not os.path.exists(args.model_path):
        print(f"错误: 模型路径不存在: {args.model_path}")
        print(f"请确保模型已下载到正确位置")
        sys.exit(1)
    
    # 收集所有输入文件
    input_files = []
    for pattern in args.input:
        # 支持通配符
        if "*" in pattern:
            input_files.extend(Path(".").glob(pattern))
        else:
            path = Path(pattern)
            if path.exists():
                input_files.append(path)
            else:
                print(f"警告: 文件不存在: {pattern}")
    
    if not input_files:
        print("错误: 没有有效的输入文件")
        sys.exit(1)
    
    # 过滤只保留图片文件
    valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    input_files = [f for f in input_files if f.suffix.lower() in valid_extensions]
    
    if not input_files:
        print(f"错误: 没有有效的图片文件（支持的格式: {', '.join(valid_extensions)}）")
        sys.exit(1)
    
    print(f"找到 {len(input_files)} 个图片文件")
    
    # 批量处理模式
    if args.batch or len(input_files) > 1:
        print(f"\n批量处理模式...")
        print(f"输出目录: {args.output_dir}")
        
        results = batch_image_to_markdown(
            image_paths=input_files,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            cleanup_tags=not args.keep_tags,
            model_path=args.model_path,
        )
        
        # 保存结果
        os.makedirs(args.output_dir, exist_ok=True)
        saved_files = []
        
        for i, (result, input_file) in enumerate(zip(results, input_files)):
            if "error" in result:
                print(f"  ✗ {input_file.name}: {result['error']}")
                continue
            
            # 生成输出文件名
            output_name = f"{input_file.stem}.mmd"
            output_path = os.path.join(args.output_dir, output_name)
            
            # 保存 markdown
            actual_path = save_markdown(result["markdown"], output_path)
            saved_files.append(actual_path)
            
            print(f"  ✓ {input_file.name} -> {output_name}")
            
            if args.verbose:
                print(f"    原始文本长度: {len(result['raw_text'])} 字符")
                print(f"    清理后长度: {len(result['markdown'])} 字符")
        
        print(f"\n完成！已保存 {len(saved_files)} 个文件到 {args.output_dir}")
    
    # 单文件处理模式
    else:
        input_file = input_files[0]
        print(f"\n处理: {input_file}")
        
        result = image_to_markdown(
            image_path=input_file,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            cleanup_tags=not args.keep_tags,
            model_path=args.model_path,
        )
        
        # 确定输出路径
        if args.output:
            output_path = args.output
        else:
            output_path = f"{input_file.stem}.mmd"
        
        # 保存结果
        actual_path = save_markdown(result["markdown"], output_path)
        
        print(f"\n✓ 已保存到: {actual_path}")
        
        if args.verbose:
            print(f"\n原始文本长度: {len(result['raw_text'])} 字符")
            print(f"清理后长度: {len(result['markdown'])} 字符")
            print(f"\n--- Markdown 内容预览 ---")
            preview = result["markdown"][:500] + "..." if len(result["markdown"]) > 500 else result["markdown"]
            print(preview)
    
    # 卸载模型
    if args.unload:
        print("\n卸载模型释放内存...")
        unload_ocr_model()
        print("✓ 模型已卸载")
    
    print("\n完成!")


if __name__ == "__main__":
    main()
