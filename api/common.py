"""
通用 API 路由
"""
from fastapi import APIRouter
from datetime import datetime
from config import EMOTION_OPTIONS, SPEED_OPTIONS, LANGUAGE_OPTIONS
from models import get_models_status
from history import get_all_speakers

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@router.get("/config")
async def get_config():
    """获取配置信息"""
    return {
        "emotions": EMOTION_OPTIONS,
        "speeds": SPEED_OPTIONS,
        "languages": LANGUAGE_OPTIONS,
    }


@router.get("/speakers")
async def get_speakers():
    """获取所有音色"""
    return {"speakers": get_all_speakers()}


@router.get("/models/status")
async def get_models_status_api():
    """获取模型加载状态"""
    return get_models_status()

