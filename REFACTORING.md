# 代码重构说明

## 重构目标

将 `web_app.py`（原2120行）重构为模块化结构，每个文件不超过300行，增强代码可读性。

## 文件结构

### 核心文件

- **`app.py`** (90行) - 主应用入口，FastAPI 应用初始化和路由注册
- **`web_app.py`** (24行) - 向后兼容入口，重定向到 `app.py`
- **`config.py`** (75行) - 配置和常量定义
- **`models.py`** (121行) - 模型加载和缓存管理
- **`utils.py`** (172行) - 工具函数（文件操作、音频转换等）
- **`history.py`** (85行) - 历史记录管理
- **`templates.py`** (287行) - HTML 模板生成
- **`routes.py`** (59行) - 页面路由注册

### API 路由 (`api/` 目录)

- **`api/common.py`** (39行) - 通用 API（健康检查、配置、音色列表等）
- **`api/tts.py`** (171行) - TTS API（文字转语音、预览、音色设计）
- **`api/stt.py`** (191行) - STT API（语音转文字）
- **`api/clone.py`** (184行) - 克隆音色 API
- **`api/history.py`** (50行) - 历史记录 API
- **`api/files.py`** (60行) - 文件服务 API（音频、文件下载）

## 文件行数统计

所有文件均不超过300行：

```
✓ config.py:       75 lines
✓ models.py:      121 lines
✓ utils.py:      172 lines
✓ history.py:       85 lines
✓ templates.py:      287 lines
✓ routes.py:       59 lines
✓ app.py:       90 lines
✓ web_app.py:       24 lines
✓ api/__init__.py:        4 lines
✓ api/clone.py:      184 lines
✓ api/common.py:       39 lines
✓ api/files.py:       60 lines
✓ api/history.py:       50 lines
✓ api/stt.py:      191 lines
✓ api/tts.py:      171 lines
```

## 主要改进

1. **模块化设计**：按功能拆分，职责清晰
2. **代码可读性**：每个文件专注于单一职责
3. **易于维护**：修改某个功能只需关注对应文件
4. **向后兼容**：`web_app.py` 仍可作为入口使用

## 使用方式

### 方式一：使用新的入口（推荐）

```bash
python app.py
```

### 方式二：使用向后兼容入口

```bash
python web_app.py
```

### 方式三：使用 uvicorn

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8766
# 或
uvicorn web_app:app --reload --host 0.0.0.0 --port 8766
```

## 配置位置变更

- **模型配置**：`config.py` 中的 `MODELS` 和 `ASR_MODELS`
- **路径配置**：`config.py` 中的路径常量
- **选项配置**：`config.py` 中的 `EMOTION_OPTIONS`、`SPEED_OPTIONS` 等

## 注意事项

1. 所有功能保持不变，只是代码组织方式改变
2. `web_app.py` 保持向后兼容，可以继续使用
3. 建议使用 `app.py` 作为新的入口点
4. 文档已更新，引用从 `web_app.py` 改为 `config.py` 或 `app.py`

