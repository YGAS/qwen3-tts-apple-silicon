/**
 * 工具函数
 */

// 处理音频路径，支持绝对路径和相对路径
function getAudioUrl(audioPath) {
    if (!audioPath || typeof audioPath !== 'string') {
        return '';
    }
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

// 格式化日期
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 转义 HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 格式化时间（秒数）
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins}:${secs.padStart(4, '0')}`;
}

