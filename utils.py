"""
工具函数
"""
import os
import shutil
import wave
import subprocess
import time
import re
from datetime import datetime
from typing import Optional, List
from config import BASE_DIR, BASE_OUTPUT_DIR, STT_OUTPUT_DIR, MODELS_DIR, SAMPLE_RATE, FILENAME_MAX_LEN
from typing import Optional


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
    
    # 清理可能直接在当前目录创建的文件
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

    cleanup_temp_files(temp_folder)

    relative_path = os.path.relpath(final_path, BASE_DIR)
    return relative_path


def format_timestamp(seconds: float) -> str:
    """将秒数转换为 SRT 时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def save_stt_results(text: str, segments: List[dict], audio_filename: str, audio_path: Optional[str] = None) -> dict:
    """保存 STT 结果，生成 TXT、SRT 文件，并保存原始音频文件"""
    os.makedirs(STT_OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
    
    # 保存原始音频文件（如果提供了音频路径）
    audio_output_path = None
    if audio_path and os.path.exists(audio_path):
        # 获取原始音频文件的扩展名
        audio_ext = os.path.splitext(audio_path)[1] or ".wav"
        audio_filename_output = f"{timestamp}_{base_name}{audio_ext}"
        audio_output_path = os.path.join(STT_OUTPUT_DIR, audio_filename_output)
        # 复制音频文件到输出目录
        shutil.copy2(audio_path, audio_output_path)
    
    # 返回相对路径
    result = {
        "txt_path": os.path.relpath(txt_path, BASE_DIR),
        "srt_path": os.path.relpath(srt_path, BASE_DIR)
    }
    if audio_output_path:
        result["audio_path"] = os.path.relpath(audio_output_path, BASE_DIR)
    
    return result

