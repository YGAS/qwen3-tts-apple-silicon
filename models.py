"""
模型加载和缓存管理
"""
import threading
from fastapi import HTTPException
from mlx_audio.tts.utils import load_model
from mlx_audio.stt.utils import load_model as load_stt_model
from config import MODELS, ASR_MODELS
from utils import get_smart_path

# 缓存的模型
_cached_models = {}
_cached_asr_models = {}
_model_loading_lock = {}
_asr_model_loading_lock = {}


def load_model_cached(mode: str, use_lite: bool = False):
    """加载并缓存 TTS 模型"""
    key = f"{mode}_{'lite' if use_lite else 'pro'}"
    
    if key in _cached_models:
        return _cached_models[key]
    
    if key not in _model_loading_lock:
        _model_loading_lock[key] = threading.Lock()
    
    with _model_loading_lock[key]:
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
    """加载并缓存 ASR 模型"""
    if model_key is None:
        for key, config in ASR_MODELS.items():
            if config.get("default", False):
                model_key = key
                break
        if model_key is None:
            model_key = list(ASR_MODELS.keys())[0]
    
    if model_key not in ASR_MODELS:
        raise HTTPException(status_code=500, detail=f"ASR 模型配置错误: {model_key}")
    
    if model_key in _cached_asr_models:
        return _cached_asr_models[model_key]
    
    if model_key not in _asr_model_loading_lock:
        _asr_model_loading_lock[model_key] = threading.Lock()
    
    with _asr_model_loading_lock[model_key]:
        if model_key in _cached_asr_models:
            return _cached_asr_models[model_key]
        
        model_info = ASR_MODELS[model_key]
        folder = model_info.get("folder")
        if not folder:
            raise HTTPException(status_code=404, detail=f"ASR 模型配置错误: 未找到本地文件夹配置")
        
        model_path = get_smart_path(folder)
        if not model_path:
            raise HTTPException(status_code=404, detail=f"ASR 模型未找到: {folder}，请确认模型已下载到 models/ 目录")
        
        print(f"[ASR模型加载] 从本地加载模型: {model_key} ({model_path})")
        try:
            _cached_asr_models[model_key] = load_stt_model(model_path)
            print(f"[ASR模型加载] 本地模型加载完成: {model_key}")
            return _cached_asr_models[model_key]
        except Exception as e:
            import traceback
            print(f"[ASR模型加载] 本地加载失败: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"ASR 模型加载失败: {str(e)}")


def get_models_status():
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

