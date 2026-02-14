/**
 * Qwen3-TTS Web 前端逻辑
 */

// 全局状态
let currentSpeaker = null;
let currentSpeakerType = null; // 'preset' 或 'cloned'
let speakers = [];
let clonedAudioFile = null;
let sttAudioFile = null; // STT 音频文件
let lastSTTResult = null; // 最后一次 STT 结果

// 语言标签映射
const languageLabels = {
    'English': '英语',
    'Chinese': '中文',
    'Japanese': '日语',
    'Korean': '韩语'
};

// 处理音频路径，支持绝对路径和相对路径
function getAudioUrl(audioPath) {
    // 如果 audioPath 为空或 undefined，返回空字符串
    if (!audioPath || typeof audioPath !== 'string') {
        return '';
    }
    // 后端路由 /api/audio/{path:path} 会自动处理绝对路径和相对路径
    // 如果路径是绝对路径（以 / 开头），直接传递（后端会识别）
    // 如果路径是相对路径，也直接传递（后端会拼接 BASE_DIR）
    // 注意：避免双斜杠，如果路径以 / 开头，就不再加斜杠
    if (audioPath.startsWith('/')) {
        return `/api/audio${audioPath}`;
    } else {
        return `/api/audio/${audioPath}`;
    }
}

// 获取试听文本
function getPreviewText(speaker) {
    const isChinese = ['Vivian', 'Serena', 'Uncle_Fu', 'Dylan', 'Eric'].includes(speaker);
    return isChinese
        ? '你好，这是一个音色试听。'
        : 'Hello, this is a voice preview.';
}

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 根据当前页面路径初始化
    const path = window.location.pathname;

    if (path === '/tts' || path === '/') {
        loadSpeakersForTTS();
        setupTTSListeners();
    } else if (path === '/stt') {
        setupSTTListeners();
    } else if (path === '/speakers') {
        loadSpeakersPage();
    } else if (path === '/clone') {
        setupCloneListeners();
    } else if (path === '/history') {
        loadHistoryPage();
    }
});

// ========== 文字转语音页面功能 ==========

async function loadSpeakersForTTS() {
    try {
        const response = await fetch('/api/speakers');
        const data = await response.json();
        speakers = data.speakers;

        const grid = document.getElementById('speaker-grid');
        if (!grid) return;

        const presetSpeakers = speakers.filter(s => s.type === 'preset');
        const clonedSpeakers = speakers.filter(s => s.type === 'cloned');

        let html = '';

        // 预设音色区块
        if (presetSpeakers.length > 0) {
            html += '<div class="speaker-section">';
            html += '<h3 class="speaker-section-title">预设音色</h3>';
            html += '<div class="speaker-grid">';
            html += presetSpeakers.map(speaker => `
                <div class="speaker-card ${currentSpeaker === speaker.name ? 'selected' : ''}"
                     data-speaker="${speaker.name}"
                     onclick="selectSpeaker('${speaker.name}')">
                    <div class="speaker-name">${speaker.name}</div>
                    <div class="speaker-langs">
                        ${speaker.languages.map(lang => `
                            <span class="lang-tag">${languageLabels[lang] || lang}</span>
                        `).join('')}
                    </div>
                </div>
            `).join('');
            html += '</div></div>';
        }

        // 克隆音色区块
        if (clonedSpeakers.length > 0) {
            html += '<div class="speaker-section">';
            html += '<h3 class="speaker-section-title">克隆音色</h3>';
            html += '<div class="speaker-grid">';
            html += clonedSpeakers.map(speaker => `
                <div class="speaker-card ${currentSpeaker === speaker.name ? 'selected' : ''}"
                     data-speaker="${speaker.name}"
                     onclick="selectSpeaker('${speaker.name}')">
                    <div class="speaker-name" style="display: flex; align-items: center; gap: 6px;">
                        ${speaker.name}
                        <i class="fas fa-copy" style="font-size: 12px; color: #22c55e;"></i>
                    </div>
                    <div class="speaker-langs">
                        <span class="lang-tag">${languageLabels[speaker.languages[0]] || speaker.languages[0]}</span>
                    </div>
                </div>
            `).join('');
            html += '</div></div>';
        }

        grid.innerHTML = html;

        // 默认选择第一个预设音色
        if (!currentSpeaker && presetSpeakers.length > 0) {
            selectSpeaker(presetSpeakers[0].name);
        }
    } catch (error) {
        console.error('加载音色失败:', error);
    }
}

