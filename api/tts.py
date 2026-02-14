"""
TTS API 路由
"""
import os
import gc
import time
import uuid
import shutil
import traceback
from datetime import datetime
from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from mlx_audio.tts.generate import generate_audio
from config import BASE_DIR, MODELS
from models import load_model_cached
from utils import cleanup_temp_files, save_audio_file
from history import save_history_item

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    speaker: str
    emotion: str = "Normal tone"
    speed: float = 1.0
    use_lite: bool = False


@router.post("/tts")
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
        temp_dir = None
        
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
        print(f"TTS Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        if temp_dir:
            cleanup_temp_files(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts/preview")
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
        
        temp_audio_dir = os.path.join(BASE_DIR, "temp_audio")
        os.makedirs(temp_audio_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"preview_{timestamp}.wav"
        audio_path = os.path.join(temp_audio_dir, audio_filename)
        
        source_file = os.path.join(temp_dir, "audio_000.wav")
        if os.path.exists(source_file):
            shutil.move(source_file, audio_path)
        
        cleanup_temp_files(temp_dir)
        temp_dir = None
        
        gc.collect()
        
        relative_path = os.path.relpath(audio_path, BASE_DIR)
        
        return {
            "success": True,
            "audio_path": relative_path,
            "is_preview": True
        }
    except Exception as e:
        print(f"Preview Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        if temp_dir:
            cleanup_temp_files(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts/design")
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

