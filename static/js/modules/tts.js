/**
 * TTS 页面功能
 */

let currentSpeaker = null;
let currentSpeakerType = null;
let speakers = [];
let currentInputMode = 'text';
let currentImageFile = null;

/**
 * 切换输入模式
 */
function switchInputMode(mode) {
    currentInputMode = mode;

    // 更新按钮状态
    const textBtn = document.getElementById('btn-input-text');
    const imageBtn = document.getElementById('btn-input-image');

    if (mode === 'text') {
        textBtn.classList.add('active');
        imageBtn.classList.remove('active');
        document.getElementById('text-input-area').classList.remove('hidden');
        document.getElementById('image-input-area').classList.add('hidden');
    } else {
        textBtn.classList.remove('active');
        imageBtn.classList.add('active');
        document.getElementById('text-input-area').classList.add('hidden');
        document.getElementById('image-input-area').classList.remove('hidden');
    }
}

/**
 * 设置图片上传监听器
 */
function setupImageUploadListeners() {
    const dropZone = document.getElementById('image-drop-zone');
    const fileInput = document.getElementById('image-file');

    if (!dropZone || !fileInput) return;

    // 点击上传
    dropZone.addEventListener('click', () => fileInput.click());

    // 文件选择
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleImageFile(e.target.files[0]);
        }
    });

    // 拖拽上传
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
        if (e.dataTransfer.files.length > 0) {
            handleImageFile(e.dataTransfer.files[0]);
        }
    });

    // OCR文本输入监听
    const ocrTextArea = document.getElementById('ocr-text');
    if (ocrTextArea) {
        ocrTextArea.addEventListener('input', () => {
            const countEl = document.getElementById('ocr-text-count');
            if (countEl) {
                countEl.textContent = `${ocrTextArea.value.length} 字`;
            }
        });
    }
}

/**
 * 处理图片文件
 */
function handleImageFile(file) {
    // 验证文件类型
    if (!file.type.startsWith('image/')) {
        alert('请选择图片文件');
        return;
    }

    currentImageFile = file;

    // 显示文件名
    const fileNameEl = document.getElementById('image-file-name');
    fileNameEl.textContent = `已选择: ${file.name}`;
    fileNameEl.classList.remove('hidden');

    // 显示图片预览
    const previewContainer = document.getElementById('image-preview-container');
    const previewImg = document.getElementById('image-preview');

    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewContainer.classList.remove('hidden');
    };
    reader.readAsDataURL(file);

    // 显示OCR按钮
    document.getElementById('ocr-section').classList.remove('hidden');
    document.getElementById('ocr-result-area').classList.add('hidden');
}

/**
 * 执行OCR识别
 */
async function performOCR() {
    if (!currentImageFile) {
        alert('请先选择图片');
        return;
    }

    const btn = document.getElementById('btn-ocr');
    const loading = document.getElementById('ocr-loading');
    const resultArea = document.getElementById('ocr-result-area');
    const ocrTextArea = document.getElementById('ocr-text');

    // 禁用按钮，显示加载
    btn.disabled = true;
    loading.classList.remove('hidden');

    // 获取OCR配置
    const baseUrl = document.getElementById('ocr-base-url')?.value?.trim() || 'http://localhost:1234/v1';
    const apiKey = document.getElementById('ocr-api-key')?.value?.trim() || '';
    const model = document.getElementById('ocr-model')?.value?.trim() || 'qwen3.5-0.8b';

    // 验证配置
    const errorEl = document.getElementById('ocr-config-error');
    if (!baseUrl) {
        errorEl.textContent = '请输入OCR服务地址';
        errorEl.classList.remove('hidden');
        btn.disabled = false;
        return;
    }
    if (!apiKey) {
        errorEl.textContent = '请输入API Key';
        errorEl.classList.remove('hidden');
        btn.disabled = false;
        return;
    }
    if (!model) {
        errorEl.textContent = '请输入模型名称';
        errorEl.classList.remove('hidden');
        btn.disabled = false;
        return;
    }
    errorEl.classList.add('hidden');

    try {
        // 将图片转换为base64
        const base64Image = await fileToBase64(currentImageFile);

        const response = await fetch('/api/ocr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: base64Image,
                base_url: baseUrl,
                api_key: apiKey,
                model: model
            })
        });

        const data = await response.json();

        if (data.success) {
            ocrTextArea.value = data.text;
            resultArea.classList.remove('hidden');

            // 更新字数统计
            const countEl = document.getElementById('ocr-text-count');
            if (countEl) {
                countEl.textContent = `${data.text.length} 字`;
            }
        } else {
            alert('识别失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('OCR识别失败:', error);
        alert('识别失败，请检查OCR服务是否正常运行');
    } finally {
        btn.disabled = false;
        loading.classList.add('hidden');
    }
}

/**
 * 文件转Base64
 */
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

/**
 * 获取当前输入的文本（根据输入模式）
 */
function getCurrentInputText() {
    if (currentInputMode === 'text') {
        return document.getElementById('tts-text')?.value.trim() || '';
    } else {
        return document.getElementById('ocr-text')?.value.trim() || '';
    }
}

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

        if (!currentSpeaker && presetSpeakers.length > 0) {
            selectSpeaker(presetSpeakers[0].name);
        }
    } catch (error) {
        console.error('加载音色失败:', error);
    }
}

function selectSpeaker(name) {
    currentSpeaker = name;
    const speaker = speakers.find(s => s.name === name);
    currentSpeakerType = speaker ? speaker.type : null;
    
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
    const text = getCurrentInputText();
    if (!text) {
        if (currentInputMode === 'text') {
            alert('请输入文案');
        } else {
            alert('请先上传图片并识别文字');
        }
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
        
        if (currentSpeakerType === 'cloned') {
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
        
        if (currentSpeakerType === 'cloned') {
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

// 将函数暴露到全局作用域，供HTML内联事件处理器调用
window.switchInputMode = switchInputMode;
window.performOCR = performOCR;

/**
 * 切换OCR配置面板的显示/隐藏
 */
function toggleOCRConfig() {
    const panel = document.getElementById('ocr-config-panel');
    const btn = document.getElementById('btn-toggle-ocr-config');
    const btnText = btn.querySelector('span');

    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        btnText.textContent = '收起配置';
    } else {
        panel.classList.add('hidden');
        btnText.textContent = '展开配置';
    }
}

window.toggleOCRConfig = toggleOCRConfig;

