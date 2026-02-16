"""
STT API 路由
"""
import os
import re
import gc
import uuid
import traceback
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from mlx_audio.stt.generate import generate_transcription
from models import load_asr_model_cached
from utils import cleanup_temp_files, cleanup_stt_temp_files, convert_audio_if_needed, save_stt_results, get_temp_path
from history import save_history_item
from api.stt_aligner import run_forced_alignment

router = APIRouter()


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    model_key: str = Form(None),
    language: str = Form("Chinese")
):
    """语音转文字 - 使用 ASR 模型生成文本，使用 ForcedAligner 模型生成时间戳"""
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

        # 加载 ASR 模型用于文本识别
        asr_model = load_asr_model_cached(model_key)

        print(f"[STT] 开始转录: {wav_path}")
        temp_output_dir = get_temp_path("temp_stt_output")
        os.makedirs(temp_output_dir, exist_ok=True)

        try:
            # 确保语言参数有效
            if not language or language.lower() in ["auto", "", "null"]:
                language = "Chinese"

            print(f"[STT] 使用语言: {language}")

            # 步骤 1: 使用 ASR 模型生成文本
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_output_dir)
                transcription = generate_transcription(
                    model=asr_model,
                    audio=wav_path,
                    output_path=temp_output_dir,
                    format="txt",
                    verbose=True,
                    language=language
                )
            finally:
                os.chdir(original_cwd)

            # 提取文本内容
            text = ""
            detected_language = "unknown"

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


            if hasattr(transcription, 'language'):
                detected_language = transcription.language

            print(f"[STT] ASR 识别结果: {text[:100]}...")

            # 步骤 2: 使用 ForcedAligner 生成时间戳
            processed_segments = []

            if text.strip():
                aligned_segments = run_forced_alignment(wav_path, text, language)

                if aligned_segments:
                    for i, seg in enumerate(aligned_segments):
                        processed_segments.append({
                            "id": i,
                            "start": seg["start_time"],
                            "end": seg["end_time"],
                            "text": seg["text"],
                            "confidence": 0.0
                        })
                else:
                    print("[STT] ForcedAligner 未返回结果，使用估计时间戳")
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

        finally:
            cleanup_stt_temp_files(temp_output_dir)
            temp_output_dir = None

        # 保存结果文件
        file_paths = save_stt_results(text, processed_segments, audio.filename, wav_path)

        # 保存历史记录
        history_item = {
            "id": str(uuid.uuid4()),
            "type": "stt",
            "audio_filename": audio.filename,
            "text": text,
            "language": detected_language if detected_language != "unknown" else language,
            "segments": processed_segments,
            "txt_path": file_paths["txt_path"],
            "srt_path": file_paths["srt_path"],
            "created_at": datetime.now().isoformat()
        }
        if "audio_path" in file_paths:
            history_item["audio_path"] = file_paths["audio_path"]
        save_history_item(history_item)

        # 清理临时文件
        cleanup_temp_files(temp_input, wav_path if wav_path != temp_input else None)
        temp_input = None
        wav_path = None

        gc.collect()

        # 构建返回结果
        result = {
            "success": True,
            "text": text,
            "language": detected_language if detected_language != "unknown" else language,
            "segments": processed_segments,
            "txt_path": file_paths["txt_path"],
            "srt_path": file_paths["srt_path"],
            "history_id": history_item["id"]
        }
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
