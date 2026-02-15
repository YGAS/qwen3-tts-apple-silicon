/**
 * STT 页面功能
 */

let sttAudioFile = null;
let lastSTTResult = null;

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
    
    if (resultDiv) resultDiv.classList.add('hidden');
    if (errorDiv) errorDiv.classList.add('hidden');
    
    try {
        const formData = new FormData();
        formData.append('audio', sttAudioFile);
        
        // 获取用户选择的语言
        const languageSelect = document.getElementById('stt-language-select');
        if (languageSelect) {
            formData.append('language', languageSelect.value);
        }
        
        const response = await fetch('/api/stt', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            lastSTTResult = data;
            
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
                
                if (txtDownload) {
                    txtDownload.href = `/api/file/${data.txt_path}`;
                    txtDownload.download = data.txt_path.split('/').pop();
                }
                if (srtDownload) {
                    srtDownload.href = `/api/file/${data.srt_path}`;
                    srtDownload.download = data.srt_path.split('/').pop();
                }
                
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

function sendToClone() {
    if (!lastSTTResult) {
        alert('没有可用的识别结果');
        return;
    }
    
    // 构建 URL 参数，传递文本文件路径和音频文件路径
    const params = new URLSearchParams();
    if (lastSTTResult.txt_path) {
        params.append('txt_path', lastSTTResult.txt_path);
    }
    if (lastSTTResult.audio_path) {
        params.append('audio_path', lastSTTResult.audio_path);
    }
    // 也传递文本内容作为备用（如果文件路径不可用）
    if (lastSTTResult.text) {
        params.append('text', lastSTTResult.text);
    }
    
    const cloneUrl = `/clone?${params.toString()}`;
    window.location.href = cloneUrl;
}

