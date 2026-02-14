"""
页面路由
"""
from fastapi.responses import HTMLResponse, RedirectResponse
from templates import (
    get_html_template,
    get_tts_page,
    get_speakers_page,
    get_clone_page,
    get_stt_page,
    get_history_page
)


def render_page(template_func, active_page: str):
    """渲染页面"""
    template = get_html_template()
    content = template.replace('{{ content | safe }}', template_func())
    content = content.replace("{{ 'active' if page == 'tts' else '' }}", "active" if active_page == 'tts' else "")
    content = content.replace("{{ 'active' if page == 'stt' else '' }}", "active" if active_page == 'stt' else "")
    content = content.replace("{{ 'active' if page == 'speakers' else '' }}", "active" if active_page == 'speakers' else "")
    content = content.replace("{{ 'active' if page == 'clone' else '' }}", "active" if active_page == 'clone' else "")
    content = content.replace("{{ 'active' if page == 'history' else '' }}", "active" if active_page == 'history' else "")
    return content


def register_routes(app):
    """注册页面路由"""
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """根路径重定向到 TTS 页面"""
        return RedirectResponse(url="/tts")
    
    @app.get("/tts", response_class=HTMLResponse)
    async def tts_page():
        """文字转语音页面"""
        return render_page(get_tts_page, 'tts')
    
    @app.get("/speakers", response_class=HTMLResponse)
    async def speakers_page():
        """音色库页面"""
        return render_page(get_speakers_page, 'speakers')
    
    @app.get("/clone", response_class=HTMLResponse)
    async def clone_page():
        """克隆声音页面"""
        return render_page(get_clone_page, 'clone')
    
    @app.get("/stt", response_class=HTMLResponse)
    async def stt_page():
        """语音转文字页面"""
        return render_page(get_stt_page, 'stt')
    
    @app.get("/history", response_class=HTMLResponse)
    async def history_page():
        """生成历史页面"""
        return render_page(get_history_page, 'history')

