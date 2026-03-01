/**
 * OCR 页面功能 - 图片转 Markdown
 */

let ocrImageFile = null;
let lastOCRResult = null;

/**
 * 设置 OCR 页面事件监听
 */
function setupOCRListeners() {
    const dropZone = document.getElementById('ocr-drop-zone');
    const fileInput = document.getElementById('ocr-image');

    if (!dropZone || !fileInput) return;

    // 点击上传
    dropZone.addEventListener('click', () => fileInput.click());

    // 拖拽事件
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
            handleOCRImageFile(files[0]);
        }
    });

    // 文件选择事件
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleOCRImageFile(e.target.files[0]);
        }
    });
}

/**
 * 处理上传的图片文件
 * @param {File} file - 图片文件
 */
function handleOCRImageFile(file) {
    // 验证文件类型
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/bmp'];
    if (!validTypes.includes(file.type)) {
        alert('请选择有效的图片文件（PNG, JPG, JPEG, GIF, WEBP, BMP）');
        return;
    }

    ocrImageFile = file;

    // 显示图片预览
    const previewContainer = document.getElementById('ocr-image-preview-container');
    const previewImg = document.getElementById('ocr-image-preview');
    const fileNameEl = document.getElementById('ocr-file-name');

    if (previewContainer && previewImg) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            previewContainer.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }

    if (fileNameEl) {
        fileNameEl.textContent = `已选择: ${file.name} (${formatFileSize(file.size)})`;
    }

    // 隐藏之前的结果
    hideResult();
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的文件大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 隐藏结果区域
 */
function hideResult() {
    const resultDiv = document.getElementById('ocr-result');
    const errorDiv = document.getElementById('ocr-error');
    const loadingDiv = document.getElementById('ocr-loading');

    if (resultDiv) resultDiv.classList.add('hidden');
    if (errorDiv) errorDiv.classList.add('hidden');
    if (loadingDiv) loadingDiv.classList.add('hidden');
}

/**
 * 执行 OCR 识别
 */
async function generateOCR() {
    if (!ocrImageFile) {
        alert('请上传图片文件');
        return;
    }

    const btn = document.getElementById('btn-ocr-generate');
    const loadingDiv = document.getElementById('ocr-loading');
    const resultDiv = document.getElementById('ocr-result');
    const errorDiv = document.getElementById('ocr-error');

    // 保存原始按钮内容
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> 识别中...';
    btn.disabled = true;

    // 隐藏之前的结果和错误
    if (resultDiv) resultDiv.classList.add('hidden');
    if (errorDiv) errorDiv.classList.add('hidden');
    if (loadingDiv) loadingDiv.classList.remove('hidden');

    try {
        // 构建表单数据
        const formData = new FormData();
        formData.append('file', ocrImageFile);

        // 获取参数
        const promptEl = document.getElementById('ocr-prompt');
        const maxTokensEl = document.getElementById('ocr-max-tokens');
        const temperatureEl = document.getElementById('ocr-temperature');
        const cleanupTagsEl = document.getElementById('ocr-cleanup-tags');

        if (promptEl) formData.append('prompt', promptEl.value);
        if (maxTokensEl) formData.append('max_tokens', maxTokensEl.value);
        if (temperatureEl) formData.append('temperature', temperatureEl.value);
        if (cleanupTagsEl) formData.append('cleanup_tags', cleanupTagsEl.checked);

        // 发送请求
        const response = await fetch('/api/ocr', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            lastOCRResult = data.data;
            displayResult(data.data);
        } else {
            throw new Error(data.detail || '识别失败');
        }
    } catch (error) {
        console.error('OCR 失败:', error);
        showError(error.message);
    } finally {
        // 恢复按钮状态
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        if (loadingDiv) loadingDiv.classList.add('hidden');
    }
}

/**
 * 显示识别结果
 * @param {Object} data - 识别结果数据
 */
