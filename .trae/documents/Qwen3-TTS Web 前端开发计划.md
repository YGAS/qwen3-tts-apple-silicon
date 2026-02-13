## 项目目标
为 Qwen3-TTS 项目开发一个直观的 Web 前端界面，让用户无需关心模型配置，轻松使用各种 TTS 功能。

## 技术栈选择
- **后端框架**: FastAPI (Python) - 提供 RESTful API
- **前端**: HTML + Vanilla JavaScript + Tailwind CSS
- **UI 组件**: 原生 HTML5 + 自定义 CSS
- **音频播放**: HTML5 Audio API

## 文件结构
```
qwen3-tts-apple-silicon/
├── main.py                    # 现有 CLI 程序（保留）
├── web_app.py                 # FastAPI 后端服务
├── requirements.txt           # 添加 fastapi, uvicorn
├── static/
│   ├── css/
│   │   └── style.css          # 自定义样式
│   └── js/
│       └── app.js             # 前端逻辑
├── templates/
│   └── index.html             # 主页面
└── docs/
    └── api.md                 # API 文档
```

## 页面结构设计

### 1. 侧边栏导航
- 文字转语音 (TTS)
- 音色库
- 克隆声音
- 生成历史

### 2. 文字转语音页面
- **文案输入区**: 文本框 + 文件上传按钮
- **音色选择**: 下拉选择器（显示名称+语言标签）
- **试听按钮**: 试听选中的音色
- **语气选择**: 下拉选择器（Normal/Sad/Excited/Angry/Whisper）
- **语速选择**: 滑块（0.5x - 2.0x）
- **生成按钮**: 提交生成请求
- **结果区**: 音频播放器 + 下载按钮

### 3. 音色库页面
- **预设音色区**:
  - 按语言分组展示（English/Chinese/Japanese/Korean）
  - 每个音色卡片：名称、语言标签、试听按钮
- **克隆音色区**:
  - 列表展示克隆的音色
  - 每个音色：名称、语言标签、试听按钮、删除按钮

### 4. 克隆声音页面
- **音频上传**: 支持拖拽上传，自动转换为 WAV
- **文案输入**: 输入音频对应的文案（重要）
- **音色名称**: 输入新音色名称
- **语言选择**: 选择音色主要语言
- **克隆按钮**: 提交克隆请求
- **状态显示**: 显示克隆进度和结果

### 5. 生成历史页面
- **历史列表**: 按时间倒序排列
- **每条记录**:
  - 文案预览（前50字）
  - 生成时间
  - 使用的音色
  - 播放按钮
  - 下载按钮
  - 删除按钮

## API 接口设计

### 基础接口
```
GET  /api/health              # 健康检查
GET  /api/speakers            # 获取所有音色列表
POST /api/tts                 # 文字转语音
POST /api/clone               # 克隆声音
GET  /api/history             # 获取生成历史
DELETE /api/history/{id}      # 删除历史记录
DELETE /api/voices/{name}     # 删除克隆音色
```

### 音色数据结构
```json
{
  "name": "Vivian",
  "type": "preset",
  "languages": ["English", "Chinese"],
  "category": "female"
}
```

### 生成历史数据结构
```json
{
  "id": "uuid",
  "text": "文案内容",
  "speaker": "Vivian",
  "emotion": "Normal",
  "speed": 1.0,
  "audio_path": "outputs/...",
  "created_at": "2024-01-01T00:00:00"
}
```

## 实现步骤

### Phase 1: 后端 API 开发
1. 创建 `web_app.py` FastAPI 应用
2. 实现音色管理 API
3. 实现 TTS 生成 API
4. 实现克隆声音 API
5. 实现历史记录 API
6. 添加静态文件服务

### Phase 2: 前端页面开发
1. 创建 `templates/index.html` 主页面框架
2. 实现侧边栏导航
3. 实现文字转语音页面
4. 实现音色库页面
5. 实现克隆声音页面
6. 实现生成历史页面

### Phase 3: 样式和交互
1. 添加 Tailwind CSS 样式
2. 实现音频播放控制
3. 添加文件拖拽上传
4. 实现加载状态和错误提示
5. 添加响应式布局

## 关键设计决策

### 1. 模型选择策略
- 后端自动根据功能选择合适的模型（Pro 1.7B 或 Lite 0.6B）
- 用户无需关心模型配置

### 2. 音色语言处理
- 显示音色的主要语言标签
- 允许用户选择目标语言进行生成
- 跨语言音色显示多语言标签

### 3. 历史记录存储
- 使用 JSON 文件存储历史记录
- 记录包含文案、音色、音频路径、时间戳
- 支持播放、下载、删除操作

### 4. 音频处理
- 后端统一处理音频格式转换（ffmpeg）
- 前端使用 HTML5 Audio 播放
- 支持 WAV 格式下载

## 启动命令
```bash
# 启动 Web 服务
python web_app.py

# 或
uvicorn web_app:app --reload --host 0.0.0.0 --port 8000
```

## 访问地址
- Web 界面: http://localhost:8000
- API 文档: http://localhost:8000/docs