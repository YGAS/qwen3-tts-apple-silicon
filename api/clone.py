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
from config import BASE_DIR, VOICES_DIR, MODELS, TMP_DIR
from models import load_model_cached
from utils import cleanup_temp_files, convert_audio_if_needed, save_audio_file, get_temp_path
from history import save_history_item

router = APIRouter()


@router.post("/clone")
async def clone_voice(
    name: str = Form(...),
    text: str = Form(...),
    language: str = Form("English"),
    audio: UploadFile = File(None),
    audio_path: str = Form(None)
):
    """克隆声音"""
    if not name.strip() or not text.strip():
        raise HTTPException(status_code=400, detail="名称和文案不能为空")
    
    safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')
    
    temp_input = None
    wav_path = None
    
    try:
        # 优先使用 audio_path，如果没有则使用上传的文件
        if audio_path:
            # 使用提供的文件路径
            full_audio_path = os.path.join(BASE_DIR, audio_path) if not os.path.isabs(audio_path) else audio_path
            if not os.path.exists(full_audio_path):
                raise HTTPException(status_code=404, detail=f"音频文件未找到: {audio_path}")
            
            # 转换为 WAV
            wav_path = convert_audio_if_needed(full_audio_path)
            if not wav_path:
                raise HTTPException(status_code=400, detail="音频转换失败")
        elif audio:
            # 保存上传的音频到 tmp 目录
            safe_filename = re.sub(r'[^\w\s.-]', '', audio.filename).strip()
            temp_input = get_temp_path("temp_upload", safe_filename)
            with open(temp_input, "wb") as f:
                f.write(await audio.read())
            
            # 转换为 WAV
            wav_path = convert_audio_if_needed(temp_input)
            if not wav_path:
                cleanup_temp_files(temp_input)
                temp_input = None
                raise HTTPException(status_code=400, detail="音频转换失败")
        else:
            raise HTTPException(status_code=400, detail="请提供音频文件或音频文件路径")
        
        # 保存到 voices 目录
        os.makedirs(VOICES_DIR, exist_ok=True)
        target_wav = os.path.join(VOICES_DIR, f"{safe_name}.wav")
        target_txt = os.path.join(VOICES_DIR, f"{safe_name}.txt")
        
        shutil.copy(wav_path, target_wav)
        with open(target_txt, "w", encoding='utf-8') as f:
            f.write(text)
        
        # 清理临时文件
        # 如果使用了上传文件，清理上传的临时文件
        if temp_input:
            cleanup_temp_files(temp_input, wav_path if wav_path != temp_input else None)
        # 如果wav_path是临时转换文件（使用audio_path时可能产生），也需要清理
        elif wav_path and TMP_DIR in wav_path and 'temp_convert_' in wav_path:
            cleanup_temp_files(wav_path)
        temp_input = None
        wav_path = None
        
        return {
            "success": True,
            "name": safe_name,
            "message": f"音色 '{safe_name}' 克隆成功"
        }
    except HTTPException:
        # HTTPException 需要重新抛出，但也要清理临时文件
        if temp_input:
            cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        elif wav_path and TMP_DIR in wav_path and 'temp_convert_' in wav_path:
            cleanup_temp_files(wav_path)
        raise
    except Exception as e:
        print(f"Clone Voice Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        # 确保清理临时文件
        if temp_input:
            cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        elif wav_path and TMP_DIR in wav_path and 'temp_convert_' in wav_path:
            cleanup_temp_files(wav_path)
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

        temp_dir = get_temp_path("temp_clone")
        os.makedirs(temp_dir, exist_ok=True)
        generate_audio(
            model=model,
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,
            output_path=temp_dir
        )

        if preview:
            # 预览音频保存在 tmp 目录下
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"preview_clone_{timestamp}.wav"
            audio_path = os.path.join(TMP_DIR, audio_filename)

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

