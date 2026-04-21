# coding=utf-8
"""
RSS HTML 报告渲染模块

提供 RSS 订阅内容的 HTML 格式报告生成功能
"""

from datetime import datetime
from typing import Dict, List, Optional, Callable

from trendradar.report.helpers import html_escape
from trendradar.report.renderer import render as _render_template, _load_asset

_RSS_CSS = _load_asset("rss_report.css")
_RSS_JS = _load_asset("rss_report.js")


def render_rss_html_content(
    rss_items: List[Dict],
    total_count: int,
    feeds_info: Optional[Dict[str, str]] = None,
    *,
    get_time_func: Optional[Callable[[], datetime]] = None,
) -> str:
    """渲染 RSS HTML 内容

    Args:
        rss_items: RSS 条目列表，每个条目包含:
            - title: 标题
            - feed_id: RSS 源 ID
            - feed_name: RSS 源名称
            - url: 链接
            - published_at: 发布时间
            - summary: 摘要（可选）
            - author: 作者（可选）
        total_count: 条目总数
        feeds_info: RSS 源 ID 到名称的映射
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now）

    Returns:
        渲染后的 HTML 字符串
    """
    html = """
        <div class="container">
            <div class="header">
                <div class="save-buttons">
                    <button class="save-btn" onclick="saveAsImage()">保存为图片</button>
                </div>
                <div class="header-title">RSS 订阅内容</div>
                <div class="header-info">
                    <div class="info-item">
                        <span class="info-label">订阅条目</span>
                        <span class="info-value">"""

    html += f"{total_count} 条"

    html += """</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">生成时间</span>
                        <span class="info-value">"""

    # 使用提供的时间函数或默认 datetime.now
    if get_time_func:
        now = get_time_func()
    else:
        now = datetime.now()
    html += now.strftime("%m-%d %H:%M")

    html += """</span>
                    </div>
                </div>
            </div>

            <div class="content">"""

    # 按 feed_id 分组
    feeds_map: Dict[str, List[Dict]] = {}
    for item in rss_items:
        feed_id = item.get("feed_id", "unknown")
        if feed_id not in feeds_map:
            feeds_map[feed_id] = []
        feeds_map[feed_id].append(item)

    # 渲染每个 RSS 源的内容
    for feed_id, items in feeds_map.items():
        feed_name = items[0].get("feed_name", feed_id) if items else feed_id
        if feeds_info and feed_id in feeds_info:
            feed_name = feeds_info[feed_id]

        escaped_feed_name = html_escape(feed_name)

        html += f"""
                <div class="feed-group">
                    <div class="feed-header">
                        <div class="feed-name">{escaped_feed_name}</div>
                        <div class="feed-count">{len(items)} 条</div>
                    </div>"""

        for item in items:
            escaped_title = html_escape(item.get("title", ""))
            url = item.get("url", "")
            published_at = item.get("published_at", "")
            author = item.get("author", "")
            summary = item.get("summary", "")

            html += """
                    <div class="rss-item">
                        <div class="rss-meta">"""

            if published_at:
                html += f'<span class="rss-time">{html_escape(published_at)}</span>'

            if author:
                html += f'<span class="rss-author">by {html_escape(author)}</span>'

            html += """
                        </div>
                        <div class="rss-title">"""

            if url:
                escaped_url = html_escape(url)
                html += f'<a href="{escaped_url}" target="_blank" class="rss-link">{escaped_title}</a>'
            else:
                html += escaped_title

            html += """
                        </div>"""

            if summary:
                escaped_summary = html_escape(summary)
                html += f"""
                        <p class="rss-summary">{escaped_summary}</p>"""

            html += """
                    </div>"""

        html += """
                </div>"""

    html += """
            </div>

            <div class="footer">
                <div class="footer-content">
                    由 <span class="project-name">TrendRadar</span> 生成 ·
                    <a href="https://github.com/sansan0/TrendRadar" target="_blank" class="footer-link">
                        GitHub 开源项目
                    </a>
                </div>
            </div>
        </div>
    """

    return _render_template(
        'rss_report.html.j2',
        {
            'body_html': html,
            'page_title': 'RSS 订阅报告',
            'report_css': _RSS_CSS,
            'report_js': _RSS_JS,
        },
    )