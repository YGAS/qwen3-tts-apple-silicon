"""
OCR API 模块 - 图片转 Markdown
使用 DeepSeek-OCR-4bit 模型进行图像文字识别
"""
import os
import re
import gc
from pathlib import Path
from typing import Optional, Union, List
from PIL import Image
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()

# 全局模型缓存
_ocr_model = None
_ocr_processor = None

# 模型路径
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "DeepSeek-OCR-4bit"
)

# 清理 grounding tags 的正则表达式
TAG_PATTERN = re.compile(
    r"<\|ref\|>(.*?)<\|/ref\|><\|det\|>.*?<\|/det\|>",
    flags=re.DOTALL,
)


def get_ocr_model(model_path: Optional[str] = None):
    """
    获取 OCR 模型（懒加载）
    
    Args:
        model_path: 模型路径，默认使用内置模型
        
    Returns:
        tuple: (model, processor)
    """
    global _ocr_model, _ocr_processor
    
    if _ocr_model is None or _ocr_processor is None:
        try:
            from mlx_vlm import load, generate
            from mlx_vlm.utils import load_config
            
            actual_path = model_path or DEFAULT_MODEL_PATH
            
            if not os.path.exists(actual_path):
                raise FileNotFoundError(f"模型路径不存在: {actual_path}")
            
            # 加载模型和处理器
            _ocr_model, _ocr_processor = load(actual_path, trust_remote_code=True)
            
        except ImportError as e:
            raise ImportError(
                f"加载 mlx-vlm 失败: {e}. "
                "请运行: pip install -U mlx-vlm"
            )
        except Exception as e:
            raise RuntimeError(f"加载 OCR 模型失败: {e}")
    
    return _ocr_model, _ocr_processor


def cleanup_grounding_tags(text: str) -> str:
    """
    清理 DeepSeek OCR 模型输出中的 grounding tags
    
    DeepSeek OCR 模型包含坐标标签，格式为:
    <|ref|>文本<|/ref|><|det|>坐标<|/det|>
    
    此函数保留文本内容，去除坐标信息
    
    Args:
        text: 原始 OCR 输出文本
        
    Returns:
        str: 清理后的文本
    """
    return TAG_PATTERN.sub(r"\1", text)


def image_to_markdown(
    image_path: Union[str, Path],
    prompt: str = "只提取图片中的原始文字内容，不要添加任何描述或标题。",
    max_tokens: int = 4000,
    temperature: float = 0.0,
    cleanup_tags: bool = True,
    model_path: Optional[str] = None
) -> dict:
    """
    将图片转换为 Markdown 文本
    
    Args:
        image_path: 图片路径
        prompt: 提示词
        max_tokens: 最大生成token数
        temperature: 温度参数
        cleanup_tags: 是否清理 grounding tags
        model_path: 自定义模型路径
        
    Returns:
        dict: 包含原始文本、清理后文本和元数据的字典
    """
    from mlx_vlm import generate
    
    # 加载模型
    model, processor = get_ocr_model(model_path)
    
    # 准备生成配置
    config = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "verbose": False,
    }
    
    # 构建包含图像 token 的提示词
    # DeepSeek OCR 模型需要 <image> token 在提示词中
    if "<image>" not in prompt:
        formatted_prompt = f"<image>\n{prompt}"
    else:
        formatted_prompt = prompt
    
    # 生成文本
    result = generate(
        model=model,
        processor=processor,
        image=str(image_path),
        prompt=formatted_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        verbose=False,
    )

    # 处理返回结果（可能是 GenerationResult 对象或字符串）
    if hasattr(result, 'text'):
        raw_output = result.text
    elif hasattr(result, 'generation'):
        raw_output = result.generation
    else:
        raw_output = str(result)

    # 清理 grounding tags
    cleaned_output = cleanup_grounding_tags(raw_output) if cleanup_tags else raw_output

    return {
        "raw_text": raw_output,
        "markdown": cleaned_output,
        "image_path": str(image_path),
        "prompt": prompt,
    }


