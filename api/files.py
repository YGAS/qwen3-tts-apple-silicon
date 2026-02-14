"""
文件服务 API 路由
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from config import BASE_DIR

router = APIRouter()


@router.get("/audio/{path:path}")
async def serve_audio(path: str):
    """提供音频文件"""
    if path.startswith('/'):
        full_path = path
    else:
        full_path = os.path.join(BASE_DIR, path)

    if os.path.exists(full_path) and full_path.endswith('.wav'):
        return FileResponse(full_path, media_type="audio/wav")
    raise HTTPException(status_code=404, detail="音频文件未找到")


@router.get("/file/{path:path}")
async def serve_file(path: str):
    """提供文件下载（TXT、SRT 等）"""
    if path.startswith('/'):
        full_path = path
    else:
        full_path = os.path.join(BASE_DIR, path)

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件未找到")
    
    ext = os.path.splitext(full_path)[1].lower()
    media_types = {
        '.txt': 'text/plain',
        '.srt': 'text/srt',
        '.vtt': 'text/vtt',
        '.json': 'application/json'
    }
    media_type = media_types.get(ext, 'application/octet-stream')
    
    return FileResponse(full_path, media_type=media_type)


@router.delete("/audio/cleanup")
async def cleanup_temp_audio():
    """清理临时音频文件"""
    temp_audio_dir = os.path.join(BASE_DIR, "temp_audio")
    if os.path.exists(temp_audio_dir):
        for f in os.listdir(temp_audio_dir):
            if f.startswith('preview_') and f.endswith('.wav'):
                try:
                    os.remove(os.path.join(temp_audio_dir, f))
                except:
                    pass
    return {"success": True}

