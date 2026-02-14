/**
 * 历史记录页面功能
 */

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

