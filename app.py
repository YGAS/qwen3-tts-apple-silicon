"""
Qwen3-TTS Web 应用主入口
"""
import os
import sys
import warnings
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 导入配置
from config import BASE_DIR, BASE_OUTPUT_DIR, VOICES_DIR

# 导入 API 路由
from api import common, tts, stt, clone, history, files

# 导入页面路由
from routes import register_routes

# 抑制警告
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# 检查依赖
try:
    from mlx_audio.tts.utils import load_model
    from mlx_audio.stt.utils import load_model as load_stt_model
except ImportError:
    print("Error: 'mlx_audio' library not found.")
    print("Run: source .venv/bin/activate")
    sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("[启动] 应用启动中...")
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(VOICES_DIR, exist_ok=True)
    print("[启动] 模型将按需加载（首次使用时自动缓存）")
    
    yield
    
    print("[关闭] 应用关闭中...")


# 创建 FastAPI 应用
app = FastAPI(
    title="Qwen3-TTS Web",
    description="Qwen3-TTS 的 Web 界面",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(common.router, prefix="/api", tags=["common"])
app.include_router(tts.router, prefix="/api", tags=["tts"])
app.include_router(stt.router, prefix="/api", tags=["stt"])
app.include_router(clone.router, prefix="/api", tags=["clone"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(files.router, prefix="/api", tags=["files"])

# 注册页面路由
register_routes(app)

# 挂载静态文件
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(VOICES_DIR, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8766)

