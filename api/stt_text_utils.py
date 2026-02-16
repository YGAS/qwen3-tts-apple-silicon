"""
STT 文本处理工具函数
"""
import re
import string


def format_time_for_srt(seconds: float) -> str:
    """将秒数转换为 SRT 时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def split_text_by_punctuation(text: str) -> list:
    """
    根据标点符号将文本分割成段落列表

    Args:
        text: ASR 生成的文本

    Returns:
        段落列表，每个元素包含段落文本
    """
    sentence_endings = r'[。！？.!?；;，,]'
    parts = re.split(f'({sentence_endings})', text)

    sentences = []
    current_sentence = ""

    for part in parts:
        if not part:
            continue
        current_sentence += part
        if re.match(sentence_endings, part):
            if current_sentence.strip():
                sentences.append(current_sentence.strip())
            current_sentence = ""

    if current_sentence.strip():
        sentences.append(current_sentence.strip())

    return sentences


def remove_punctuation(text: str) -> str:
    """移除文本中的标点符号"""
    chinese_punctuation = '。！？.!?；;，,、：:""''（）【】《》'
    english_punctuation = string.punctuation
    all_punctuation = chinese_punctuation + english_punctuation

    result = ''
    for char in text:
        if char not in all_punctuation:
            result += char
    return result


def merge_short_sentences(segments: list, min_duration: float = 2.0, max_chars: int = 20) -> list:
    """
    合并时间间隔短、持续时间短的句子，避免字幕闪动
    输出时移除标点符号，多个句子用空格分隔

    Args:
        segments: 句子片段列表
        min_duration: 最小持续时间（秒）
        max_chars: 合并后的最大字数

    Returns:
        合并后的句子片段列表
    """
    if not segments:
        return []

    if len(segments) <= 1:
        if segments:
            segments[0]['text'] = remove_punctuation(segments[0]['text'])
        return segments

    result = []
    current_segment = None

    for segment in segments:
        clean_text = remove_punctuation(segment['text'])

        if current_segment is None:
            current_segment = {
                'text': clean_text,
                'start_time': segment['start_time'],
                'end_time': segment['end_time']
            }
            continue

        current_duration = current_segment['end_time'] - current_segment['start_time']
        gap = segment['start_time'] - current_segment['end_time']

        should_merge = (
            current_duration < min_duration and
            gap < 0.5 and
            len(current_segment['text'] + clean_text) + 1 <= max_chars
        )

        if should_merge:
            current_segment['text'] += ' ' + clean_text
            current_segment['end_time'] = segment['end_time']
        else:
            result.append(current_segment)
            current_segment = {
                'text': clean_text,
                'start_time': segment['start_time'],
                'end_time': segment['end_time']
            }

    if current_segment:
        result.append(current_segment)

    return result


def find_sentence_timestamps(sentences: list, char_timestamps: list) -> list:
    """
    根据字级别时间戳，为每个句子找到开始和结束时间戳

    Args:
        sentences: 文本段落列表
        char_timestamps: 字级别时间戳列表

    Returns:
        句子级别的时间戳列表
    """
    result = []

    all_chars = []
    for ts in char_timestamps:
        char_text = ts.get('text', '') if isinstance(ts, dict) else getattr(ts, 'text', '')
        char_start = ts.get('start', 0.0) if isinstance(ts, dict) else getattr(ts, 'start', 0.0)
        char_end = ts.get('end', 0.0) if isinstance(ts, dict) else getattr(ts, 'end', 0.0)

        for char in char_text:
            if char.strip():
                all_chars.append({'text': char, 'start': char_start, 'end': char_end})

    char_index = 0
    for sentence in sentences:
        clean_sentence = ''.join(sentence.split())
        clean_sentence_no_punct = remove_punctuation(clean_sentence)

        if not clean_sentence_no_punct:
            continue

        sentence_chars = list(clean_sentence_no_punct)
        sentence_len = len(sentence_chars)

        found = False
        start_time = 0.0
        end_time = 0.0

        while char_index < len(all_chars):
            if all_chars[char_index]['text'] == sentence_chars[0]:
                match = True
                for i in range(sentence_len):
                    if char_index + i >= len(all_chars):
                        match = False
                        break
                    if all_chars[char_index + i]['text'] != sentence_chars[i]:
                        match = False
                        break

                if match:
                    start_time = all_chars[char_index]['start']
                    end_time = all_chars[char_index + sentence_len - 1]['end']
                    char_index += sentence_len
                    found = True
                    break

            char_index += 1

        if found:
            result.append({
                'text': sentence,
                'start_time': start_time,
                'end_time': end_time
            })

    return result
