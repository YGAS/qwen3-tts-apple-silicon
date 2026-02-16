# 切换 ASR 模型指南

本文档说明如何将 ASR（语音识别）模型从 `Qwen3-ASR-0.6B-8bit` 切换到 `Qwen3-ASR-1.7B-8bit`。

## 模型信息

| 模型 | 参数量 | 路径 |
|------|--------|------|
| Qwen3-ASR-0.6B-8bit | 0.6B | `/Users/ycl/Documents/qwen3-tts-apple-silicon/models/Qwen3-ASR-0.6B-8bit` |
| Qwen3-ASR-1.7B-8bit | 1.7B | `/Users/ycl/Documents/qwen3-tts-apple-silicon/models/Qwen3-ASR-1.7B-8bit` |

## 切换方法

### 方法一：修改配置文件（推荐）

编辑 [`config.py`](../config.py) 文件中的 `ASR_MODELS` 配置：

```python
# 修改前（当前配置）
ASR_MODELS = {
    "qwen3_asr_0.6b": {
        "folder": "Qwen3-ASR-0.6B-8bit",
        "type": "qwen3_asr",
        "default": True
    },
}

# 修改后（切换到 1.7B 模型）
ASR_MODELS = {
    "qwen3_asr_1.7b": {
        "folder": "Qwen3-ASR-1.7B-8bit",
        "type": "qwen3_asr",
        "default": True
    },
}
```

### 方法二：同时保留两个模型配置

如果需要在两个模型之间灵活切换，可以同时保留两个配置：

```python
ASR_MODELS = {
    "qwen3_asr_0.6b": {
        "folder": "Qwen3-ASR-0.6B-8bit",
        "type": "qwen3_asr",
        "default": False
    },
    "qwen3_asr_1.7b": {
        "folder": "Qwen3-ASR-1.7B-8bit",
        "type": "qwen3_asr",
        "default": True  # 设置为默认模型
    },
}
```

然后通过 API 请求参数 `model_key` 指定要使用的模型：

```bash
curl -X POST "http://localhost:8000/stt" \
  -F "audio=@your_audio.wav" \
  -F "model_key=qwen3_asr_1.7b" \
  -F "language=Chinese"
```

### 方法三：通过 API 动态指定

无需修改配置文件，直接在 API 调用时通过 `model_key` 参数指定：

```bash
# 使用 0.6B 模型
curl -X POST "http://localhost:8000/stt" \
  -F "audio=@your_audio.wav" \
  -F "model_key=qwen3_asr_0.6b" \
  -F "language=Chinese"

# 使用 1.7B 模型（需要先添加配置）
curl -X POST "http://localhost:8000/stt" \
  -F "audio=@your_audio.wav" \
  -F "model_key=qwen3_asr_1.7b" \
  -F "language=Chinese"
```

## 模型加载机制

模型加载逻辑位于 [`models.py`](../models.py) 中的 `load_asr_model_cached` 函数：

1. 如果 `model_key` 为 `None`，则使用 `default: True` 的模型
2. 模型会被缓存，重复调用时直接返回已加载的模型
3. 首次加载时会从本地路径加载模型文件

## 注意事项

1. **内存占用**：1.7B 模型比 0.6B 模型占用更多内存，请确保系统有足够资源
2. **模型缓存**：切换模型后，已加载的旧模型仍会保留在内存中，直到重启服务
3. **模型路径**：确保模型文件夹名称与 `config.py` 中配置的 `folder` 值一致
4. **模型文件完整性**：确认 `Qwen3-ASR-1.7B-8bit` 目录包含完整的模型文件：
   - `config.json`
   - `model.safetensors`
   - `model.safetensors.index.json`
   - `tokenizer_config.json`
   - `vocab.json`
   - `merges.txt`
   - `preprocessor_config.json`
   - `generation_config.json`

## 快速切换步骤

1. 打开 `config.py` 文件
2. 找到 `ASR_MODELS` 配置（第 36-42 行）
3. 修改 `folder` 值为 `"Qwen3-ASR-1.7B-8bit"`
4. 可选：修改 `model_key` 名称为 `"qwen3_asr_1.7b"`
5. 保存文件
6. 重启服务使配置生效

## 验证切换是否成功

重启服务后，调用 STT API 并观察控制台输出：

```
[ASR模型加载] 从本地加载模型: qwen3_asr_1.7b (/Users/ycl/Documents/qwen3-tts-apple-silicon/models/Qwen3-ASR-1.7B-8bit)
[ASR模型加载] 本地模型加载完成: qwen3_asr_1.7b
```

看到以上输出说明模型已成功切换到 1.7B 版本。
