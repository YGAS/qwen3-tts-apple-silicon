"""
Qwen3-TTS Web 应用入口文件
此文件已重构，主要功能已迁移到模块化结构中：
- app.py: 主应用入口
- config.py: 配置和常量
- models.py: 模型加载
- utils.py: 工具函数
- api/: API 路由
- routes.py: 页面路由
- templates.py: HTML 模板

为了向后兼容，此文件重定向到 app.py
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入主应用
from app import app

# 导出 app 以供 uvicorn 等工具使用
__all__ = ['app']

# 为了向后兼容，支持直接运行此文件
if __name__ == "__main__":
    import uvicorn
    from config import BASE_DIR, BASE_OUTPUT_DIR, VOICES_DIR, TMP_DIR
    
    # 确保目录存在
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(VOICES_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8766)
