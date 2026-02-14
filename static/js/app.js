/**
 * Qwen3-TTS Web 前端主入口
 */

// 加载模块（按顺序）
const scripts = [
    '/static/js/modules/config.js',
    '/static/js/modules/utils.js',
    '/static/js/modules/tts.js',
    '/static/js/modules/stt.js',
    '/static/js/modules/speakers.js',
    '/static/js/modules/clone.js',
    '/static/js/modules/history.js'
];

// 动态加载脚本
function loadScripts(scripts, callback) {
    let loaded = 0;
    scripts.forEach(src => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = () => {
            loaded++;
            if (loaded === scripts.length && callback) {
                callback();
            }
        };
        script.onerror = () => {
            console.error(`Failed to load script: ${src}`);
            loaded++;
            if (loaded === scripts.length && callback) {
                callback();
            }
        };
        document.head.appendChild(script);
    });
}

// 页面初始化
loadScripts(scripts, () => {
    document.addEventListener('DOMContentLoaded', function() {
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
    
    // 如果 DOM 已经加载完成，直接执行
    if (document.readyState === 'loading') {
        // DOM 还在加载，等待 DOMContentLoaded
    } else {
        // DOM 已经加载完成，直接执行
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
    }
});