function selectSpeaker(name) {
    currentSpeaker = name;
    
    // 查找音色类型
    const speaker = speakers.find(s => s.name === name);
    currentSpeakerType = speaker ? speaker.type : null;
    
    // 更新选中状态
    document.querySelectorAll('.speaker-card').forEach(card => {
        card.classList.remove('selected');
        if (card.getAttribute('data-speaker') === name) {
            card.classList.add('selected');
        }
    });
}

function setupTTSListeners() {
    const textArea = document.getElementById('tts-text');
    if (textArea) {
        textArea.addEventListener('input', () => {
            const countEl = document.getElementById('text-count');
            if (countEl) {
                countEl.textContent = `${textArea.value.length} 字`;
            }
        });
    }
}

async function generateTTS() {
    const text = document.getElementById('tts-text')?.value.trim();
    if (!text) {
        alert('请输入文案');
        return;
    }
    
    if (!currentSpeaker || !currentSpeakerType) {
        alert('请选择音色');
        return;
    }
    
    const btn = document.getElementById('btn-generate');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> 生成中...';
    btn.disabled = true;
    
    try {
        const emotion = document.getElementById('tts-emotion').value;
        const speed = parseFloat(document.getElementById('tts-speed').value);
        const useLite = document.getElementById('tts-lite').checked;
        
        let response;
        
        // 根据音色类型选择不同的 API
        if (currentSpeakerType === 'cloned') {
            // 使用克隆音色 API
            const formData = new URLSearchParams();
            formData.append('text', text);
            formData.append('voice_name', currentSpeaker);
            formData.append('use_lite', useLite.toString());
            formData.append('preview', 'false');
            
            response = await fetch('/api/tts/clone', {
                method: 'POST',
                body: formData
            });
        } else {
            // 使用预设音色 API
            response = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text,
                    speaker: currentSpeaker,
                    emotion,
                    speed,
                    use_lite: useLite
                })
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            const resultDiv = document.getElementById('tts-result');
            const audio = document.getElementById('tts-audio');
            const downloadLink = document.getElementById('tts-download');
            
            const audioUrl = getAudioUrl(data.audio_path);
            audio.src = audioUrl;
            downloadLink.href = audioUrl;
            downloadLink.download = data.audio_path.split('/').pop();
            
            resultDiv.classList.remove('hidden');
            audio.play();
        } else {
            alert('生成失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('生成失败:', error);
        alert('生成失败，请检查模型是否已下载');
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}

async function previewSpeaker() {
    if (!currentSpeaker || !currentSpeakerType) {
        alert('请先选择音色');
        return;
    }
    
    const btn = document.getElementById('btn-preview');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> 生成中...';
    btn.disabled = true;
    
    try {
        const emotion = document.getElementById('tts-emotion').value;
        const speed = parseFloat(document.getElementById('tts-speed').value);
        const useLite = document.getElementById('tts-lite').checked;
        
        let response;
        
        // 根据音色类型选择不同的 API
        if (currentSpeakerType === 'cloned') {
            // 使用克隆音色预览 API
            const previewText = '你好，这是我的声音。';
            const formData = new URLSearchParams();
            formData.append('text', previewText);
            formData.append('voice_name', currentSpeaker);
            formData.append('use_lite', useLite.toString());
            formData.append('preview', 'true');
            
            response = await fetch('/api/tts/clone', {
                method: 'POST',
                body: formData
            });
        } else {
            // 使用预设音色预览 API
            const previewText = getPreviewText(currentSpeaker);
            
            response = await fetch('/api/tts/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: previewText,
                    speaker: currentSpeaker,
                    emotion,
                    speed,
                    use_lite: useLite
                })
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            const audio = new Audio(getAudioUrl(data.audio_path));
            audio.play();
            
            // 播放完成后自动删除临时音频（如果是预览）
            if (data.is_preview) {
                audio.onended = async () => {
                    try {
                        await fetch('/api/audio/cleanup', { method: 'DELETE' });
                    } catch (e) {
                        // 忽略清理错误
                    }
                };
            }
        } else {
            alert('试听失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('试听失败:', error);
        alert('试听失败');
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}

// ========== 音色库页面功能 ==========

async function loadSpeakersPage() {
    try {
        const response = await fetch('/api/speakers');
        const data = await response.json();
        speakers = data.speakers;
        
        // 预设音色
        const presetContainer = document.getElementById('preset-speakers');
        if (presetContainer) {
            const presetSpeakers = speakers.filter(s => s.type === 'preset');
            presetContainer.innerHTML = presetSpeakers.map(speaker => `
                <div class="speaker-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span class="speaker-name">${speaker.name}</span>
                        ${speaker.is_multilingual ? '<i class="fas fa-globe" style="color: #3b82f6;" title="多语言"></i>' : ''}
                    </div>
                    <div class="speaker-langs">
                        ${speaker.languages.map(lang => `
                            <span class="lang-tag">${languageLabels[lang] || lang}</span>
                        `).join('')}
                    </div>
                    <button onclick="previewSpeakerByName('${speaker.name}', this)" 
                            style="width: 100%; margin-top: 12px; padding: 8px; background: #4b5563; border: none; border-radius: 6px; color: #fff; cursor: pointer; font-size: 13px;">
                        <i class="fas fa-play" style="margin-right: 4px;"></i>试听
                    </button>
                </div>
            `).join('');
        }
        
        // 克隆音色
        const clonedContainer = document.getElementById('cloned-speakers');
        const noClonedMsg = document.getElementById('no-cloned');
        if (clonedContainer) {
            const clonedSpeakers = speakers.filter(s => s.type === 'cloned');
            
            if (clonedSpeakers.length === 0) {
                clonedContainer.innerHTML = '';
                if (noClonedMsg) noClonedMsg.classList.remove('hidden');
            } else {
                if (noClonedMsg) noClonedMsg.classList.add('hidden');
                clonedContainer.innerHTML = clonedSpeakers.map(speaker => `
                    <div class="speaker-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span class="speaker-name">${speaker.name}</span>
                            <i class="fas fa-copy" style="color: #22c55e;"></i>
                        </div>
                        <div class="speaker-langs">
                            <span class="lang-tag">${languageLabels[speaker.languages[0]] || speaker.languages[0]}</span>
                        </div>
                        <div style="display: flex; gap: 8px; margin-top: 12px;">
                            <button onclick="previewClonedSpeaker('${speaker.name}', this)" 
                                    style="flex: 1; padding: 8px; background: #4b5563; border: none; border-radius: 6px; color: #fff; cursor: pointer; font-size: 13px;">
                                <i class="fas fa-play"></i>
                            </button>
                            <button onclick="deleteClonedSpeaker('${speaker.name}')" 
                                    style="padding: 8px 12px; background: #dc2626; border: none; border-radius: 6px; color: #fff; cursor: pointer; font-size: 13px;">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('加载音色失败:', error);
    }
}

async function previewSpeakerByName(name, btnElement) {
    const previewText = getPreviewText(name);

    // 保存原始按钮内容并显示加载状态
    const originalHTML = btnElement.innerHTML;
    btnElement.innerHTML = '<span class="spinner"></span> 生成中...';
    btnElement.disabled = true;

    try {
        // 使用 preview API，不保存历史记录
        const response = await fetch('/api/tts/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: previewText,
                speaker: name,
                emotion: 'Normal tone',
                speed: 1.0,
                use_lite: true
            })
        });

        const data = await response.json();

        if (data.success) {
            const audio = new Audio(getAudioUrl(data.audio_path));
            audio.play();

            // 播放完成后自动删除临时音频
            audio.onended = async () => {
                try {
                    await fetch('/api/audio/cleanup', { method: 'DELETE' });
                } catch (e) {
                    // 忽略清理错误
                }
            };
        } else {
            alert('试听失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('试听失败:', error);
        alert('试听失败，请检查模型是否已下载');
    } finally {
        btnElement.innerHTML = originalHTML;
        btnElement.disabled = false;
    }
}

async function previewClonedSpeaker(name, btnElement) {
    // 保存原始按钮内容并显示加载状态
    const originalHTML = btnElement.innerHTML;
    btnElement.innerHTML = '<span class="spinner"></span>';
    btnElement.disabled = true;

    try {
        // 使用 clone preview API，不保存历史记录
        const response = await fetch('/api/tts/clone', {
            method: 'POST',
            body: new URLSearchParams({
                text: '你好，这是我的声音。',
                voice_name: name,
                use_lite: 'true',
                preview: 'true'
            })
        });

        const data = await response.json();

        if (data.success) {
            const audio = new Audio(getAudioUrl(data.audio_path));
            audio.play();

            // 播放完成后自动删除临时音频
            audio.onended = async () => {
                try {
                    await fetch('/api/audio/cleanup', { method: 'DELETE' });
                } catch (e) {
                    // 忽略清理错误
                }
            };
        } else {
            alert('试听失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('试听失败:', error);
        alert('试听失败，请检查模型是否已下载');
    } finally {
        btnElement.innerHTML = originalHTML;
        btnElement.disabled = false;
    }
}

async function deleteClonedSpeaker(name) {
    if (!confirm(`确定要删除音色 "${name}" 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/voices/${name}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadSpeakersPage();
        }
    } catch (error) {
        console.error('删除失败:', error);
        alert('删除失败');
    }
}

// ========== 克隆声音页面功能 ==========

function setupCloneListeners() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('clone-audio');
    
    if (!dropZone || !fileInput) return;
    
    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleAudioFile(files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleAudioFile(e.target.files[0]);
        }
    });
}

function handleAudioFile(file) {
    if (!file.type.startsWith('audio/')) {
        alert('请选择音频文件');
        return;
    }
    
    clonedAudioFile = file;
    const fileNameEl = document.getElementById('file-name');
    if (fileNameEl) {
        fileNameEl.textContent = `已选择: ${file.name}`;
        fileNameEl.classList.remove('hidden');
    }
}

async function cloneVoice() {
    const name = document.getElementById('clone-name')?.value.trim();
    const text = document.getElementById('clone-text')?.value.trim();
    const language = document.getElementById('clone-language')?.value;
    
    if (!name) {
        alert('请输入音色名称');
        return;
    }
    
    if (!clonedAudioFile) {
        alert('请上传参考音频');
        return;
    }
    
    if (!text) {
        alert('请输入参考文案');
        return;
    }
    
    const btn = document.getElementById('btn-clone');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> 克隆中...';
    btn.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('text', text);
        formData.append('language', language);
        formData.append('audio', clonedAudioFile);
        
        const response = await fetch('/api/clone', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            const resultDiv = document.getElementById('clone-result');
            const messageEl = document.getElementById('clone-message');
            
            messageEl.textContent = data.message;
            resultDiv.classList.remove('hidden');
            
            // 清空表单
            document.getElementById('clone-name').value = '';
            document.getElementById('clone-text').value = '';
            clonedAudioFile = null;
            
            const fileNameEl = document.getElementById('file-name');
            if (fileNameEl) fileNameEl.classList.add('hidden');
        } else {
            alert('克隆失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('克隆失败:', error);
        alert('克隆失败');
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}

// ========== 生成历史页面功能 ==========

async function loadHistoryPage() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();
        
        const historyList = document.getElementById('history-list');
        const noHistory = document.getElementById('no-history');
        
        if (!historyList) return;
        
        if (data.history.length === 0) {
            historyList.innerHTML = '';
            if (noHistory) noHistory.classList.remove('hidden');
            return;
        }
        
        if (noHistory) noHistory.classList.add('hidden');
        
        historyList.innerHTML = data.history.map(item => {
            // STT 历史记录可能没有 audio_path（只保存文本和字幕文件）
            const hasAudio = item.audio_path && item.type !== 'stt';
            const audioUrl = getAudioUrl(item.audio_path);
            
            return `
            <div class="history-item">
                <div class="history-header">
                    <div style="flex: 1;">
                        <p class="history-text">${escapeHtml(item.text)}</p>
                        <div class="history-meta">
                            ${item.speaker ? `<span><i class="fas fa-user" style="margin-right: 4px;"></i>${item.speaker}</span>` : ''}
                            <span><i class="fas fa-clock" style="margin-right: 4px;"></i>${formatDate(item.created_at)}</span>
                            ${item.type === 'stt' ? '<span><i class="fas fa-microphone" style="margin-right: 4px;"></i>语音转文字</span>' : ''}
                        </div>
                    </div>
                    <button onclick="deleteHistory('${item.id}')" 
                            style="padding: 8px 12px; background: #dc2626; border: none; border-radius: 6px; color: #fff; cursor: pointer;">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                ${hasAudio ? `<audio src="${audioUrl}" controls></audio>` : ''}
                <div style="margin-top: 12px;">
                    ${hasAudio ? `
                    <a href="${audioUrl}" download 
                       style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: #4b5563; border-radius: 6px; color: #fff; text-decoration: none; font-size: 14px;">
                        <i class="fas fa-download"></i>下载音频
                    </a>
                    ` : ''}
                    ${item.type === 'stt' ? `
                    ${item.txt_path ? `
                    <a href="/api/file/${item.txt_path}" download 
                       style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: #4b5563; border-radius: 6px; color: #fff; text-decoration: none; font-size: 14px; margin-left: 8px;">
                        <i class="fas fa-file-alt"></i>下载 TXT
                    </a>
                    ` : ''}
                    ${item.srt_path ? `
                    <a href="/api/file/${item.srt_path}" download 
                       style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: #4b5563; border-radius: 6px; color: #fff; text-decoration: none; font-size: 14px; margin-left: 8px;">
                        <i class="fas fa-file-alt"></i>下载 SRT
                    </a>
                    ` : ''}
                    ` : ''}
                </div>
            </div>
        `;
        }).join('');
    } catch (error) {
        console.error('加载历史记录失败:', error);
    }
}

async function deleteHistory(id) {
    if (!confirm('确定要删除这条记录吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/history/${id}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadHistoryPage();
        }
    } catch (error) {
        console.error('删除失败:', error);
        alert('删除失败');
    }
}

// ========== 工具函数 ==========

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== 语音转文字页面功能 ==========

function setupSTTListeners() {
    const dropZone = document.getElementById('stt-drop-zone');
    const fileInput = document.getElementById('stt-audio');
    
    if (!dropZone || !fileInput) return;
    
    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleSTTAudioFile(files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleSTTAudioFile(e.target.files[0]);
        }
    });
}

