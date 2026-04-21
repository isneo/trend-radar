# coding=utf-8
"""
报告渲染基础设施

集中管理 Jinja2 环境、CSS/JS 资源加载，供各 HTML 渲染模块共享。
CSS/JS 以字符串形式在渲染时内联到输出，保证邮件客户端（不认 <link>）兼容。
"""

from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape


_REPORT_DIR = Path(__file__).parent
_ASSETS_DIR = _REPORT_DIR / "assets"
_TEMPLATES_DIR = _REPORT_DIR / "templates"


def _load_asset(name: str) -> str:
    path = _ASSETS_DIR / name
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


REPORT_CSS: str = _load_asset("report.css")
REPORT_JS: str = _load_asset("report.js")


_env: Environment = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html", "j2", "html.j2")),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
    """渲染指定 Jinja2 模板

    Args:
        template_name: 模板文件名（相对 templates/ 目录，如 "report.html.j2"）
        context: 模板上下文变量

    Returns:
        渲染后的 HTML 字符串
    """
    ctx: Dict[str, Any] = {
        "report_css": REPORT_CSS,
        "report_js": REPORT_JS,
    }
    if context:
        ctx.update(context)
    template = _env.get_template(template_name)
    return template.render(**ctx)


def get_env() -> Environment:
    """返回共享的 Jinja2 Environment（调试/扩展用）"""
    return _env
