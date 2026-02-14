# mlx-audio STT 模型配置指南

## mlx-audio 支持的 STT 模型类型

mlx-audio 的 STT（语音转文字）模块支持以下模型类型：

1. **whisper** - OpenAI Whisper 模型（推荐）
   - 多语言支持优秀
   - 准确度高
   - 支持多种模型大小（tiny, base, small, medium, large）

2. **parakeet** - NVIDIA Parakeet 模型
   - 高性能语音识别

3. **voxtral** - Voxtral 模型
   - 多语言支持

4. **glmasr** - GLM ASR 模型
   - 中文支持较好

5. **vibevoice_asr** - VibeVoice ASR 模型

6. **wav2vec** - Facebook Wav2Vec2 模型
   - 预训练模型，需要微调

## 模型配置方式

### 方式一：从网络加载（推荐，首次自动下载）

在 `web_app.py` 的 `ASR_MODELS` 配置中：

```python
ASR_MODELS = {
    "whisper_base": {
        "model_id": "openai/whisper-base",  # HuggingFace 模型 ID
        "folder": "whisper-base",  # 可选：本地文件夹名称
        "type": "whisper",
        "default": True
    }
}
```

**优点**：
- 配置简单，只需提供 HuggingFace 模型 ID
- 首次加载会自动下载并缓存到 `~/.cache/huggingface/hub/`
- 后续加载会使用本地缓存，无需重新下载

### 方式二：从本地加载

1. **下载模型到本地**

   将模型文件下载到 `models/` 目录下，目录结构参考 TTS 模型：
   ```
   models/
   └── whisper-base/
       ├── config.json
       ├── model.safetensors
       └── tokenizer.json
   ```

   或者使用 `snapshots` 子目录结构：
   ```
   models/
   └── whisper-base/
       └── snapshots/
           └── <hash>/
               ├── config.json
               ├── model.safetensors
               └── tokenizer.json
   ```

2. **配置模型**

   ```python
   ASR_MODELS = {
       "whisper_base": {
           "model_id": "openai/whisper-base",  # 可选：作为备用
           "folder": "whisper-base",  # 本地文件夹名称
           "type": "whisper",
           "default": True
       }
   }
   ```

3. **加载逻辑**

   `load_asr_model_cached` 函数会：
   - 优先尝试从本地 `models/` 目录加载
   - 如果本地加载失败，自动尝试从网络加载（如果配置了 `model_id`）

## 推荐的模型配置

### Whisper 系列（推荐）

```python
# 小型模型（速度快，资源占用少）
"whisper_tiny": {
    "model_id": "openai/whisper-tiny",
    "folder": "whisper-tiny",
    "type": "whisper",
    "default": False
}

# 基础模型（平衡速度和准确度，推荐）
"whisper_base": {
    "model_id": "openai/whisper-base",
    "folder": "whisper-base",
    "type": "whisper",
    "default": True
}

# 中型模型（准确度高，但速度较慢）
"whisper_medium": {
    "model_id": "openai/whisper-medium",
    "folder": "whisper-medium",
    "type": "whisper",
    "default": False
}
```

### 其他模型示例

```python
# Parakeet
"parakeet": {
    "model_id": "mlx-community/parakeet-tdt-1.1b",
    "folder": "parakeet-tdt-1.1b",
    "type": "parakeet",
    "default": False
}

# Wav2Vec2
"wav2vec2": {
    "model_id": "facebook/wav2vec2-base-960h",
    "folder": "wav2vec2-base-960h",
    "type": "wav2vec",
    "default": False
}
```

## 下载模型

### 方法一：使用 huggingface-cli

```bash
# 安装 huggingface-cli
pip install huggingface_hub

# 下载模型
huggingface-cli download openai/whisper-base --local-dir models/whisper-base
```

### 方法二：使用 Python 脚本

```python
from huggingface_hub import snapshot_download

# 下载模型
model_path = snapshot_download(
    repo_id="openai/whisper-base",
    local_dir="models/whisper-base"
)
```

### 方法三：手动下载

1. 访问 HuggingFace 模型页面（如 https://huggingface.co/openai/whisper-base）
2. 下载所有文件到 `models/whisper-base/` 目录

## 注意事项

1. **模型类型必须匹配**：`type` 字段必须与 mlx-audio 支持的模型类型一致
2. **首次加载较慢**：从网络加载模型时，首次需要下载，可能需要几分钟
3. **本地缓存**：网络下载的模型会自动缓存到 `~/.cache/huggingface/hub/`，后续加载会更快
4. **内存占用**：不同大小的模型占用内存不同，请根据设备配置选择合适的模型

## 常见问题

**Q: 如何知道模型是否支持？**
A: 检查 `models/` 目录下是否有对应的模型实现，或查看 mlx-audio 文档。

**Q: 本地加载失败怎么办？**
A: 如果配置了 `model_id`，系统会自动尝试从网络加载。

**Q: 如何切换模型？**
A: 修改 `ASR_MODELS` 中的 `default: True` 设置，或在前端选择不同的模型。