def batch_image_to_markdown(
    image_paths: List[Union[str, Path]],
    prompt: str = "只提取图片中的原始文字内容，不要添加任何描述或标题。",
    max_tokens: int = 4000,
    temperature: float = 0.0,
    cleanup_tags: bool = True,
    model_path: Optional[str] = None
) -> List[dict]:
    """
    批量将图片转换为 Markdown 文本
    
    Args:
        image_paths: 图片路径列表
        prompt: 提示词
        max_tokens: 最大生成token数
        temperature: 温度参数
        cleanup_tags: 是否清理 grounding tags
        model_path: 自定义模型路径
        
    Returns:
        List[dict]: 每个图片的处理结果列表
    """
    results = []
    for image_path in image_paths:
        try:
            result = image_to_markdown(
                image_path=image_path,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                cleanup_tags=cleanup_tags,
                model_path=model_path
            )
            results.append(result)
        except Exception as e:
            results.append({
                "error": str(e),
                "image_path": str(image_path),
                "markdown": "",
                "raw_text": "",
            })
    return results


def unload_ocr_model():
    """卸载 OCR 模型释放内存"""
    global _ocr_model, _ocr_processor
    
    if _ocr_model is not None:
        del _ocr_model
        _ocr_model = None
    
    if _ocr_processor is not None:
        del _ocr_processor
        _ocr_processor = None
    
    # 强制垃圾回收
    gc.collect()


@router.post("/ocr")
async def ocr_endpoint(
    file: UploadFile = File(...),
    prompt: str = Form("只提取图片中的原始文字内容，不要添加任何描述或标题。"),
    max_tokens: int = Form(4000),
    temperature: float = Form(0.0),
    cleanup_tags: bool = Form(True),
):
    """
    OCR 图片转 Markdown API
    
    - **file**: 上传的图片文件
    - **prompt**: 提示词（可选，默认转换为markdown格式）
    - **max_tokens**: 最大生成token数（可选，默认4000）
    - **temperature**: 温度参数（可选，默认0.0）
    - **cleanup_tags**: 是否清理 grounding tags（可选，默认True）
    """
    import tempfile
    import shutil
    
    # 验证文件类型
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}. 支持的类型: {', '.join(allowed_types)}"
        )
    
    # 保存上传的文件到临时目录
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 执行 OCR
        result = image_to_markdown(
            image_path=temp_path,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            cleanup_tags=cleanup_tags,
        )
        
        return JSONResponse(content={
            "success": True,
            "data": result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 处理失败: {str(e)}")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@router.post("/ocr/batch")
async def ocr_batch_endpoint(
    files: List[UploadFile] = File(...),
    prompt: str = Form("只提取图片中的原始文字内容，不要添加任何描述或标题。"),
    max_tokens: int = Form(4000),
    temperature: float = Form(0.0),
    cleanup_tags: bool = Form(True),
):
    """
    批量 OCR 图片转 Markdown API
    
    - **files**: 上传的图片文件列表
    - **prompt**: 提示词（可选）
    - **max_tokens**: 最大生成token数（可选）
    - **temperature**: 温度参数（可选）
    - **cleanup_tags**: 是否清理 grounding tags（可选）
    """
    import tempfile
    import shutil
    
    temp_paths = []
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 保存所有上传的文件
        for file in files:
            allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
            if file.content_type not in allowed_types:
                continue
                
            temp_path = os.path.join(temp_dir, file.filename)
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_paths.append(temp_path)
        
        # 批量执行 OCR
        results = batch_image_to_markdown(
            image_paths=temp_paths,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            cleanup_tags=cleanup_tags,
        )
        
        return JSONResponse(content={
            "success": True,
            "count": len(results),
            "data": results
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量 OCR 处理失败: {str(e)}")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@router.get("/ocr/status")
async def ocr_status():
    """获取 OCR 模型状态"""
    global _ocr_model, _ocr_processor
    
    return {
        "model_loaded": _ocr_model is not None and _ocr_processor is not None,
        "model_path": DEFAULT_MODEL_PATH,
        "model_exists": os.path.exists(DEFAULT_MODEL_PATH),
    }


@router.post("/ocr/unload")
async def ocr_unload():
    """卸载 OCR 模型释放内存"""
    unload_ocr_model()
    return {"message": "OCR 模型已卸载"}
