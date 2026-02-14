/**
 * 克隆声音页面功能
 */

let clonedAudioFile = null;

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