function handleSTTAudioFile(file) {
    if (!file.type.startsWith('audio/')) {
        alert('请选择音频文件');
        return;
    }
    
    sttAudioFile = file;
    const fileNameEl = document.getElementById('stt-file-name');
    if (fileNameEl) {
        fileNameEl.textContent = `已选择: ${file.name}`;
        fileNameEl.classList.remove('hidden');
    }
    
    // 隐藏之前的结果和错误
    const resultDiv = document.getElementById('stt-result');
    const errorDiv = document.getElementById('stt-error');
    if (resultDiv) resultDiv.classList.add('hidden');
    if (errorDiv) errorDiv.classList.add('hidden');
}

async function generateSTT() {
    if (!sttAudioFile) {
        alert('请上传音频文件');
        return;
    }
    
    const btn = document.getElementById('btn-stt-generate');
    const retryBtn = document.getElementById('btn-stt-retry');
    const resultDiv = document.getElementById('stt-result');
    const errorDiv = document.getElementById('stt-error');
    
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> 识别中...';
    btn.disabled = true;
    if (retryBtn) retryBtn.style.display = 'none';
    
    // 隐藏之前的结果和错误
    if (resultDiv) resultDiv.classList.add('hidden');
    if (errorDiv) errorDiv.classList.add('hidden');
    
    try {
        const formData = new FormData();
        formData.append('audio', sttAudioFile);
        
        const response = await fetch('/api/stt', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            lastSTTResult = data;
            
            // 显示结果
            if (resultDiv) {
                const textEl = document.getElementById('stt-text');
                const languageEl = document.getElementById('stt-language');
                const segmentsEl = document.getElementById('stt-segments');
                const txtDownload = document.getElementById('stt-download-txt');
                const srtDownload = document.getElementById('stt-download-srt');
                const toCloneBtn = document.getElementById('btn-stt-to-clone');
                
                if (textEl) textEl.textContent = data.text;
                if (languageEl) {
                    const langMap = {'zh': '中文', 'en': '英语', 'ja': '日语', 'ko': '韩语'};
                    languageEl.textContent = langMap[data.language] || data.language;
                }
                
                // 显示分段信息
                if (segmentsEl && data.segments && data.segments.length > 0) {
                    let segmentsHTML = '<div style="margin-top: 16px;"><label class="form-label">分段信息</label>';
                    segmentsHTML += '<div style="max-height: 200px; overflow-y: auto;">';
                    data.segments.forEach((seg, idx) => {
                        const start = formatTime(seg.start);
                        const end = formatTime(seg.end);
                        const confidence = seg.confidence > 0 ? ` (${(seg.confidence * 100).toFixed(1)}%)` : '';
                        segmentsHTML += `
                            <div style="background-color: #374151; border-radius: 6px; padding: 12px; margin-bottom: 8px;">
                                <div style="font-size: 12px; color: #9ca3af; margin-bottom: 4px;">
                                    ${start} - ${end}${confidence}
                                </div>
                                <div style="color: #d1d5db;">${escapeHtml(seg.text)}</div>
                            </div>
                        `;
                    });
                    segmentsHTML += '</div></div>';
                    segmentsEl.innerHTML = segmentsHTML;
                }
                
                // 设置下载链接
                if (txtDownload) {
                    txtDownload.href = `/api/file/${data.txt_path}`;
                    txtDownload.download = data.txt_path.split('/').pop();
                }
                if (srtDownload) {
                    srtDownload.href = `/api/file/${data.srt_path}`;
                    srtDownload.download = data.srt_path.split('/').pop();
                }
                
                // 显示"用于克隆音色"按钮
                if (toCloneBtn) {
                    toCloneBtn.style.display = 'inline-flex';
                }
                
                resultDiv.classList.remove('hidden');
            }
        } else {
            throw new Error(data.detail || '识别失败');
        }
    } catch (error) {
        console.error('STT 失败:', error);
        const errorDiv = document.getElementById('stt-error');
        const errorMsg = document.getElementById('stt-error-message');
        if (errorDiv && errorMsg) {
            errorMsg.textContent = `识别失败: ${error.message}`;
            errorDiv.classList.remove('hidden');
        }
        if (retryBtn) retryBtn.style.display = 'inline-flex';
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}

function retrySTT() {
    if (sttAudioFile) {
        generateSTT();
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins}:${secs.padStart(4, '0')}`;
}

function sendToClone() {
    if (!lastSTTResult || !sttAudioFile) {
        alert('没有可用的识别结果');
        return;
    }
    
    // 跳转到克隆页面，并传递数据
    const cloneUrl = `/clone?text=${encodeURIComponent(lastSTTResult.text)}`;
    window.location.href = cloneUrl;
    
    // 使用 sessionStorage 存储数据，以便克隆页面使用
    sessionStorage.setItem('stt_text', lastSTTResult.text);
    sessionStorage.setItem('stt_audio_name', sttAudioFile.name);
}
