# Qwen3-TTS Web API 文档

## 概述

Qwen3-TTS Web 提供 RESTful API 用于文字转语音、声音克隆等功能。

## 基础信息

- **基础 URL**: `http://localhost:8766`
- **API 文档**: `http://localhost:8766/docs` (Swagger UI)

## API 端点

### 1. 健康检查

```http
GET /api/health
```

**响应**:
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00"
}
```

### 2. 获取配置

```http
GET /api/config
```

**响应**:
```json
{
  "emotions": [
    {"value": "Normal tone", "label": "正常", "description": "标准语调"},
    {"value": "Sad and crying, speaking slowly", "label": "悲伤哭泣", "description": "悲伤哭泣，语速较慢"},
    ...
  ],
  "speeds": [
    {"value": 0.8, "label": "慢速 (0.8x)"},
    {"value": 1.0, "label": "正常 (1.0x)"},
    {"value": 1.3, "label": "快速 (1.3x)"}
  ],
  "languages": [
    {"value": "English", "label": "英语"},
    {"value": "Chinese", "label": "中文"},
    {"value": "Japanese", "label": "日语"},
    {"value": "Korean", "label": "韩语"}
  ]
}
```

### 3. 获取音色列表

```http
GET /api/speakers
```

**响应**:
```json
{
  "speakers": [
    {
      "name": "Vivian",
      "type": "preset",
      "languages": ["English", "Chinese"],
      "is_multilingual": true
    },
    {
      "name": "MyVoice",
      "type": "cloned",
      "languages": ["Chinese"],
      "is_multilingual": false
    }
  ]
}
```

### 4. 文字转语音

```http
POST /api/tts
Content-Type: application/json

{
  "text": "你好，这是测试文案",
  "speaker": "Vivian",
  "emotion": "Normal tone",
  "speed": 1.0,
  "use_lite": false
}
```

**参数说明**:
- `text` (必填): 要转换的文案
- `speaker` (必填): 音色名称
- `emotion` (可选): 语气，默认 "Normal tone"
- `speed` (可选): 语速，默认 1.0
- `use_lite` (可选): 是否使用 Lite 模型，默认 false

**响应**:
```json
{
  "success": true,
  "audio_path": "outputs/CustomVoice/20240101_120000_你好这是测试.wav",
  "history_id": "uuid-string"
}
```

### 5. 音色设计

```http
POST /api/tts/design
Content-Type: application/x-www-form-urlencoded

text=你好&description=深沉的旁白声音&use_lite=false
```

**参数说明**:
- `text` (必填): 要转换的文案
- `description` (必填): 音色描述
- `use_lite` (可选): 是否使用 Lite 模型

### 6. 克隆声音

```http
POST /api/clone
Content-Type: multipart/form-data

name=我的声音&text=音频中的文案&language=Chinese&audio=<文件>
```

**参数说明**:
- `name` (必填): 音色名称
- `text` (必填): 音频中的文案
- `language` (可选): 语言类型，默认 "English"
- `audio` (必填): 音频文件 (MP3, WAV, M4A 等)

**响应**:
```json
{
  "success": true,
  "name": "我的声音",
  "message": "音色 '我的声音' 克隆成功"
}
```

### 7. 使用克隆音色生成语音

```http
POST /api/tts/clone
Content-Type: application/x-www-form-urlencoded

text=你好&voice_name=我的声音&use_lite=false
```

**参数说明**:
- `text` (必填): 要转换的文案
- `voice_name` (必填): 克隆的音色名称
- `use_lite` (可选): 是否使用 Lite 模型

### 8. 获取生成历史

```http
GET /api/history
```

**响应**:
```json
{
  "history": [
    {
      "id": "uuid-string",
      "text": "你好，这是测试",
      "speaker": "Vivian",
      "emotion": "Normal tone",
      "speed": 1.0,
      "audio_path": "outputs/CustomVoice/20240101_120000_你好这是测试.wav",
      "created_at": "2024-01-01T12:00:00"
    }
  ]
}
```

### 9. 删除历史记录

```http
DELETE /api/history/{history_id}
```

**响应**:
```json
{
  "success": true
}
```

### 10. 删除克隆音色

```http
DELETE /api/voices/{voice_name}
```

**响应**:
```json
{
  "success": true,
  "message": "音色 '音色名' 已删除"
}
```

### 11. 获取音频文件

```http
GET /api/audio/{path}
```

**示例**:
```http
GET /api/audio/outputs/CustomVoice/20240101_120000_你好.wav
```

## 错误处理

所有 API 在出错时返回 HTTP 错误状态码和错误详情：

```json
{
  "detail": "错误描述信息"
}
```

常见错误码：
- `400`: 请求参数错误
- `404`: 资源未找到
- `500`: 服务器内部错误

## 音色列表

### 预设音色

| 音色名称 | 支持语言 |
|---------|---------|
| Ryan | English |
| Aiden | English |
| Ethan | English |
| Chelsie | English |
| Serena | English, Chinese |
| Vivian | English, Chinese |
| Uncle_Fu | Chinese |
| Dylan | Chinese |
| Eric | Chinese |
| Ono_Anna | Japanese |
| Sohee | Korean |

## 启动服务

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动 Web 服务
python web_app.py

# 或使用 uvicorn
uvicorn web_app:app --reload --host 0.0.0.0 --port 8766
```

访问 http://localhost:8766 使用 Web 界面。
