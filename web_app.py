"""
Qwen3-TTS Web 应用
提供 RESTful API 和 Web 界面
"""

import os
import sys
import shutil
import time
import wave
import gc
import re
import subprocess
import warnings
import uuid
import json
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Suppress harmless library warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from mlx_audio.tts.utils import load_model
    from mlx_audio.tts.generate import generate_audio
    from mlx_audio.stt.utils import load_model as load_stt_model
    from mlx_audio.stt.generate import generate_transcription
except ImportError:
    print("Error: 'mlx_audio' library not found.")
    print("Run: source .venv/bin/activate")
    sys.exit(1)

# Configuration - 使用脚本所在目录作为基准
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
MODELS_DIR = os.path.join(BASE_DIR, "models")
VOICES_DIR = os.path.join(BASE_DIR, "voices")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
STT_OUTPUT_DIR = os.path.join(BASE_OUTPUT_DIR, "STT")

# Settings
SAMPLE_RATE = 24000
FILENAME_MAX_LEN = 20

# Model Definitions - 简化配置，自动选择
MODELS = {
    "custom": {
        "pro": {"folder": "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit", "output_subfolder": "CustomVoice"},
        "lite": {"folder": "Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit", "output_subfolder": "CustomVoice"},
    },
    "design": {
        "pro": {"folder": "Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit", "output_subfolder": "VoiceDesign"},
        "lite": {"folder": "Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit", "output_subfolder": "VoiceDesign"},
    },
    "clone": {
        "pro": {"folder": "Qwen3-TTS-12Hz-1.7B-Base-8bit", "output_subfolder": "Clones"},
        "lite": {"folder": "Qwen3-TTS-12Hz-0.6B-Base-8bit", "output_subfolder": "Clones"},
    },
}

# ASR Model Definitions - 语音转文字模型配置
# mlx-audio 支持的 STT 模型类型：
# - whisper: OpenAI Whisper 模型（推荐，多语言支持好）
# - parakeet: NVIDIA Parakeet 模型
# - voxtral: Voxtral 模型
# - glmasr: GLM ASR 模型
# - vibevoice_asr: VibeVoice ASR 模型
# - wav2vec: Facebook Wav2Vec2 模型
#
# 配置说明：
# - model_id: HuggingFace 模型 ID（从网络加载）或本地路径（从本地加载）
# - folder: 本地模型文件夹名称（如果使用本地加载）
# - type: 模型类型（whisper, parakeet, voxtral, glmasr, vibevoice_asr, wav2vec）
# - default: 是否为默认模型
#
# 本地配置方式：
# 1. 将模型下载到 models/ 目录下（参考 TTS 模型的目录结构）
# 2. 设置 folder 为模型文件夹名称
# 3. load_asr_model_cached 会自动从本地加载
#
# 网络配置方式：
# 1. 设置 model_id 为 HuggingFace 模型 ID（如 "openai/whisper-base"）
# 2. 首次加载会自动下载并缓存到 ~/.cache/huggingface/hub/
# 3. 后续加载会使用本地缓存
ASR_MODELS = {
    # Qwen3-ASR 模型（本地加载）
    "qwen3_asr_0.6b": {
        "folder": "Qwen3-ASR-0.6B-8bit",  # 本地文件夹名称
        "type": "qwen3_asr",
        "default": True  # 默认模型
    },
    # Whisper 模型示例（备用，已注释）
    # "whisper_base": {
    #     "model_id": "openai/whisper-base",  # 从网络加载
    #     "folder": "whisper-base",  # 本地文件夹名称（如果使用本地加载）
    #     "type": "whisper",
    #     "default": False
    # },
    # Parakeet 模型示例
    # "parakeet": {
    #     "model_id": "mlx-community/parakeet-tdt-1.1b",
    #     "folder": "parakeet-tdt-1.1b",
    #     "type": "parakeet",
    #     "default": False
    # },
    # Wav2Vec2 模型示例
    # "wav2vec2": {
    #     "model_id": "facebook/wav2vec2-base-960h",
    #     "folder": "wav2vec2-base-960h",
    #     "type": "wav2vec",
    #     "default": False
    # },
}

# 音色映射表
SPEAKER_MAP = {
    "English": ["Ryan", "Aiden", "Ethan", "Chelsie", "Serena", "Vivian"],
    "Chinese": ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"],
    "Japanese": ["Ono_Anna"],
    "Korean": ["Sohee"]
}

# 语气选项
EMOTION_OPTIONS = [
    {"value": "Normal tone", "label": "正常", "description": "标准语调"},
    {"value": "Sad and crying, speaking slowly", "label": "悲伤哭泣", "description": "悲伤哭泣，语速较慢"},
    {"value": "Excited and happy, speaking very fast", "label": "兴奋开心", "description": "兴奋开心，语速很快"},
    {"value": "Angry and shouting", "label": "愤怒大喊", "description": "愤怒大喊"},
    {"value": "Whispering quietly", "label": "轻声耳语", "description": "轻声耳语"},
]

# 语速选项
SPEED_OPTIONS = [
    {"value": 0.8, "label": "慢速 (0.8x)"},
    {"value": 1.0, "label": "正常 (1.0x)"},
    {"value": 1.3, "label": "快速 (1.3x)"},
]

# 语言选项
LANGUAGE_OPTIONS = [
    {"value": "English", "label": "英语"},
    {"value": "Chinese", "label": "中文"},
    {"value": "Japanese", "label": "日语"},
    {"value": "Korean", "label": "韩语"},
]

# 启动和关闭事件处理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import asyncio
    import concurrent.futures
    
    # 启动时执行
    print("[启动] 应用启动中...")
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(VOICES_DIR, exist_ok=True)
    
    # 预加载常用模型（在线程池中执行，避免阻塞事件循环）
    def preload_model_sync(mode: str, use_lite: bool, name: str):
        """同步加载模型（在线程中执行）"""
        try:
            load_model_cached(mode, use_lite)
            print(f"[启动] ✓ {name} 预加载完成")
            return True
        except Exception as e:
            print(f"[启动] ⚠ {name} 预加载失败: {e}")
            return False
    
    # 禁用启动时预加载模型（MLX/Metal 在并发加载时会出现命令缓冲区冲突）
    # 改为按需加载，首次使用时自动加载并缓存
    # 这样可以避免启动时的 Metal 错误，同时保持模型缓存机制
    print("[启动] 模型将按需加载（首次使用时自动缓存）")
    
    # 如果需要预加载，可以取消下面的注释，但必须串行执行
    # async def preload_models():
    #     await asyncio.sleep(1)  # 等待应用完全启动
    #     try:
    #         preload_model_sync("custom", True, "预设音色模型 (Lite)")
    #     except Exception as e:
    #         print(f"[启动] ⚠ 模型预加载失败: {e}")
    # task = asyncio.create_task(preload_models())
    task = None
    
    yield  # 应用运行期间
    
    # 如果应用关闭时模型还在加载，取消任务
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # 关闭时执行（如果需要清理资源）
    print("[关闭] 应用关闭中...")


