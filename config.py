"""
配置和常量定义
"""
import os

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
MODELS_DIR = os.path.join(BASE_DIR, "models")
VOICES_DIR = os.path.join(BASE_DIR, "voices")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
STT_OUTPUT_DIR = os.path.join(BASE_OUTPUT_DIR, "STT")
TMP_DIR = os.path.join(BASE_DIR, "tmp")

# 设置
SAMPLE_RATE = 24000
FILENAME_MAX_LEN = 20

# TTS 模型定义
MODELS = {
    "custom": {
        "pro": {"folder": "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit", "output_subfolder": "CustomVoice"},
        "lite": {"folder": "Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit", "output_subfolder": "CustomVoice"},
    },
    "design": {
        "pro": {"folder": "Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit", "output_subfolder": "VoiceDesign"},
        "lite": {"folder": "Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit", "output_subfolder": "VoiceDesign"},
    },
    "clone": {
        "pro": {"folder": "Qwen3-TTS-12Hz-1.7B-Base-8bit", "output_subfolder": "Clones"},
        "lite": {"folder": "Qwen3-TTS-12Hz-0.6B-Base-8bit", "output_subfolder": "Clones"},
    },
}

# ASR 模型定义
ASR_MODELS = {
    "qwen3_asr_0.6b": {
        "folder": "Qwen3-ASR-0.6B-8bit",
        "type": "qwen3_asr",
        "default": False
    },
    "qwen3_asr_1.7b": {
        "folder": "Qwen3-ASR-1.7B-8bit",
        "type": "qwen3_asr",
        "default": True
    },
}

# ForcedAligner 模型定义
FORCED_ALIGNER_MODELS = {
    "qwen3_forced_aligner_0.6b": {
        "folder": "Qwen3-ForcedAligner-0.6B-8bit",
        "type": "qwen3_forced_aligner",
        "default": True
    },
}

# 音色映射表
SPEAKER_MAP = {
    "English": ["Ryan", "Aiden", "Ethan", "Chelsie", "Serena", "Vivian"],
    "Chinese": ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"],
    "Japanese": ["Ono_Anna"],
    "Korean": ["Sohee"]
}

# 语气选项
EMOTION_OPTIONS = [
    {"value": "Normal tone", "label": "正常", "description": "标准语调"},
    {"value": "Sad and crying, speaking slowly", "label": "悲伤哭泣", "description": "悲伤哭泣，语速较慢"},
    {"value": "Excited and happy, speaking very fast", "label": "兴奋开心", "description": "兴奋开心，语速很快"},
    {"value": "Angry and shouting", "label": "愤怒大喊", "description": "愤怒大喊"},
    {"value": "Whispering quietly", "label": "轻声耳语", "description": "轻声耳语"},
]

# 语速选项
SPEED_OPTIONS = [
    {"value": 0.8, "label": "慢速 (0.8x)"},
    {"value": 1.0, "label": "正常 (1.0x)"},
    {"value": 1.3, "label": "快速 (1.3x)"},
]

# 语言选项
LANGUAGE_OPTIONS = [
    {"value": "English", "label": "英语"},
    {"value": "Chinese", "label": "中文"},
    {"value": "Japanese", "label": "日语"},
    {"value": "Korean", "label": "韩语"},
]

