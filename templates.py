"""
HTML 模板生成
"""


def get_html_template():
    """获取 HTML 基础模板"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Qwen3-TTS Web</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎙️</text></svg>">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="container">
        <aside class="sidebar">
            <div class="sidebar-header">
                <h1>
                    <i class="fas fa-wave-square" style="color: #3b82f6;"></i>
                    Qwen3-TTS
                </h1>
                <p>本地语音合成</p>
            </div>
            
            <nav class="nav-menu">
                <a href="/tts" class="nav-item {{ 'active' if page == 'tts' else '' }}">
                    <i class="fas fa-microphone-lines"></i>
                    <span>文字转语音</span>
                </a>
                <a href="/stt" class="nav-item {{ 'active' if page == 'stt' else '' }}">
                    <i class="fas fa-language"></i>
                    <span>语音转文字</span>
                </a>
                <a href="/speakers" class="nav-item {{ 'active' if page == 'speakers' else '' }}">
                    <i class="fas fa-users"></i>
                    <span>音色库</span>
                </a>
                <a href="/clone" class="nav-item {{ 'active' if page == 'clone' else '' }}">
                    <i class="fas fa-copy"></i>
                    <span>克隆声音</span>
                </a>
                <a href="/history" class="nav-item {{ 'active' if page == 'history' else '' }}">
                    <i class="fas fa-clock-rotate-left"></i>
                    <span>生成历史</span>
                </a>
            </nav>
            
            <div class="sidebar-footer">
                <p><span class="status-dot"></span>模型就绪</p>
                <p style="margin-top: 4px;">Apple Silicon 优化</p>
            </div>
        </aside>

        <main class="main-content">
            {{ content | safe }}
        </main>
    </div>
    
    <script src="/static/js/app.js?v=14"></script>
</body>
</html>'''


def get_tts_page():
    """TTS 页面内容"""
    return '''<h1 class="page-title">文字转语音</h1>

<div style="max-width: 800px;">
    <div class="card">
        <label class="form-label">输入文案</label>
        <textarea id="tts-text" class="form-textarea" placeholder="请输入要转换为语音的文案..."></textarea>
        <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 13px; color: #9ca3af;">
            <span>支持中文、英文、日文、韩文</span>
            <span id="text-count">0 字</span>
        </div>
    </div>

    <div class="card">
        <label class="form-label">选择音色</label>
        <div class="speaker-sections-container" id="speaker-grid"></div>
    </div>

    <div class="card">
        <div class="grid-2">
            <div>
                <label class="form-label">语气</label>
                <select id="tts-emotion" class="form-select">
                    <option value="Normal tone">正常 - 标准语调</option>
                    <option value="Sad and crying, speaking slowly">悲伤哭泣 - 语速较慢</option>
                    <option value="Excited and happy, speaking very fast">兴奋开心 - 语速很快</option>
                    <option value="Angry and shouting">愤怒大喊</option>
                    <option value="Whispering quietly">轻声耳语</option>
                </select>
            </div>
            <div>
                <label class="form-label">语速</label>
                <select id="tts-speed" class="form-select">
                    <option value="0.8">慢速 (0.8x)</option>
                    <option value="1.0" selected>正常 (1.0x)</option>
                    <option value="1.3">快速 (1.3x)</option>
                </select>
            </div>
        </div>
        <label style="display: flex; align-items: center; gap: 8px; margin-top: 16px; cursor: pointer;">
            <input type="checkbox" id="tts-lite" style="width: 16px; height: 16px;" checked>
            <span style="font-size: 14px; color: #d1d5db;">使用 Lite 模型（更快，质量稍低）</span>
        </label>
    </div>

    <div style="display: flex; gap: 12px; margin-bottom: 20px;">
        <button class="btn btn-primary" id="btn-generate" onclick="generateTTS()">
            <i class="fas fa-play"></i>
            <span>生成语音</span>
        </button>
        <button class="btn btn-secondary" id="btn-preview" onclick="previewSpeaker()">
            <i class="fas fa-headphones"></i>
            <span>试听音色</span>
        </button>
    </div>

    <div id="tts-result" class="card hidden">
        <label class="form-label">生成结果</label>
        <audio id="tts-audio" controls></audio>
        <div style="margin-top: 12px;">
            <a id="tts-download" href="#" download class="btn btn-secondary" style="text-decoration: none;">
                <i class="fas fa-download"></i>
                <span>下载</span>
            </a>
        </div>
    </div>
</div>'''


def get_speakers_page():
    """音色库页面内容"""
    return '''<h1 class="page-title">音色库</h1>

<div class="card">
    <h2 style="font-size: 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-star" style="color: #eab308;"></i>
        预设音色
    </h2>
    <div class="speaker-grid" id="preset-speakers"></div>
</div>

<div class="card">
    <h2 style="font-size: 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-copy" style="color: #22c55e;"></i>
        克隆音色
    </h2>
    <div class="speaker-grid" id="cloned-speakers"></div>
    <p id="no-cloned" class="hidden" style="text-align: center; color: #9ca3af; padding: 40px;">
        暂无克隆音色，请先克隆声音
    </p>
</div>'''


def get_clone_page():
    """克隆声音页面内容"""
    return '''<h1 class="page-title">克隆声音</h1>

<div style="max-width: 600px;">
    <div class="card">
        <label class="form-label">上传参考音频</label>
        <div class="drop-zone" id="drop-zone">
            <i class="fas fa-cloud-upload-alt" style="font-size: 48px; color: #6b7280; margin-bottom: 16px;"></i>
            <p style="color: #d1d5db; margin-bottom: 8px;">拖拽音频文件到此处，或点击上传</p>
            <p style="font-size: 13px; color: #6b7280;">支持 MP3, WAV, M4A 等格式</p>
            <input type="file" id="clone-audio" accept="audio/*" style="display: none;">
        </div>
        <p id="file-name" class="hidden" style="margin-top: 12px; color: #22c55e; font-size: 14px;"></p>
    </div>

    <div class="card">
        <label class="form-label">音色名称</label>
        <input type="text" id="clone-name" class="form-input" placeholder="例如：我的声音、老板的声音">
    </div>

    <div class="card">
        <label class="form-label">参考文案</label>
        <p style="font-size: 13px; color: #9ca3af; margin-bottom: 12px;">输入音频中说的准确内容（对克隆质量很重要）</p>
        <textarea id="clone-text" class="form-textarea" rows="3" placeholder="请输入音频中的文案..."></textarea>
    </div>

    <div class="card">
        <label class="form-label">语言类型</label>
        <select id="clone-language" class="form-select">
            <option value="English">英语</option>
            <option value="Chinese">中文</option>
            <option value="Japanese">日语</option>
            <option value="Korean">韩语</option>
        </select>
    </div>

    <button class="btn btn-primary" id="btn-clone" onclick="cloneVoice()" style="width: 100%; justify-content: center;">
        <i class="fas fa-copy"></i>
        <span>开始克隆</span>
    </button>

    <div id="clone-result" class="success-message hidden" style="margin-top: 20px;">
        <i class="fas fa-check-circle"></i>
        <span id="clone-message"></span>
    </div>
</div>'''


def get_stt_page():
    """STT 页面内容"""
    return '''<h1 class="page-title">语音转文字</h1>

<div style="max-width: 800px;">
    <div class="card">
        <label class="form-label">上传音频文件</label>
        <div class="drop-zone" id="stt-drop-zone">
            <i class="fas fa-cloud-upload-alt" style="font-size: 48px; color: #6b7280; margin-bottom: 16px;"></i>
            <p style="color: #d1d5db; margin-bottom: 8px;">拖拽音频文件到此处，或点击上传</p>
            <p style="font-size: 13px; color: #6b7280;">支持 MP3, WAV, M4A, FLAC 等格式</p>
            <input type="file" id="stt-audio" accept="audio/*" style="display: none;">
        </div>
        <p id="stt-file-name" class="hidden" style="margin-top: 12px; color: #22c55e; font-size: 14px;"></p>
    </div>

    <div style="display: flex; gap: 12px; margin-bottom: 20px;">
        <button class="btn btn-primary" id="btn-stt-generate" onclick="generateSTT()">
            <i class="fas fa-microphone-lines"></i>
            <span>开始识别</span>
        </button>
        <button class="btn btn-secondary" id="btn-stt-retry" onclick="retrySTT()" style="display: none;">
            <i class="fas fa-redo"></i>
            <span>重试</span>
        </button>
    </div>

    <div id="stt-result" class="card hidden">
        <label class="form-label">识别结果</label>
        
        <div style="background-color: #374151; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 13px; color: #9ca3af;">识别文本</span>
                <span id="stt-language" style="font-size: 12px; color: #22c55e;"></span>
            </div>
            <div id="stt-text" style="color: #d1d5db; line-height: 1.6; white-space: pre-wrap; max-height: 300px; overflow-y: auto;"></div>
        </div>

        <div id="stt-segments" style="margin-bottom: 16px;"></div>

        <div style="display: flex; gap: 12px;">
            <a id="stt-download-txt" href="#" download class="btn btn-secondary" style="text-decoration: none;">
                <i class="fas fa-file-alt"></i>
                <span>下载 TXT</span>
            </a>
            <a id="stt-download-srt" href="#" download class="btn btn-secondary" style="text-decoration: none;">
                <i class="fas fa-file-video"></i>
                <span>下载 SRT</span>
            </a>
            <button class="btn btn-primary" id="btn-stt-to-clone" onclick="sendToClone()" style="display: none;">
                <i class="fas fa-copy"></i>
                <span>用于克隆音色</span>
            </button>
        </div>
    </div>

    <div id="stt-error" class="card hidden" style="background-color: rgba(220, 38, 38, 0.1); border: 1px solid #dc2626;">
        <div style="color: #dc2626;">
            <i class="fas fa-exclamation-circle"></i>
            <span id="stt-error-message"></span>
        </div>
    </div>
</div>'''


def get_history_page():
    """历史记录页面内容"""
    return '''<h1 class="page-title">生成历史</h1>

<div id="history-list"></div>

<p id="no-history" class="hidden" style="text-align: center; color: #9ca3af; padding: 60px;">
    <i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 16px; display: block;"></i>
    暂无生成记录
</p>'''

