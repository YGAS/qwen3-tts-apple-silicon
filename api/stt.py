"""
STT API 路由
"""
import os
import re
import gc
import time
import uuid
import traceback
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from mlx_audio.stt.generate import generate_transcription
from models import load_asr_model_cached
from utils import cleanup_temp_files, cleanup_stt_temp_files, convert_audio_if_needed, save_stt_results, get_temp_path
from config import TMP_DIR
from history import save_history_item

router = APIRouter()


@router.post("/stt")
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
        # 保存上传的音频到 tmp 目录
        safe_filename = re.sub(r'[^\w\s.-]', '', audio.filename).strip()
        temp_input = get_temp_path("temp_stt", safe_filename)
        with open(temp_input, "wb") as f:
            content = await audio.read()
            f.write(content)
        
        wav_path = convert_audio_if_needed(temp_input)
        if not wav_path:
            cleanup_temp_files(temp_input)
            temp_input = None
            raise HTTPException(status_code=400, detail="音频转换失败，请检查文件格式")
        
        if wav_path != temp_input:
            cleanup_temp_files(temp_input)
            temp_input = None
        
        model = load_asr_model_cached(model_key)
        
        print(f"[STT] 开始转录: {wav_path}")
        temp_output_dir = get_temp_path("temp_stt_output")
        os.makedirs(temp_output_dir, exist_ok=True)
        
        try:
            transcription = generate_transcription(
                model=model,
                audio=wav_path,
                output_path=temp_output_dir,
                format="txt",
                verbose=True
            )
            
            text = ""
            language = "unknown"
            processed_segments = []
            
            if hasattr(transcription, 'text'):
                text = transcription.text
            elif isinstance(transcription, str):
                text = transcription
            else:
                output_file = os.path.join(temp_output_dir, "transcript.txt")
                if not os.path.exists(output_file):
                    output_file = os.path.join(temp_output_dir, "transcription.txt")
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        text = f.read().strip()
            
            if hasattr(transcription, 'segments'):
                segments = transcription.segments
            elif hasattr(transcription, 'chunks'):
                segments = transcription.chunks
            else:
                segments = []
            
            if segments:
                for i, seg in enumerate(segments):
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
                
                if processed_segments and isinstance(segments[0], dict):
                    language = segments[0].get("language", "unknown")
                elif processed_segments and hasattr(segments[0], 'language'):
                    language = getattr(segments[0], 'language', 'unknown')
            
            if language == "unknown" and hasattr(transcription, 'language'):
                language = transcription.language
        finally:
            cleanup_stt_temp_files(temp_output_dir)
            temp_output_dir = None
        
        if not processed_segments and text:
            sentences = re.split(r'[。！？.!?]', text)
            current_time = 0.0
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    duration = len(sentence) / 25.0
                    processed_segments.append({
                        "id": i,
                        "start": current_time,
                        "end": current_time + duration,
                        "text": sentence.strip(),
                        "confidence": 0.0
                    })
                    current_time += duration
        
        # 保存结果文件（包括原始音频文件）
        file_paths = save_stt_results(text, processed_segments, audio.filename, wav_path)
        
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
        # 如果保存了音频文件，添加到历史记录中
        if "audio_path" in file_paths:
            history_item["audio_path"] = file_paths["audio_path"]
        save_history_item(history_item)
        
        # 清理临时文件（音频文件已保存到输出目录，可以清理临时文件）
        cleanup_temp_files(temp_input, wav_path if wav_path != temp_input else None)
        temp_input = None
        wav_path = None
        
        gc.collect()
        
        # 构建返回结果
        result = {
            "success": True,
            "text": text,
            "language": language,
            "segments": processed_segments,
            "txt_path": file_paths["txt_path"],
            "srt_path": file_paths["srt_path"],
            "history_id": history_item["id"]
        }
        # 如果保存了音频文件，添加到返回结果中
        if "audio_path" in file_paths:
            result["audio_path"] = file_paths["audio_path"]
        
        return result
    except HTTPException:
        cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        cleanup_stt_temp_files(temp_output_dir)
        raise
    except Exception as e:
        print(f"STT Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        cleanup_temp_files(temp_input, wav_path if wav_path and wav_path != temp_input else None)
        cleanup_stt_temp_files(temp_output_dir)
        raise HTTPException(status_code=500, detail=f"语音转文字失败: {str(e)}")