function displayResult(data) {
    const resultDiv = document.getElementById('ocr-result');
    const textEl = document.getElementById('ocr-text');
    const statsEl = document.getElementById('ocr-stats');
    const rawSection = document.getElementById('ocr-raw-section');
    const rawTextEl = document.getElementById('ocr-raw-text');

    if (!resultDiv) return;

    // 显示 Markdown 文本
    if (textEl) {
        textEl.textContent = data.markdown || '';
    }

    // 显示统计信息
    if (statsEl) {
        const charCount = (data.markdown || '').length;
        statsEl.textContent = `${charCount} 字符`;
    }

    // 显示原始输出（如果有 grounding tags）
    if (rawSection && rawTextEl && data.raw_text) {
        const hasTags = data.raw_text.includes('<|ref|>') || data.raw_text.includes('<|det|>');
        if (hasTags) {
            rawTextEl.textContent = data.raw_text;
            rawSection.classList.remove('hidden');
        } else {
            rawSection.classList.add('hidden');
        }
    }

    resultDiv.classList.remove('hidden');

    // 滚动到结果区域
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * 显示错误信息
 * @param {string} message - 错误信息
 */
function showError(message) {
    const errorDiv = document.getElementById('ocr-error');
    const errorMsg = document.getElementById('ocr-error-message');

    if (errorDiv && errorMsg) {
        errorMsg.textContent = message;
        errorDiv.classList.remove('hidden');
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

/**
 * 清空所有内容
 */
function clearOCR() {
    // 清空文件
    ocrImageFile = null;
    lastOCRResult = null;

    // 清空文件输入
    const fileInput = document.getElementById('ocr-image');
    if (fileInput) fileInput.value = '';

    // 隐藏预览
    const previewContainer = document.getElementById('ocr-image-preview-container');
    if (previewContainer) previewContainer.classList.add('hidden');

    // 重置参数
    const promptEl = document.getElementById('ocr-prompt');
    const maxTokensEl = document.getElementById('ocr-max-tokens');
    const temperatureEl = document.getElementById('ocr-temperature');
    const cleanupTagsEl = document.getElementById('ocr-cleanup-tags');

    if (promptEl) promptEl.value = '只提取图片中的原始文字内容，不要添加任何描述或标题。';
    if (maxTokensEl) maxTokensEl.value = '4000';
    if (temperatureEl) temperatureEl.value = '0.0';
    if (cleanupTagsEl) cleanupTagsEl.checked = true;

    // 隐藏结果和错误
    hideResult();
}

/**
 * 复制识别结果到剪贴板
 */
async function copyOCRResult() {
    if (!lastOCRResult || !lastOCRResult.markdown) {
        alert('没有可复制的内容');
        return;
    }

    try {
        await navigator.clipboard.writeText(lastOCRResult.markdown);

        // 显示复制成功提示
        const btn = event.target.closest('button');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check"></i><span>已复制</span>';
        btn.style.backgroundColor = '#22c55e';

        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.backgroundColor = '';
        }, 2000);
    } catch (err) {
        console.error('复制失败:', err);
        alert('复制失败，请手动复制');
    }
}

/**
 * 下载识别结果为 .mmd 文件
 */
function downloadOCRResult() {
    if (!lastOCRResult || !lastOCRResult.markdown) {
        alert('没有可下载的内容');
        return;
    }

    const blob = new Blob([lastOCRResult.markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;

    // 生成文件名
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    a.download = `ocr-result-${timestamp}.mmd`;

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    URL.revokeObjectURL(url);
}

/**
 * 切换原始输出显示/隐藏
 */
function toggleRawOutput() {
    const rawSection = document.getElementById('ocr-raw-section');
    const btn = event.target.closest('button');

    if (!rawSection || !btn) return;

    const isHidden = rawSection.classList.contains('hidden');

    if (isHidden) {
        rawSection.classList.remove('hidden');
        btn.innerHTML = '<i class="fas fa-eye-slash"></i><span>隐藏</span>';
    } else {
        rawSection.classList.add('hidden');
        btn.innerHTML = '<i class="fas fa-eye"></i><span>显示</span>';
    }
}
