/**
 * TTS 页面功能
 */

let currentSpeaker = null;
let currentSpeakerType = null;
let speakers = [];

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

