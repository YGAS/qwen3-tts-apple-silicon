"""
历史记录管理
"""
import os
import json
from typing import List
from config import HISTORY_FILE, VOICES_DIR, SPEAKER_MAP

# 导出 HISTORY_FILE 供其他模块使用
__all__ = ['get_history', 'save_history_item', 'get_all_speakers', 'HISTORY_FILE']


def get_history() -> List[dict]:
    """获取历史记录"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_history_item(item: dict):
    """保存历史记录"""
    history = get_history()
    history.insert(0, item)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_all_speakers() -> List[dict]:
    """获取所有音色"""
    speakers = []
    
    # 预设音色
    all_speakers_set = set()
    for lang, names in SPEAKER_MAP.items():
        for name in names:
            all_speakers_set.add(name)
    
    for name in sorted(all_speakers_set):
        languages = []
        for lang, names in SPEAKER_MAP.items():
            if name in names:
                languages.append(lang)
        speakers.append({
            "name": name,
            "type": "preset",
            "languages": languages,
            "is_multilingual": len(languages) > 1
        })
    
    # 克隆音色
    if os.path.exists(VOICES_DIR):
        for f in sorted(os.listdir(VOICES_DIR)):
            if f.endswith(".wav"):
                name = f.replace(".wav", "")
                txt_path = os.path.join(VOICES_DIR, f.replace(".wav", ".txt"))
                language = "Unknown"
                if os.path.exists(txt_path):
                    try:
                        with open(txt_path, 'r', encoding='utf-8') as tf:
                            content = tf.read()
                            # 简单判断语言
                            if any('\u4e00' <= c <= '\u9fff' for c in content):
                                language = "Chinese"
                            elif any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in content):
                                language = "Japanese"
                            elif any('\uac00' <= c <= '\ud7af' for c in content):
                                language = "Korean"
                            else:
                                language = "English"
                    except:
                        pass
                
                speakers.append({
                    "name": name,
                    "type": "cloned",
                    "languages": [language],
                    "is_multilingual": False
                })
    
    return speakers

