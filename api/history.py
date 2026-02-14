"""
历史记录 API 路由
"""
import os
import json
from fastapi import APIRouter, HTTPException
from config import BASE_DIR
from history import get_history, HISTORY_FILE

router = APIRouter()


@router.get("/history")
async def get_history_api():
    """获取生成历史（包括 TTS 和 STT）"""
    return {"history": get_history()}


@router.get("/history/stt")
async def get_stt_history_api():
    """获取 STT 历史记录"""
    history = get_history()
    stt_history = [item for item in history if item.get("type") == "stt"]
    return {"history": stt_history}


@router.delete("/history/{history_id}")
async def delete_history(history_id: str):
    """删除历史记录"""
    history = get_history()
    for item in history:
        if item["id"] == history_id:
            if "audio_path" in item:
                audio_path = os.path.join(BASE_DIR, item["audio_path"]) if not item["audio_path"].startswith('/') else item["audio_path"]
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            if "txt_path" in item:
                txt_path = os.path.join(BASE_DIR, item["txt_path"]) if not item["txt_path"].startswith('/') else item["txt_path"]
                if os.path.exists(txt_path):
                    os.remove(txt_path)
            if "srt_path" in item:
                srt_path = os.path.join(BASE_DIR, item["srt_path"]) if not item["srt_path"].startswith('/') else item["srt_path"]
                if os.path.exists(srt_path):
                    os.remove(srt_path)
            history.remove(item)
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            return {"success": True}
    raise HTTPException(status_code=404, detail="历史记录未找到")

