# OCR 模块使用指南

OCR 模块使用 DeepSeek-OCR-4bit 模型将图片转换为 Markdown 格式文本。

## 功能特性

- 图片转 Markdown 文本
- 自动清理 grounding tags（坐标信息）
- 支持批量处理
- 提供 Web API 和 CLI 工具
- 模型懒加载和手动卸载

## 安装依赖

```bash
pip install -U mlx-vlm pillow
```

## CLI 使用方法

### 单文件处理

```bash
# 基本用法
python ocr_cli.py image.png

# 指定输出文件
python ocr_cli.py image.png -o output.md

# 自定义提示词
python ocr_cli.py image.png --prompt "Extract all text from this image"

# 显示详细信息
python ocr_cli.py image.png -v
```

### 批量处理

```bash
# 批量处理多个文件
python ocr_cli.py *.png --batch -d ./results

# 处理完成后卸载模型释放内存
python ocr_cli.py *.png --batch --unload
```

### CLI 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | 输入图片路径（支持多个文件） | 必填 |
| `-o, --output` | 输出文件路径（单文件模式） | 同输入文件名，扩展名改为 `.mmd` |
| `-d, --output-dir` | 批量模式下的输出目录 | `./ocr_results` |
| `-p, --prompt` | OCR 提示词 | `只提取图片中的原始文字内容，不要添加任何描述或标题。` |
| `--max-tokens` | 最大生成 token 数 | `4000` |
| `--temperature` | 温度参数 | `0.0` |
| `--batch` | 批量处理模式 | `False` |
| `--keep-tags` | 保留 grounding tags | `False` |
| `--unload` | 处理完成后卸载模型 | `False` |
| `-v, --verbose` | 显示详细信息 | `False` |

## Web API 使用方法

启动 Web 服务后，可以使用以下 API：

### 检查模型状态

```bash
curl http://localhost:8766/api/ocr/status
```

### 单文件 OCR

```bash
curl -X POST http://localhost:8766/api/ocr \
  -F "file=@image.png" \
  -F "prompt=只提取图片中的原始文字内容，不要添加任何描述或标题。" \
  -F "max_tokens=4000" \
  -F "temperature=0.0" \
  -F "cleanup_tags=true"
```

### 批量 OCR

```bash
curl -X POST http://localhost:8766/api/ocr/batch \
  -F "files=@page1.png" \
  -F "files=@page2.png" \
  -F "prompt=只提取图片中的原始文字内容，不要添加任何描述或标题。"
```

### 卸载模型

```bash
curl -X POST http://localhost:8766/api/ocr/unload
```

## Python API 使用方法

```python
from api.ocr import (
    image_to_markdown,
    batch_image_to_markdown,
    cleanup_grounding_tags,
    unload_ocr_model,
)

# 单文件处理
result = image_to_markdown(
    image_path="image.png",
    prompt="只提取图片中的原始文字内容，不要添加任何描述或标题。",
    max_tokens=4000,
    temperature=0.0,
    cleanup_tags=True,
)

print(result["markdown"])  # 清理后的 Markdown 文本
print(result["raw_text"])  # 原始输出（包含 grounding tags）

# 批量处理
results = batch_image_to_markdown(
    image_paths=["page1.png", "page2.png"],
    prompt="只提取图片中的原始文字内容，不要添加任何描述或标题。",
)

# 卸载模型释放内存
unload_ocr_model()
```

## 关于 Grounding Tags

DeepSeek OCR 模型输出包含 grounding tags，格式为：

```
<|ref|>文本内容<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>
```

其中：
- `<|ref|>...<|/ref|>` 包含识别出的文本
- `<|det|>...<|/det|>` 包含文本在图片中的坐标位置

默认情况下，模块会自动清理这些 tags，只保留纯文本内容。如果需要保留坐标信息，可以设置 `cleanup_tags=False`。

### 手动清理示例

```python
from api.ocr import cleanup_grounding_tags

raw_text = "<|ref|>Hello<|/ref|><|det|>[[10, 20, 50, 30]]<|/det|>"
clean_text = cleanup_grounding_tags(raw_text)
print(clean_text)  # 输出: Hello
```

## 输出文件格式

OCR 结果默认保存为 `.mmd` 文件（multimodal markdown），这是一种约定俗成的扩展名，表示该 Markdown 文件来自 OCR 识别，可能包含一些识别 artifacts。

## 注意事项

1. **模型加载**：模型采用懒加载策略，首次调用时会自动加载
2. **内存管理**：OCR 模型占用较多内存，处理完成后可以调用 `unload_ocr_model()` 释放
3. **支持的图片格式**：PNG, JPG, JPEG, GIF, WEBP, BMP
4. **首次运行**：首次加载模型可能需要一些时间，请耐心等待
