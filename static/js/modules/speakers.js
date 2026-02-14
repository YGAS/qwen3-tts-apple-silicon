/**
 * 音色库页面功能
 */

let speakers = [];

async function loadSpeakersPage() {
    try {
        const response = await fetch('/api/speakers');
        const data = await response.json();
        speakers = data.speakers;
        
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
    const originalHTML = btnElement.innerHTML;
    btnElement.innerHTML = '<span class="spinner"></span> 生成中...';
    btnElement.disabled = true;

    try {
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
    const originalHTML = btnElement.innerHTML;
    btnElement.innerHTML = '<span class="spinner"></span>';
    btnElement.disabled = true;

    try {
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

