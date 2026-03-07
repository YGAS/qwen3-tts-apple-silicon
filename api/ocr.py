"""
OCR API 路由 - 使用LMStudio进行图片文字识别
"""
import os
import re
import base64
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests

router = APIRouter()

# OCR默认配置
DEFAULT_OCR_BASE_URL = "http://localhost:1234/v1"
DEFAULT_OCR_API_KEY = "sk-lm-SaeJfHIy:GTdi4a8wepwEzetDEH7N"
DEFAULT_OCR_MODEL = "qwen3.5-0.8b"


class OCRRequest(BaseModel):
    """OCR请求模型"""
    image: str  # base64编码的图片，包含data:image/xxx;base64,前缀
    base_url: str = DEFAULT_OCR_BASE_URL
    api_key: str = DEFAULT_OCR_API_KEY
    model: str = DEFAULT_OCR_MODEL


class OCRConfig(BaseModel):
    """OCR配置模型"""
    base_url: str = DEFAULT_OCR_BASE_URL
    api_key: str = DEFAULT_OCR_API_KEY
    model: str = DEFAULT_OCR_MODEL


class OCRResponse(BaseModel):
    """OCR响应模型"""
    success: bool
    text: str = ""
    detail: str = ""


def extract_base64_data(base64_string: str) -> str:
    """从base64字符串中提取纯数据部分"""
    if ',' in base64_string:
        return base64_string.split(',')[1]
    return base64_string


def get_image_mime_type(base64_string: str) -> str:
    """从base64字符串中提取MIME类型"""
    if ',' in base64_string and ';' in base64_string:
        match = re.match(r'data:([^;]+);', base64_string)
        if match:
            return match.group(1)
    return "image/jpeg"


def validate_ocr_config(base_url: str, api_key: str, model: str) -> tuple[bool, str]:
    """验证OCR配置参数"""
    if not base_url or not base_url.strip():
        return False, "OCR服务地址不能为空"

    if not base_url.startswith(('http://', 'https://')):
        return False, "OCR服务地址必须以 http:// 或 https:// 开头"

    if not api_key or not api_key.strip():
        return False, "API Key不能为空"

    if not model or not model.strip():
        return False, "模型名称不能为空"

    return True, ""


@router.post("/ocr", response_model=OCRResponse)
async def perform_ocr(request: OCRRequest):
    """
    使用LMStudio进行图片OCR识别

    接收base64编码的图片，返回识别出的文字
    """
    if not request.image:
        raise HTTPException(status_code=400, detail="图片数据不能为空")

    # 验证配置参数
    is_valid, error_msg = validate_ocr_config(request.base_url, request.api_key, request.model)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"OCR配置错误: {error_msg}")

    try:
        # 提取base64数据
        base64_data = extract_base64_data(request.image)
        mime_type = get_image_mime_type(request.image)

        # 构建OpenAI格式的消息
        # 使用data URL格式传递图片
        image_url = f"data:{mime_type};base64,{base64_data}"

        # 调用OCR API
        headers = {
            "Authorization": f"Bearer {request.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": "system",
                    "content": "# Role 你是一个专业的 OCR 识别与 TTS（文本转语音）文本优化专家。你的核心任务是从图片中提取文字，并将其处理为最适合 TTS 引擎朗读的格式。# Workflow 1. **OCR 识别**：准确识别图片中的所有可见文字，包括标题、副标题、正文、列表、注释等，不要遗漏任何有效信息。2. **文本纠错**：根据上下文逻辑，自动修正明显的 OCR 识别错误，确保语义通顺。3. **结构保留与 TTS 优化**：  - **标题处理**：    - 必须保留所有标题/副标题文字，不可省略或合并。    - 标题末尾添加句号或感叹号等标点，确保 TTS 朗读时有自然收尾。    - 标题与正文之间使用双换行符（\n\n）分隔，制造明显停顿。    - 若标题较短（如 2-5 字），可在标题后添加逗号或短停顿标记，避免朗读过快。  - **停顿标记**：使用标准标点符号（逗号、句号、分号）控制呼吸和短停顿；长句按语义适当拆分。  - **段落标记**：按语义逻辑使用双换行符（\n\n）区分段落。  - **特殊处理**：仅移除纯装饰性符号（如页码、图标、水印），保留对语义重要的数字、英文、标点。4. **输出控制**：  - **严禁**输出任何开场白、结束语或解释性文字。  - **严禁**使用 Markdown 代码块包裹内容。  - **只输出**最终优化后的纯文本，确保可直接接入 TTS 引擎。# Constraints- 如果图片中没有文字，输出空内容。- 保持原文语言，不要翻译。- 输出必须是纯文本，不包含任何元数据或格式标记。- 标题是核心结构信息，优先级高于段落合并，宁可多分段也不合并标题。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请处理这张图片：执行完整 OCR 识别，保留所有标题和层级结构，并根据 TTS 朗读需求优化停顿与段落。只输出优化后的纯文字，不要任何额外说明或 Markdown 格式。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2048
        }

        response = requests.post(
            f"{request.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            error_detail = f"OCR API错误: HTTP {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_detail += f" - {error_data['error']}"
            except:
                error_detail += f" - {response.text}"
            raise HTTPException(status_code=500, detail=error_detail)

        result = response.json()

        # 提取识别的文字
        if "choices" in result and len(result["choices"]) > 0:
            recognized_text = result["choices"][0]["message"]["content"].strip()

            # 清理可能的markdown格式
            recognized_text = re.sub(r'^```\w*\n?', '', recognized_text)
            recognized_text = re.sub(r'\n?```$', '', recognized_text)
            recognized_text = recognized_text.strip()

            return OCRResponse(
                success=True,
                text=recognized_text,
                detail="识别成功"
            )
        else:
            raise HTTPException(status_code=500, detail="OCR API返回结果格式错误")

    except HTTPException:
        raise
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail=f"无法连接到OCR服务，请确保服务已启动并可通过 {request.base_url} 访问"
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="OCR请求超时，请稍后重试"
        )
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")


@router.get("/ocr/config", response_model=OCRConfig)
async def get_ocr_config():
    """获取默认OCR配置"""
    return OCRConfig(
        base_url=DEFAULT_OCR_BASE_URL,
        api_key=DEFAULT_OCR_API_KEY,
        model=DEFAULT_OCR_MODEL
    )
