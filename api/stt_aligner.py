"""
STT ForcedAligner 对齐功能
"""
import os
import traceback
from mlx_audio.stt.generate import generate_transcription
from models import load_forced_aligner_model_cached
from utils import cleanup_stt_temp_files, get_temp_path
from api.stt_text_utils import split_text_by_punctuation, find_sentence_timestamps, merge_short_sentences


def run_forced_alignment(audio_path: str, text: str, language: str = "Chinese") -> list:
    """
    使用 ForcedAligner 模型进行强制对齐，返回带时间戳的片段列表

    Args:
        audio_path: 音频文件路径
        text: 需要对齐的文本（ASR 生成的文本）
        language: 语言

    Returns:
        包含时间戳的片段列表
    """
    try:
        aligner_model = load_forced_aligner_model_cached()

        temp_align_dir = get_temp_path("temp_forced_align")
        os.makedirs(temp_align_dir, exist_ok=True)
        original_cwd = os.getcwd()

        try:
            os.chdir(temp_align_dir)
            transcription = generate_transcription(
                model=aligner_model,
                audio=audio_path,
                text=text,
                output_path=temp_align_dir,
                verbose=True,
                language=language
            )
        finally:
            os.chdir(original_cwd)
            cleanup_stt_temp_files(temp_align_dir)


        # 提取字级别时间戳
        char_timestamps = []
        if hasattr(transcription, 'segments') and transcription.segments:
            for seg in transcription.segments:
                if isinstance(seg, dict):
                    char_timestamps.append({
                        'text': seg.get('text', ''),
                        'start': seg.get('start', 0.0),
                        'end': seg.get('end', 0.0)
                    })
                elif hasattr(seg, '__dict__'):
                    char_timestamps.append({
                        'text': getattr(seg, 'text', ''),
                        'start': getattr(seg, 'start', 0.0),
                        'end': getattr(seg, 'end', 0.0)
                    })
        else:
            return []

        # 步骤 1: 根据标点符号分割 ASR 文本
        sentences = split_text_by_punctuation(text)

        # 步骤 2: 为每个段落匹配时间戳
        aligned_segments = find_sentence_timestamps(sentences, char_timestamps)

        # 步骤 3: 合并时间间隔短的句子
        merged_segments = merge_short_sentences(aligned_segments)

        return merged_segments

    except Exception as e:
        print(f"[ForcedAligner] 对齐失败: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return []
