"""
克隆音色 API 路由
"""
import os
import re
import gc
import time
import uuid
import shutil
import traceback
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from mlx_audio.tts.generate import generate_audio
from config import BASE_DIR, VOICES_DIR, MODELS
from models import load_model_cached
from utils import cleanup_temp_files, convert_audio_if_needed, save_audio_file
from history import save_history_item

router = APIRouter()


@router.post("/clone")
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
        temp_input = f"temp_upload_{int(time.time())}_{audio.filename}"
        with open(temp_input, "wb") as f:
            f.write(await audio.read())
        
        wav_path = convert_audio_if_needed(temp_input)
        if not wav_path:
            cleanup_temp_files(temp_input)
            temp_input = None
            raise HTTPException(status_code=400, detail="音频转换失败")
        
        os.makedirs(VOICES_DIR, exist_ok=True)
        target_wav = os.path.join(VOICES_DIR, f"{safe_name}.wav")
        target_txt = os.path.join(VOICES_DIR, f"{safe_name}.txt")
        
        shutil.copy(wav_path, target_wav)
        with open(target_txt, "w", encoding='utf-8') as f:
            f.write(text)
        
        cleanup_temp_files(temp_input, wav_path if wav_path != temp_input else None)
        temp_input = None
        wav_path = None
        
        return {
            "success": True,
            "name": safe_name,
            "message": f"音色 '{safe_name}' 克隆成功"
        }
    except HTTPException:
        cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        raise
    except Exception as e:
        print(f"Clone Voice Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts/clone")
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

        if preview:
            temp_audio_dir = os.path.join(BASE_DIR, "temp_audio")
            os.makedirs(temp_audio_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"preview_clone_{timestamp}.wav"
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
        else:
            model_info = MODELS["clone"]["lite" if use_lite else "pro"]
            audio_path = save_audio_file(temp_dir, model_info["output_subfolder"], text)
            temp_dir = None

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
        print(f"Clone TTS Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        if temp_dir:
            cleanup_temp_files(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/voices/{voice_name}")
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

