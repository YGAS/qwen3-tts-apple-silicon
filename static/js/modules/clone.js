/**
 * 克隆声音页面功能
 */

let clonedAudioFile = null;
let sttAudioPath = null;  // 从 STT 页面传递过来的音频文件路径

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
    
    // 处理从 STT 页面传递过来的参数
    handleSTTParams();
}

async function handleSTTParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const txtPath = urlParams.get('txt_path');
    const audioPath = urlParams.get('audio_path');
    const text = urlParams.get('text');
    
    // 如果有文本文件路径，从服务器读取文本内容
    if (txtPath) {
        try {
            const response = await fetch(`/api/file/${txtPath}`);
            if (response.ok) {
                const textContent = await response.text();
                const textArea = document.getElementById('clone-text');
                if (textArea) {
                    textArea.value = textContent.trim();
                }
            }
        } catch (error) {
            console.error('读取文本文件失败:', error);
            // 如果读取失败，使用 URL 参数中的文本作为备用
            if (text) {
                const textArea = document.getElementById('clone-text');
                if (textArea) {
                    textArea.value = text;
                }
            }
        }
    } else if (text) {
        // 如果没有文件路径，直接使用 URL 参数中的文本
        const textArea = document.getElementById('clone-text');
        if (textArea) {
            textArea.value = text;
        }
    }
    
    // 如果有音频文件路径，保存并显示音频文件名
    if (audioPath) {
        sttAudioPath = audioPath;  // 保存音频路径，后续克隆时直接使用
        const fileName = audioPath.split('/').pop();
        const fileNameEl = document.getElementById('file-name');
        if (fileNameEl) {
            fileNameEl.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px;">
                    <i class="fas fa-check-circle" style="color: #22c55e;"></i>
                    <span style="font-weight: 500;">已选择音频文件: ${escapeHtml(fileName)}</span>
                    <a href="/api/file/${audioPath}" download="${fileName}" style="margin-left: auto; color: #3b82f6; text-decoration: none; font-size: 13px;">
                        <i class="fas fa-download"></i> 下载
                    </a>
                </div>
            `;
            fileNameEl.classList.remove('hidden');
        }
    }
}

function handleAudioFile(file) {
    if (!file.type.startsWith('audio/')) {
        alert('请选择音频文件');
        return;
    }
    
    clonedAudioFile = file;
    sttAudioPath = null;  // 用户手动上传文件时，清除 STT 传递的路径
    const fileNameEl = document.getElementById('file-name');
    if (fileNameEl) {
        // 如果之前有从 STT 传递的信息，更新显示为用户新选择的文件
        fileNameEl.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-check-circle" style="color: #22c55e;"></i>
                <span>已选择: ${escapeHtml(file.name)}</span>
            </div>
        `;
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
    
    if (!sttAudioPath && !clonedAudioFile) {
        alert('请提供参考音频');
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
        
        // 优先使用 STT 传递的音频路径，否则使用上传的文件
        if (sttAudioPath) {
            formData.append('audio_path', sttAudioPath);
        } else {
            formData.append('audio', clonedAudioFile);
        }
        
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
            
            document.getElementById('clone-name').value = '';
            document.getElementById('clone-text').value = '';
            clonedAudioFile = null;
            sttAudioPath = null;
            
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