# FastAPI 应用
app = FastAPI(
    title="Qwen3-TTS Web",
    description="Qwen3-TTS 的 Web 界面",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 缓存的模型
_cached_models = {}
_cached_asr_models = {}  # ASR 模型缓存
_model_loading_lock = {}  # 用于防止并发加载同一模型
_asr_model_loading_lock = {}  # ASR 模型加载锁


# Pydantic 模型
class TTSRequest(BaseModel):
    text: str
    speaker: str
    emotion: str = "Normal tone"
    speed: float = 1.0
    use_lite: bool = False


class CloneRequest(BaseModel):
    name: str
    text: str
    language: str = "English"


class HistoryItem(BaseModel):
    id: str
    text: str
    speaker: str
    emotion: str
    speed: float
    audio_path: str
    created_at: str


# 工具函数
def get_smart_path(folder_name: str) -> Optional[str]:
    """获取模型路径"""
    full_path = os.path.join(MODELS_DIR, folder_name)
    if not os.path.exists(full_path):
        return None

    snapshots_dir = os.path.join(full_path, "snapshots")
    if os.path.exists(snapshots_dir):
        subfolders = [f for f in os.listdir(snapshots_dir) if not f.startswith('.')]
        if subfolders:
            return os.path.join(snapshots_dir, subfolders[0])

    return full_path


def load_model_cached(mode: str, use_lite: bool = False):
    """加载并缓存模型"""
    import threading
    
    key = f"{mode}_{'lite' if use_lite else 'pro'}"
    
    # 如果模型已缓存，直接返回
    if key in _cached_models:
        return _cached_models[key]
    
    # 使用锁防止并发加载同一模型
    if key not in _model_loading_lock:
        _model_loading_lock[key] = threading.Lock()
    
    with _model_loading_lock[key]:
        # 双重检查，可能在等待锁的过程中其他线程已经加载了模型
        if key in _cached_models:
            return _cached_models[key]
        
        model_type = "lite" if use_lite else "pro"
        if mode not in MODELS or model_type not in MODELS[mode]:
            raise HTTPException(status_code=500, detail=f"模型配置错误: {mode}")
        
        model_info = MODELS[mode][model_type]
        model_path = get_smart_path(model_info["folder"])
        if not model_path:
            raise HTTPException(status_code=404, detail=f"模型未找到: {model_info['folder']}")
        
        print(f"[模型加载] 开始加载模型: {key} ({model_path})")
        _cached_models[key] = load_model(model_path)
        print(f"[模型加载] 模型加载完成: {key}")
        return _cached_models[key]


def load_asr_model_cached(model_key: str = None):
    """加载并缓存 ASR 模型（仅从本地加载）"""
    import threading
    
    # 如果没有指定模型，使用默认模型
    if model_key is None:
        for key, config in ASR_MODELS.items():
            if config.get("default", False):
                model_key = key
                break
        if model_key is None:
            # 如果没有默认模型，使用第一个
            model_key = list(ASR_MODELS.keys())[0]
    
    if model_key not in ASR_MODELS:
        raise HTTPException(status_code=500, detail=f"ASR 模型配置错误: {model_key}")
    
    # 如果模型已缓存，直接返回
    if model_key in _cached_asr_models:
        return _cached_asr_models[model_key]
    
    # 使用锁防止并发加载同一模型
    if model_key not in _asr_model_loading_lock:
        _asr_model_loading_lock[model_key] = threading.Lock()
    
    with _asr_model_loading_lock[model_key]:
        # 双重检查
        if model_key in _cached_asr_models:
            return _cached_asr_models[model_key]
        
        model_info = ASR_MODELS[model_key]
        
        # 只从本地加载（参考 TTS 的实现方式）
        folder = model_info.get("folder")
        if not folder:
            raise HTTPException(status_code=404, detail=f"ASR 模型配置错误: 未找到本地文件夹配置")
        
        model_path = get_smart_path(folder)
        if not model_path:
            raise HTTPException(status_code=404, detail=f"ASR 模型未找到: {folder}，请确认模型已下载到 models/ 目录")
        
        print(f"[ASR模型加载] 从本地加载模型: {model_key} ({model_path})")
        try:
            # mlx-audio 0.3.2+ 已支持 qwen3_asr，直接加载即可
            _cached_asr_models[model_key] = load_stt_model(model_path)
            print(f"[ASR模型加载] 本地模型加载完成: {model_key}")
            return _cached_asr_models[model_key]
        except Exception as e:
            import traceback
            print(f"[ASR模型加载] 本地加载失败: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"ASR 模型加载失败: {str(e)}")


def cleanup_temp_files(*paths):
    """清理临时文件或目录"""
    for path in paths:
        if path and os.path.exists(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
            except Exception as e:
                print(f"[清理临时文件] 警告: 无法删除 {path}: {e}")


def cleanup_stt_temp_files(temp_output_dir: str):
    """清理 STT 临时文件（包括目录和可能直接创建的文件）"""
    if not temp_output_dir:
        return
    
    # 清理目录
    cleanup_temp_files(temp_output_dir)
    
    # 清理可能直接在当前目录创建的文件（generate_transcription 可能直接创建文件）
    # 检查当前目录下所有以 temp_output_dir 开头的文件
    base_name = os.path.basename(temp_output_dir)
    current_dir = os.getcwd()
    try:
        for filename in os.listdir(current_dir):
            if filename.startswith(base_name) and os.path.isfile(os.path.join(current_dir, filename)):
                cleanup_temp_files(os.path.join(current_dir, filename))
    except Exception as e:
        print(f"[清理STT临时文件] 警告: 无法列出目录 {current_dir}: {e}")


def convert_audio_if_needed(input_path: str) -> Optional[str]:
    """转换音频为 WAV 格式"""
    if not os.path.exists(input_path):
        return None

    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)

    if ext.lower() == ".wav":
        try:
            with wave.open(input_path, 'rb') as f:
                if f.getnchannels() > 0:
                    return input_path
        except wave.Error:
            pass

    temp_wav = os.path.join(os.getcwd(), f"temp_convert_{int(time.time())}.wav")
    
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", input_path,
           "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", temp_wav]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return temp_wav
    except (subprocess.CalledProcessError, FileNotFoundError):
        # 转换失败时清理临时文件
        cleanup_temp_files(temp_wav)
        return None


def save_audio_file(temp_folder: str, subfolder: str, text_snippet: str) -> str:
    """保存生成的音频文件"""
    save_path = os.path.join(BASE_OUTPUT_DIR, subfolder)
    os.makedirs(save_path, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_text = re.sub(r'[^\w\s-]', '', text_snippet)[:FILENAME_MAX_LEN].strip().replace(' ', '_') or "audio"
    filename = f"{timestamp}_{clean_text}.wav"
    final_path = os.path.join(save_path, filename)

    source_file = os.path.join(temp_folder, "audio_000.wav")

    if os.path.exists(source_file):
        shutil.move(source_file, final_path)

    # 清理临时目录
    cleanup_temp_files(temp_folder)

    # 返回相对路径（相对于 BASE_DIR）
    relative_path = os.path.relpath(final_path, BASE_DIR)
    return relative_path


def format_timestamp(seconds: float) -> str:
    """将秒数转换为 SRT 时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def save_stt_results(text: str, segments: List[dict], audio_filename: str) -> dict:
    """保存 STT 结果，生成 TXT 和 SRT 文件"""
    os.makedirs(STT_OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 从音频文件名提取基础名称
    base_name = os.path.splitext(os.path.basename(audio_filename))[0]
    base_name = re.sub(r'[^\w\s-]', '', base_name)[:FILENAME_MAX_LEN].strip().replace(' ', '_') or "audio"
    
    # 保存 TXT 文件（纯文本，无时间戳）
    txt_filename = f"{timestamp}_{base_name}.txt"
    txt_path = os.path.join(STT_OUTPUT_DIR, txt_filename)
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    # 保存 SRT 文件（带时间戳）
    srt_filename = f"{timestamp}_{base_name}.srt"
    srt_path = os.path.join(STT_OUTPUT_DIR, srt_filename)
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            start_time = format_timestamp(segment.get('start', 0))
            end_time = format_timestamp(segment.get('end', 0))
            segment_text = segment.get('text', '').strip()
            confidence = segment.get('confidence', 0)
            
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{segment_text}\n")
            if confidence > 0:
                f.write(f"[置信度: {confidence:.2%}]\n")
            f.write("\n")
    
    # 返回相对路径
    return {
        "txt_path": os.path.relpath(txt_path, BASE_DIR),
        "srt_path": os.path.relpath(srt_path, BASE_DIR)
    }


def get_history() -> List[dict]:
    """获取历史记录"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_history_item(item: dict):
    """保存历史记录"""
    history = get_history()
    history.insert(0, item)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_all_speakers() -> List[dict]:
    """获取所有音色"""
    speakers = []
    
    # 预设音色
    all_speakers_set = set()
    for lang, names in SPEAKER_MAP.items():
        for name in names:
            all_speakers_set.add(name)
    
    for name in sorted(all_speakers_set):
        languages = []
        for lang, names in SPEAKER_MAP.items():
            if name in names:
                languages.append(lang)
        speakers.append({
            "name": name,
            "type": "preset",
            "languages": languages,
            "is_multilingual": len(languages) > 1
        })
    
    # 克隆音色
    if os.path.exists(VOICES_DIR):
        for f in sorted(os.listdir(VOICES_DIR)):
            if f.endswith(".wav"):
                name = f.replace(".wav", "")
                txt_path = os.path.join(VOICES_DIR, f.replace(".wav", ".txt"))
                language = "Unknown"
                if os.path.exists(txt_path):
                    try:
                        with open(txt_path, 'r', encoding='utf-8') as tf:
                            content = tf.read()
                            # 简单判断语言
                            if any('\u4e00' <= c <= '\u9fff' for c in content):
                                language = "Chinese"
                            elif any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in content):
                                language = "Japanese"
                            elif any('\uac00' <= c <= '\ud7af' for c in content):
                                language = "Korean"
                            else:
                                language = "English"
                    except:
                        pass
                
                speakers.append({
                    "name": name,
                    "type": "cloned",
                    "languages": [language],
                    "is_multilingual": False
                })
    
    return speakers


# API 路由
@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/config")
async def get_config():
    """获取配置信息"""
    return {
        "emotions": EMOTION_OPTIONS,
        "speeds": SPEED_OPTIONS,
        "languages": LANGUAGE_OPTIONS,
    }


@app.get("/api/speakers")
async def get_speakers():
    """获取所有音色"""
    return {"speakers": get_all_speakers()}


@app.get("/api/models/status")
async def get_models_status():
    """获取模型加载状态"""
    status = {}
    for key in _cached_models.keys():
        mode, model_type = key.rsplit("_", 1)
        status[key] = {
            "mode": mode,
            "type": model_type,
            "loaded": True,
            "status": "已加载"
        }
    
    # 列出所有可能的模型配置
    all_models = {}
    for mode in MODELS.keys():
        for model_type in ["lite", "pro"]:
            if model_type in MODELS[mode]:
                key = f"{mode}_{model_type}"
                if key not in status:
                    all_models[key] = {
                        "mode": mode,
                        "type": model_type,
                        "loaded": False,
                        "status": "未加载"
                    }
    
    return {
        "loaded_models": status,
        "available_models": all_models,
        "total_loaded": len(status)
    }


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """文字转语音"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="文案不能为空")
    
    temp_dir = None
    try:
        model = load_model_cached("custom", request.use_lite)
        model_info = MODELS["custom"]["lite" if request.use_lite else "pro"]
        
        temp_dir = f"temp_{int(time.time())}"
        generate_audio(
            model=model,
            text=request.text,
            voice=request.speaker,
            instruct=request.emotion,
            speed=request.speed,
            output_path=temp_dir
        )
        
        audio_path = save_audio_file(temp_dir, model_info["output_subfolder"], request.text)
        temp_dir = None  # save_audio_file 已经清理了，标记为 None
        
        # 保存历史记录
        history_item = {
            "id": str(uuid.uuid4()),
            "text": request.text,
            "speaker": request.speaker,
            "emotion": request.emotion,
            "speed": request.speed,
            "audio_path": audio_path,
            "created_at": datetime.now().isoformat()
        }
        save_history_item(history_item)
        
        gc.collect()
        
        return {
            "success": True,
            "audio_path": audio_path,
            "history_id": history_item["id"]
        }
    except Exception as e:
        import traceback
        print(f"TTS Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        # 确保清理临时文件
        if temp_dir:
            cleanup_temp_files(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts/preview")
async def preview_voice(request: TTSRequest):
    """音色试听 - 不保存历史记录，音频自动删除"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="文案不能为空")
    
    temp_dir = None
    try:
        model = load_model_cached("custom", request.use_lite)
        
        temp_dir = f"temp_{int(time.time())}"
        generate_audio(
            model=model,
            text=request.text,
            voice=request.speaker,
            instruct=request.emotion,
            speed=request.speed,
            output_path=temp_dir
        )
        
        # 保存到临时目录，不放入 outputs
        temp_audio_dir = os.path.join(BASE_DIR, "temp_audio")
        os.makedirs(temp_audio_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"preview_{timestamp}.wav"
        audio_path = os.path.join(temp_audio_dir, audio_filename)
        
        source_file = os.path.join(temp_dir, "audio_000.wav")
        if os.path.exists(source_file):
            shutil.move(source_file, audio_path)
        
        # 清理临时目录
        cleanup_temp_files(temp_dir)
        temp_dir = None
        
        gc.collect()
        
        # 返回相对路径（相对于 BASE_DIR）
        relative_path = os.path.relpath(audio_path, BASE_DIR)
        
        return {
            "success": True,
            "audio_path": relative_path,
            "is_preview": True
        }
    except Exception as e:
        import traceback
        print(f"Preview Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        # 确保清理临时文件
        if temp_dir:
            cleanup_temp_files(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts/design")
async def design_voice(text: str = Form(...), description: str = Form(...), use_lite: bool = Form(False)):
    """音色设计"""
    if not text.strip() or not description.strip():
        raise HTTPException(status_code=400, detail="文案和描述不能为空")
    
    try:
        model = load_model_cached("design", use_lite)
        model_info = MODELS["design"]["lite" if use_lite else "pro"]
        
        temp_dir = f"temp_{int(time.time())}"
        generate_audio(
            model=model,
            text=text,
            instruct=description,
            output_path=temp_dir
        )
        
        audio_path = save_audio_file(temp_dir, model_info["output_subfolder"], text)
        
        # 保存历史记录
        history_item = {
            "id": str(uuid.uuid4()),
            "text": text,
            "speaker": f"设计音色: {description[:20]}",
            "emotion": description,
            "speed": 1.0,
            "audio_path": audio_path,
            "created_at": datetime.now().isoformat()
        }
        save_history_item(history_item)
        
        gc.collect()
        
        return {
            "success": True,
            "audio_path": audio_path,
            "history_id": history_item["id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clone")
async def clone_voice(
    name: str = Form(...),
    text: str = Form(...),
    language: str = Form("English"),
    audio: UploadFile = File(...)
):
    """克隆声音"""
    if not name.strip() or not text.strip():
        raise HTTPException(status_code=400, detail="名称和文案不能为空")
    
    safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')
    
    temp_input = None
    wav_path = None
    
    try:
        # 保存上传的音频
        temp_input = f"temp_upload_{int(time.time())}_{audio.filename}"
        with open(temp_input, "wb") as f:
            f.write(await audio.read())
        
        # 转换为 WAV
        wav_path = convert_audio_if_needed(temp_input)
        if not wav_path:
            cleanup_temp_files(temp_input)
            temp_input = None
            raise HTTPException(status_code=400, detail="音频转换失败")
        
        # 保存到 voices 目录
        os.makedirs(VOICES_DIR, exist_ok=True)
        target_wav = os.path.join(VOICES_DIR, f"{safe_name}.wav")
        target_txt = os.path.join(VOICES_DIR, f"{safe_name}.txt")
        
        shutil.copy(wav_path, target_wav)
        with open(target_txt, "w", encoding='utf-8') as f:
            f.write(text)
        
        # 清理临时文件
        cleanup_temp_files(temp_input, wav_path if wav_path != temp_input else None)
        temp_input = None
        wav_path = None
        
        return {
            "success": True,
            "name": safe_name,
            "message": f"音色 '{safe_name}' 克隆成功"
        }
    except HTTPException:
        # HTTPException 需要重新抛出，但也要清理临时文件
        cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        raise
    except Exception as e:
        import traceback
        print(f"Clone Voice Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        # 确保清理临时文件
        cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts/clone")
async def tts_with_cloned_voice(
    text: str = Form(...),
    voice_name: str = Form(...),
    use_lite: bool = Form(False),
    preview: bool = Form(False)
):
    """使用克隆音色生成语音"""
    if not text.strip():
        raise HTTPException(status_code=400, detail="文案不能为空")

    ref_audio = os.path.join(VOICES_DIR, f"{voice_name}.wav")
    ref_txt = os.path.join(VOICES_DIR, f"{voice_name}.txt")

    if not os.path.exists(ref_audio):
        raise HTTPException(status_code=404, detail=f"音色未找到: {voice_name}")

    ref_text = "."
    if os.path.exists(ref_txt):
        with open(ref_txt, 'r', encoding='utf-8') as f:
            ref_text = f.read().strip()

    temp_dir = None
    try:
        model = load_model_cached("clone", use_lite)

        temp_dir = f"temp_{int(time.time())}"
        generate_audio(
            model=model,
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,
            output_path=temp_dir
        )

        # 如果是试听模式，保存到临时目录，不保存历史记录
        if preview:
            temp_audio_dir = os.path.join(BASE_DIR, "temp_audio")
            os.makedirs(temp_audio_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"preview_clone_{timestamp}.wav"
            audio_path = os.path.join(temp_audio_dir, audio_filename)

            source_file = os.path.join(temp_dir, "audio_000.wav")
            if os.path.exists(source_file):
                shutil.move(source_file, audio_path)

            # 清理临时目录
            cleanup_temp_files(temp_dir)
            temp_dir = None

            gc.collect()

            # 返回相对路径（相对于 BASE_DIR）
            relative_path = os.path.relpath(audio_path, BASE_DIR)

            return {
                "success": True,
                "audio_path": relative_path,
                "is_preview": True
            }
        else:
            # 正常模式，保存到 outputs 并记录历史
            model_info = MODELS["clone"]["lite" if use_lite else "pro"]
            audio_path = save_audio_file(temp_dir, model_info["output_subfolder"], text)
            temp_dir = None  # save_audio_file 已经清理了，标记为 None

            # 保存历史记录
            history_item = {
                "id": str(uuid.uuid4()),
                "text": text,
                "speaker": f"克隆音色: {voice_name}",
                "emotion": "克隆",
                "speed": 1.0,
                "audio_path": audio_path,
                "created_at": datetime.now().isoformat()
            }
            save_history_item(history_item)

            gc.collect()

            return {
                "success": True,
                "audio_path": audio_path,
                "history_id": history_item["id"]
            }
    except Exception as e:
        import traceback
        print(f"Clone TTS Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        # 确保清理临时文件
        if temp_dir:
            cleanup_temp_files(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history_api():
    """获取生成历史（包括 TTS 和 STT）"""
    return {"history": get_history()}


@app.get("/api/history/stt")
async def get_stt_history_api():
    """获取 STT 历史记录"""
    history = get_history()
    stt_history = [item for item in history if item.get("type") == "stt"]
    return {"history": stt_history}


@app.delete("/api/history/{history_id}")
async def delete_history(history_id: str):
    """删除历史记录"""
    history = get_history()
    for item in history:
        if item["id"] == history_id:
            # 删除音频文件
            if os.path.exists(item["audio_path"]):
                os.remove(item["audio_path"])
            history.remove(item)
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            return {"success": True}
    raise HTTPException(status_code=404, detail="历史记录未找到")


@app.post("/api/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    model_key: str = Form(None)
):
    """语音转文字"""
    if not audio.filename:
        raise HTTPException(status_code=400, detail="请上传音频文件")
    
    temp_input = None
    wav_path = None
    temp_output_dir = None
    
    try:
        # 保存上传的音频到临时文件
        temp_input = f"temp_stt_{int(time.time())}_{audio.filename}"
        with open(temp_input, "wb") as f:
            content = await audio.read()
            f.write(content)
        
        # 转换为 WAV（如果需要）
        wav_path = convert_audio_if_needed(temp_input)
        if not wav_path:
            cleanup_temp_files(temp_input)
            temp_input = None
            raise HTTPException(status_code=400, detail="音频转换失败，请检查文件格式")
        
        # 如果创建了转换文件，可以立即删除原始上传文件（不再需要）
        if wav_path != temp_input:
            cleanup_temp_files(temp_input)
            temp_input = None  # 标记为已清理，避免重复清理
        
        # 加载 ASR 模型
        model = load_asr_model_cached(model_key)
        
        # 执行转录
        print(f"[STT] 开始转录: {wav_path}")
        # 使用临时输出文件，然后读取结果
        temp_output_dir = f"temp_stt_output_{int(time.time())}"
        os.makedirs(temp_output_dir, exist_ok=True)
        
        try:
            # generate_transcription 使用 audio 参数（不是 audio_path）
            # 返回的是 transcription 对象，有 .text 属性
            transcription = generate_transcription(
                model=model,
                audio=wav_path,  # 使用 audio 参数（音频文件路径）
                output_path=temp_output_dir,
                format="txt",  # 先保存为 txt
                verbose=True
            )
            
            # 从 transcription 对象获取文本
            text = ""
            language = "unknown"
            processed_segments = []
            
            # 获取完整文本
            if hasattr(transcription, 'text'):
                text = transcription.text
            elif isinstance(transcription, str):
                text = transcription
            else:
                # 尝试从输出文件读取
                output_file = os.path.join(temp_output_dir, "transcript.txt")
                if not os.path.exists(output_file):
                    output_file = os.path.join(temp_output_dir, "transcription.txt")
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        text = f.read().strip()
            
            # 获取分段信息
            if hasattr(transcription, 'segments'):
                segments = transcription.segments
            elif hasattr(transcription, 'chunks'):
                segments = transcription.chunks
            else:
                segments = []
            
            # 处理 segments
            if segments:
                for i, seg in enumerate(segments):
                    # 处理不同格式的 segment
                    if isinstance(seg, dict):
                        seg_text = seg.get("text", seg.get("words", ""))
                        seg_start = seg.get("start", seg.get("start_time", 0.0))
                        seg_end = seg.get("end", seg.get("end_time", 0.0))
                        seg_conf = seg.get("confidence", seg.get("score", 0.0))
                    elif hasattr(seg, '__dict__'):
                        seg_text = getattr(seg, 'text', getattr(seg, 'words', ''))
                        seg_start = getattr(seg, 'start', getattr(seg, 'start_time', 0.0))
                        seg_end = getattr(seg, 'end', getattr(seg, 'end_time', 0.0))
                        seg_conf = getattr(seg, 'confidence', getattr(seg, 'score', 0.0))
                    else:
                        seg_text = str(seg)
                        seg_start = 0.0
                        seg_end = 0.0
                        seg_conf = 0.0
                    
                    processed_segments.append({
                        "id": i,
                        "start": float(seg_start),
                        "end": float(seg_end),
                        "text": seg_text,
                        "confidence": float(seg_conf)
                    })
                
                # 尝试从第一个 segment 获取语言信息
                if processed_segments and isinstance(segments[0], dict):
                    language = segments[0].get("language", "unknown")
                elif processed_segments and hasattr(segments[0], 'language'):
                    language = getattr(segments[0], 'language', 'unknown')
            
            # 尝试从 transcription 对象获取语言
            if language == "unknown" and hasattr(transcription, 'language'):
                language = transcription.language
        finally:
            # 清理临时输出目录和可能直接创建的文件
            cleanup_stt_temp_files(temp_output_dir)
            temp_output_dir = None
        
        # 如果没有分段信息，尝试从文本创建基本分段
        if not processed_segments and text:
            # 简单分段：按句号、问号、感叹号分割
            sentences = re.split(r'[。！？.!?]', text)
            current_time = 0.0
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    # 估算每句话的时间（假设每分钟150字）
                    duration = len(sentence) / 25.0  # 约25字/秒
                    processed_segments.append({
                        "id": i,
                        "start": current_time,
                        "end": current_time + duration,
                        "text": sentence.strip(),
                        "confidence": 0.0
                    })
                    current_time += duration
        
        # 保存结果文件
        file_paths = save_stt_results(text, processed_segments, audio.filename)
        
        # 保存历史记录
        history_item = {
            "id": str(uuid.uuid4()),
            "type": "stt",
            "audio_filename": audio.filename,
            "text": text,
            "language": language,
            "segments": processed_segments,
            "txt_path": file_paths["txt_path"],
            "srt_path": file_paths["srt_path"],
            "created_at": datetime.now().isoformat()
        }
        save_history_item(history_item)
        
        # 清理临时文件
        cleanup_temp_files(temp_input, wav_path if wav_path != temp_input else None)
        temp_input = None
        wav_path = None
        
        gc.collect()
        
        return {
            "success": True,
            "text": text,
            "language": language,
            "segments": processed_segments,
            "txt_path": file_paths["txt_path"],
            "srt_path": file_paths["srt_path"],
            "history_id": history_item["id"]
        }
    except HTTPException:
        # HTTPException 需要重新抛出，但也要清理临时文件
        cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        cleanup_stt_temp_files(temp_output_dir)
        raise
    except Exception as e:
        import traceback
        print(f"STT Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        # 确保清理所有临时文件
        cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        cleanup_stt_temp_files(temp_output_dir)
        raise HTTPException(status_code=500, detail=f"语音转文字失败: {str(e)}")


@app.delete("/api/voices/{voice_name}")
async def delete_cloned_voice(voice_name: str):
    """删除克隆音色"""
    wav_path = os.path.join(VOICES_DIR, f"{voice_name}.wav")
    txt_path = os.path.join(VOICES_DIR, f"{voice_name}.txt")
    
    deleted = False
    if os.path.exists(wav_path):
        os.remove(wav_path)
        deleted = True
    if os.path.exists(txt_path):
        os.remove(txt_path)
        deleted = True
    
    if deleted:
        return {"success": True, "message": f"音色 '{voice_name}' 已删除"}
    else:
        raise HTTPException(status_code=404, detail="音色未找到")


@app.get("/api/audio/{path:path}")
async def serve_audio(path: str):
    """提供音频文件"""
    # 支持绝对路径和相对路径
    if path.startswith('/'):
        full_path = path
    else:
        full_path = os.path.join(BASE_DIR, path)

    if os.path.exists(full_path) and full_path.endswith('.wav'):
        return FileResponse(full_path, media_type="audio/wav")
    raise HTTPException(status_code=404, detail="音频文件未找到")


@app.get("/api/file/{path:path}")
async def serve_file(path: str):
    """提供文件下载（TXT、SRT 等）"""
    # 支持绝对路径和相对路径
    if path.startswith('/'):
        full_path = path
    else:
        full_path = os.path.join(BASE_DIR, path)

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件未找到")
    
    # 根据文件扩展名设置媒体类型
    ext = os.path.splitext(full_path)[1].lower()
    media_types = {
        '.txt': 'text/plain',
        '.srt': 'text/srt',
        '.vtt': 'text/vtt',
        '.json': 'application/json'
    }
    media_type = media_types.get(ext, 'application/octet-stream')
    
    return FileResponse(full_path, media_type=media_type)


@app.delete("/api/audio/cleanup")
async def cleanup_temp_audio():
    """清理临时音频文件"""
    temp_audio_dir = os.path.join(BASE_DIR, "temp_audio")
    if os.path.exists(temp_audio_dir):
        # 删除所有预览音频文件
        for f in os.listdir(temp_audio_dir):
            if f.startswith('preview_') and f.endswith('.wav'):
                try:
                    os.remove(os.path.join(temp_audio_dir, f))
                except:
                    pass
    return {"success": True}


# HTML 模板函数
def get_html_template():
    """获取 HTML 模板"""
    return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Qwen3-TTS Web</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎙️</text></svg>">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #111827;
            color: #fff;
            min-height: 100vh;
        }
        
        .container {
            display: flex;
            min-height: 100vh;
        }
        
        /* 侧边栏 */
        .sidebar {
            width: 260px;
            background-color: #1f2937;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #374151;
        }
        
        .sidebar-header {
            padding: 24px;
            border-bottom: 1px solid #374151;
        }
        
        .sidebar-header h1 {
            font-size: 20px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .sidebar-header p {
            font-size: 13px;
            color: #9ca3af;
            margin-top: 4px;
        }
        
        .nav-menu {
            flex: 1;
            padding: 16px 12px;
        }
        
        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            margin-bottom: 4px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            color: #d1d5db;
            text-decoration: none;
        }
        
        .nav-item:hover {
            background-color: #374151;
            color: #fff;
        }
        
        .nav-item.active {
            background-color: #2563eb;
            color: #fff;
        }
        
        .nav-item i {
            width: 24px;
            text-align: center;
        }
        
        .sidebar-footer {
            padding: 16px;
            border-top: 1px solid #374151;
            font-size: 12px;
            color: #9ca3af;
        }
        
        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: #22c55e;
            border-radius: 50%;
            margin-right: 6px;
        }
        
        /* 主内容区 */
        .main-content {
            flex: 1;
            padding: 32px;
            overflow-y: auto;
        }
        
        .page-title {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 24px;
        }
        
        /* 卡片样式 */
        .card {
            background-color: #1f2937;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        
        .card-title {
            font-size: 14px;
            font-weight: 600;
            color: #e5e7eb;
            margin-bottom: 12px;
        }
        
        /* 表单元素 */
        .form-label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: #e5e7eb;
            margin-bottom: 8px;
        }
        
        .form-textarea {
            width: 100%;
            background-color: #374151;
            border: 1px solid #4b5563;
            border-radius: 8px;
            padding: 12px;
            color: #fff;
            font-size: 14px;
            resize: vertical;
            min-height: 120px;
        }
        
        .form-textarea:focus {
            outline: none;
            border-color: #2563eb;
        }
        
        .form-select {
            width: 100%;
            background-color: #374151;
            border: 1px solid #4b5563;
            border-radius: 8px;
            padding: 10px 12px;
            color: #fff;
            font-size: 14px;
            cursor: pointer;
        }
        
        .form-select:focus {
            outline: none;
            border-color: #2563eb;
        }
        
        .form-input {
            width: 100%;
            background-color: #374151;
            border: 1px solid #4b5563;
            border-radius: 8px;
            padding: 10px 12px;
            color: #fff;
            font-size: 14px;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #2563eb;
        }
        
        /* 按钮 */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }
        
        .btn-primary {
            background-color: #2563eb;
            color: #fff;
        }
        
        .btn-primary:hover {
            background-color: #1d4ed8;
        }
        
        .btn-secondary {
            background-color: #4b5563;
            color: #fff;
        }
        
        .btn-secondary:hover {
            background-color: #6b7280;
        }
        
        .btn-danger {
            background-color: #dc2626;
            color: #fff;
        }
        
        .btn-danger:hover {
            background-color: #b91c1c;
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        /* 音色卡片 */
        .speaker-sections-container {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .speaker-section {
            display: flex;
            flex-direction: column;
        }

        .speaker-section-title {
            font-size: 14px;
            color: #9ca3af;
            margin-bottom: 12px;
        }

        .speaker-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            width: 100%;
        }
        
        .speaker-card {
            background-color: #374151;
            border-radius: 10px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s;
            border: 2px solid transparent;
            flex: 0 0 auto;
            min-width: 160px;
            max-width: 100%;
        }
        
        .speaker-card:hover {
            background-color: #4b5563;
        }
        
        .speaker-card.selected {
            border-color: #2563eb;
            background-color: #4b5563;
        }
        
        .speaker-name {
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .speaker-langs {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }
        
        .lang-tag {
            font-size: 11px;
            background-color: #1f2937;
            padding: 2px 8px;
            border-radius: 4px;
        }
        
        /* 拖拽上传 */
        .drop-zone {
            border: 2px dashed #4b5563;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .drop-zone:hover {
            border-color: #2563eb;
            background-color: #374151;
        }
        
        .drop-zone.dragover {
            border-color: #2563eb;
            background-color: #374151;
        }
        
        /* 历史记录 */
        .history-item {
            background-color: #1f2937;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }
        
        .history-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }
        
        .history-text {
            color: #d1d5db;
            line-height: 1.5;
            flex: 1;
        }
        
        .history-meta {
            display: flex;
            gap: 16px;
            font-size: 13px;
            color: #9ca3af;
            margin-top: 8px;
        }
        
        /* 音频播放器 */
        audio {
            width: 100%;
            margin-top: 12px;
        }
        
        /* 加载动画 */
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #fff;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* 隐藏元素 */
        .hidden {
            display: none !important;
        }
        
        /* 成功提示 */
        .success-message {
            background-color: rgba(34, 197, 94, 0.1);
            border: 1px solid #22c55e;
            border-radius: 8px;
            padding: 16px;
            color: #22c55e;
        }
        
        /* 网格布局 */
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }
        
        @media (max-width: 768px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
            
            .sidebar {
                width: 200px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 侧边栏 -->
        <aside class="sidebar">
            <div class="sidebar-header">
                <h1>
                    <i class="fas fa-wave-square" style="color: #3b82f6;"></i>
                    Qwen3-TTS
                </h1>
                <p>本地语音合成</p>
            </div>
            
            <nav class="nav-menu">
                <a href="/tts" class="nav-item {{ 'active' if page == 'tts' else '' }}">
                    <i class="fas fa-microphone-lines"></i>
                    <span>文字转语音</span>
                </a>
                <a href="/stt" class="nav-item {{ 'active' if page == 'stt' else '' }}">
                    <i class="fas fa-language"></i>
                    <span>语音转文字</span>
                </a>
                <a href="/speakers" class="nav-item {{ 'active' if page == 'speakers' else '' }}">
                    <i class="fas fa-users"></i>
                    <span>音色库</span>
                </a>
                <a href="/clone" class="nav-item {{ 'active' if page == 'clone' else '' }}">
                    <i class="fas fa-copy"></i>
                    <span>克隆声音</span>
                </a>
                <a href="/history" class="nav-item {{ 'active' if page == 'history' else '' }}">
                    <i class="fas fa-clock-rotate-left"></i>
                    <span>生成历史</span>
                </a>
            </nav>
            
            <div class="sidebar-footer">
                <p><span class="status-dot"></span>模型就绪</p>
                <p style="margin-top: 4px;">Apple Silicon 优化</p>
            </div>
        </aside>

        <!-- 主内容 -->
        <main class="main-content">
            {{ content | safe }}
        </main>
    </div>
    
    <script src="/static/js/app.js?v=13"></script>
</body>
</html>
'''


# 页面内容生成函数
def get_tts_page():
    return '''
<h1 class="page-title">文字转语音</h1>

<div style="max-width: 800px;">
    <!-- 文案输入 -->
    <div class="card">
        <label class="form-label">输入文案</label>
        <textarea id="tts-text" class="form-textarea" placeholder="请输入要转换为语音的文案..."></textarea>
        <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 13px; color: #9ca3af;">
            <span>支持中文、英文、日文、韩文</span>
            <span id="text-count">0 字</span>
        </div>
    </div>

    <!-- 音色选择 -->
    <div class="card">
        <label class="form-label">选择音色</label>
        <div class="speaker-sections-container" id="speaker-grid">
            <!-- 动态加载 -->
        </div>
    </div>

    <!-- 参数设置 -->
    <div class="card">
        <div class="grid-2">
            <div>
                <label class="form-label">语气</label>
                <select id="tts-emotion" class="form-select">
                    <option value="Normal tone">正常 - 标准语调</option>
                    <option value="Sad and crying, speaking slowly">悲伤哭泣 - 语速较慢</option>
                    <option value="Excited and happy, speaking very fast">兴奋开心 - 语速很快</option>
                    <option value="Angry and shouting">愤怒大喊</option>
                    <option value="Whispering quietly">轻声耳语</option>
                </select>
            </div>
            <div>
                <label class="form-label">语速</label>
                <select id="tts-speed" class="form-select">
                    <option value="0.8">慢速 (0.8x)</option>
                    <option value="1.0" selected>正常 (1.0x)</option>
                    <option value="1.3">快速 (1.3x)</option>
                </select>
            </div>
        </div>
        <label style="display: flex; align-items: center; gap: 8px; margin-top: 16px; cursor: pointer;">
            <input type="checkbox" id="tts-lite" style="width: 16px; height: 16px;" checked>
            <span style="font-size: 14px; color: #d1d5db;">使用 Lite 模型（更快，质量稍低）</span>
        </label>
    </div>

    <!-- 按钮 -->
    <div style="display: flex; gap: 12px; margin-bottom: 20px;">
        <button class="btn btn-primary" id="btn-generate" onclick="generateTTS()">
            <i class="fas fa-play"></i>
            <span>生成语音</span>
        </button>
        <button class="btn btn-secondary" id="btn-preview" onclick="previewSpeaker()">
            <i class="fas fa-headphones"></i>
            <span>试听音色</span>
        </button>
    </div>

    <!-- 结果 -->
    <div id="tts-result" class="card hidden">
        <label class="form-label">生成结果</label>
        <audio id="tts-audio" controls></audio>
        <div style="margin-top: 12px;">
            <a id="tts-download" href="#" download class="btn btn-secondary" style="text-decoration: none;">
                <i class="fas fa-download"></i>
                <span>下载</span>
            </a>
        </div>
    </div>
</div>
'''


def get_speakers_page():
    return '''
<h1 class="page-title">音色库</h1>

<!-- 预设音色 -->
<div class="card">
    <h2 style="font-size: 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-star" style="color: #eab308;"></i>
        预设音色
    </h2>
    <div class="speaker-grid" id="preset-speakers">
        <!-- 动态加载 -->
    </div>
</div>

<!-- 克隆音色 -->
<div class="card">
    <h2 style="font-size: 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
        <i class="fas fa-copy" style="color: #22c55e;"></i>
        克隆音色
    </h2>
    <div class="speaker-grid" id="cloned-speakers">
        <!-- 动态加载 -->
    </div>
    <p id="no-cloned" class="hidden" style="text-align: center; color: #9ca3af; padding: 40px;">
        暂无克隆音色，请先克隆声音
    </p>
</div>
'''


def get_clone_page():
    return '''
<h1 class="page-title">克隆声音</h1>

<div style="max-width: 600px;">
    <!-- 音频上传 -->
    <div class="card">
        <label class="form-label">上传参考音频</label>
        <div class="drop-zone" id="drop-zone">
            <i class="fas fa-cloud-upload-alt" style="font-size: 48px; color: #6b7280; margin-bottom: 16px;"></i>
            <p style="color: #d1d5db; margin-bottom: 8px;">拖拽音频文件到此处，或点击上传</p>
            <p style="font-size: 13px; color: #6b7280;">支持 MP3, WAV, M4A 等格式</p>
            <input type="file" id="clone-audio" accept="audio/*" style="display: none;">
        </div>
        <p id="file-name" class="hidden" style="margin-top: 12px; color: #22c55e; font-size: 14px;"></p>
    </div>

    <!-- 音色名称 -->
    <div class="card">
        <label class="form-label">音色名称</label>
        <input type="text" id="clone-name" class="form-input" placeholder="例如：我的声音、老板的声音">
    </div>

    <!-- 参考文案 -->
    <div class="card">
        <label class="form-label">参考文案</label>
        <p style="font-size: 13px; color: #9ca3af; margin-bottom: 12px;">输入音频中说的准确内容（对克隆质量很重要）</p>
        <textarea id="clone-text" class="form-textarea" rows="3" placeholder="请输入音频中的文案..."></textarea>
    </div>

    <!-- 语言选择 -->
    <div class="card">
        <label class="form-label">语言类型</label>
        <select id="clone-language" class="form-select">
            <option value="English">英语</option>
            <option value="Chinese">中文</option>
            <option value="Japanese">日语</option>
            <option value="Korean">韩语</option>
        </select>
    </div>

    <!-- 克隆按钮 -->
    <button class="btn btn-primary" id="btn-clone" onclick="cloneVoice()" style="width: 100%; justify-content: center;">
        <i class="fas fa-copy"></i>
        <span>开始克隆</span>
    </button>

    <!-- 结果 -->
    <div id="clone-result" class="success-message hidden" style="margin-top: 20px;">
        <i class="fas fa-check-circle"></i>
        <span id="clone-message"></span>
    </div>
</div>
'''


def get_stt_page():
    return '''
<h1 class="page-title">语音转文字</h1>

<div style="max-width: 800px;">
    <!-- 音频上传 -->
    <div class="card">
        <label class="form-label">上传音频文件</label>
        <div class="drop-zone" id="stt-drop-zone">
            <i class="fas fa-cloud-upload-alt" style="font-size: 48px; color: #6b7280; margin-bottom: 16px;"></i>
            <p style="color: #d1d5db; margin-bottom: 8px;">拖拽音频文件到此处，或点击上传</p>
            <p style="font-size: 13px; color: #6b7280;">支持 MP3, WAV, M4A, FLAC 等格式</p>
            <input type="file" id="stt-audio" accept="audio/*" style="display: none;">
        </div>
        <p id="stt-file-name" class="hidden" style="margin-top: 12px; color: #22c55e; font-size: 14px;"></p>
    </div>

    <!-- 按钮 -->
    <div style="display: flex; gap: 12px; margin-bottom: 20px;">
        <button class="btn btn-primary" id="btn-stt-generate" onclick="generateSTT()">
            <i class="fas fa-microphone-lines"></i>
            <span>开始识别</span>
        </button>
        <button class="btn btn-secondary" id="btn-stt-retry" onclick="retrySTT()" style="display: none;">
            <i class="fas fa-redo"></i>
            <span>重试</span>
        </button>
    </div>

    <!-- 结果 -->
    <div id="stt-result" class="card hidden">
        <label class="form-label">识别结果</label>
        
        <!-- 文本预览 -->
        <div style="background-color: #374151; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 13px; color: #9ca3af;">识别文本</span>
                <span id="stt-language" style="font-size: 12px; color: #22c55e;"></span>
            </div>
            <div id="stt-text" style="color: #d1d5db; line-height: 1.6; white-space: pre-wrap; max-height: 300px; overflow-y: auto;"></div>
        </div>

        <!-- 分段信息 -->
        <div id="stt-segments" style="margin-bottom: 16px;"></div>

        <!-- 下载按钮 -->
        <div style="display: flex; gap: 12px;">
            <a id="stt-download-txt" href="#" download class="btn btn-secondary" style="text-decoration: none;">
                <i class="fas fa-file-alt"></i>
                <span>下载 TXT</span>
            </a>
            <a id="stt-download-srt" href="#" download class="btn btn-secondary" style="text-decoration: none;">
                <i class="fas fa-file-video"></i>
                <span>下载 SRT</span>
            </a>
            <button class="btn btn-primary" id="btn-stt-to-clone" onclick="sendToClone()" style="display: none;">
                <i class="fas fa-copy"></i>
                <span>用于克隆音色</span>
            </button>
        </div>
    </div>

    <!-- 错误信息 -->
    <div id="stt-error" class="card hidden" style="background-color: rgba(220, 38, 38, 0.1); border: 1px solid #dc2626;">
        <div style="color: #dc2626;">
            <i class="fas fa-exclamation-circle"></i>
            <span id="stt-error-message"></span>
        </div>
    </div>
</div>
'''


def get_history_page():
    return '''
<h1 class="page-title">生成历史</h1>

<div id="history-list">
    <!-- 动态加载 -->
</div>

<p id="no-history" class="hidden" style="text-align: center; color: #9ca3af; padding: 60px;">
    <i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 16px; display: block;"></i>
    暂无生成记录
</p>

'''


# 页面路由
@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径重定向到 TTS 页面"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/tts")


@app.get("/tts", response_class=HTMLResponse)
async def tts_page():
    """文字转语音页面"""
    template = get_html_template()
    content = template.replace('{{ content | safe }}', get_tts_page())
    content = content.replace("{{ 'active' if page == 'tts' else '' }}", "active")
    content = content.replace("{{ 'active' if page == 'speakers' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'clone' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'history' else '' }}", "")
    return content


@app.get("/speakers", response_class=HTMLResponse)
async def speakers_page():
    """音色库页面"""
    template = get_html_template()
    content = template.replace('{{ content | safe }}', get_speakers_page())
    content = content.replace("{{ 'active' if page == 'tts' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'stt' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'speakers' else '' }}", "active")
    content = content.replace("{{ 'active' if page == 'clone' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'history' else '' }}", "")
    return content


@app.get("/clone", response_class=HTMLResponse)
async def clone_page():
    """克隆声音页面"""
    template = get_html_template()
    content = template.replace('{{ content | safe }}', get_clone_page())
    content = content.replace("{{ 'active' if page == 'tts' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'stt' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'speakers' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'clone' else '' }}", "active")
    content = content.replace("{{ 'active' if page == 'history' else '' }}", "")
    return content


@app.get("/stt", response_class=HTMLResponse)
async def stt_page():
    """语音转文字页面"""
    template = get_html_template()
    content = template.replace('{{ content | safe }}', get_stt_page())
    content = content.replace("{{ 'active' if page == 'tts' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'stt' else '' }}", "active")
    content = content.replace("{{ 'active' if page == 'speakers' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'clone' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'history' else '' }}", "")
    return content


@app.get("/history", response_class=HTMLResponse)
async def history_page():
    """生成历史页面"""
    template = get_html_template()
    content = template.replace('{{ content | safe }}', get_history_page())
    content = content.replace("{{ 'active' if page == 'tts' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'stt' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'speakers' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'clone' else '' }}", "")
    content = content.replace("{{ 'active' if page == 'history' else '' }}", "active")
    return content


# 挂载静态文件
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")




if __name__ == "__main__":
    import uvicorn
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(VOICES_DIR, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8766)
