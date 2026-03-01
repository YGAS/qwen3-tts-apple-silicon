#!/usr/bin/env python3
"""
OCR 模块测试脚本
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.ocr import (
    cleanup_grounding_tags,
    DEFAULT_MODEL_PATH,
)


def test_cleanup_grounding_tags():
    """测试清理 grounding tags 功能"""
    print("=" * 60)
    print("测试: cleanup_grounding_tags")
    print("=" * 60)
    
    # 测试数据 - 包含 grounding tags 的文本
    test_cases = [
        {
            "name": "基本标签清理",
            "input": "<|ref|>这是一段文本<|/ref|><|det|>[[100, 200, 300, 400]]<|/det|>",
            "expected": "这是一段文本"
        },
        {
            "name": "多行内容",
            "input": """<|ref|>标题<|/ref|><|det|>[[10, 10, 100, 30]]<|/det|>
<|ref|>段落内容<|/ref|><|det|>[[10, 40, 500, 100]]<|/det|>""",
            "expected": """标题
段落内容"""
        },
        {
            "name": "无标签内容",
            "input": "这是一段普通文本",
            "expected": "这是一段普通文本"
        },
        {
            "name": "混合内容",
            "input": "前缀<|ref|>重要内容<|/ref|><|det|>[[1,2,3,4]]<|/det|>后缀",
            "expected": "前缀重要内容后缀"
        },
    ]
    
    all_passed = True
    for case in test_cases:
        result = cleanup_grounding_tags(case["input"])
        passed = result == case["expected"]
        status = "✓" if passed else "✗"
        print(f"\n{status} {case['name']}")
        if not passed:
            all_passed = False
            print(f"  输入: {repr(case['input'])}")
            print(f"  期望: {repr(case['expected'])}")
            print(f"  实际: {repr(result)}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过!")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)
    return all_passed


def test_model_path():
    """测试模型路径"""
    print("\n" + "=" * 60)
    print("测试: 模型路径检查")
    print("=" * 60)
    
    print(f"模型路径: {DEFAULT_MODEL_PATH}")
    
    if os.path.exists(DEFAULT_MODEL_PATH):
        print(f"✓ 模型目录存在")
        
        # 检查关键文件
        required_files = ["config.json", "model.safetensors"]
        for filename in required_files:
            filepath = os.path.join(DEFAULT_MODEL_PATH, filename)
            if os.path.exists(filepath):
                print(f"  ✓ {filename} 存在")
            else:
                print(f"  ✗ {filename} 缺失")
    else:
        print(f"✗ 模型目录不存在")
        return False
    
    print("=" * 60)
    return True


def test_api_imports():
    """测试 API 模块导入"""
    print("\n" + "=" * 60)
    print("测试: API 模块导入")
    print("=" * 60)
    
    try:
        from api.ocr import (
            image_to_markdown,
            batch_image_to_markdown,
            get_ocr_model,
            unload_ocr_model,
            router,
        )
        print("✓ 成功导入所有 API 函数")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("OCR 模块测试")
    print("=" * 60 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("清理 grounding tags", test_cleanup_grounding_tags()))
    results.append(("模型路径检查", test_model_path()))
    results.append(("API 模块导入", test_api_imports()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    print("=" * 60)
    
    if all_passed:
        print("\n✓ 所有测试通过!")
        return 0
    else:
        print("\n✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
