import markdown
import logging
import re
from bs4 import BeautifulSoup
from exchangelib import HTMLBody
from .config import EWS_EMAIL_SIGNATURE

logger = logging.getLogger("ews_mcp")

def markdown_to_html(md_text: str) -> str:
    """Convert Markdown to HTML with extensions for better email compatibility."""
    # 阶段 1: 文本清洗 (Sanitization Layer)
    # 处理大模型/MCP传输中常见的双重转义问题
    txt = md_text.replace('\\\\n', '\n').replace('\\n', '\n')
    # 统一换行符
    txt = txt.replace('\r\n', '\n').replace('\r', '\n')
    # 移除首尾多余空白
    txt = txt.strip()

    # 阶段 2: 增强型解析 (Enhanced Markdown Parser)
    # nl2br: 允许单回车换行，符合写信直觉
    # extra: 支持表格、列表等
    html = markdown.markdown(txt, extensions=['extra', 'nl2br', 'sane_lists'])
    return html

def inject_inline_styles(html: str) -> str:
    """Use BeautifulSoup to inject compatible inline styles for various email clients."""
    soup = BeautifulSoup(html, "html.parser")
    
    # 定义高兼容性的内联样式表
    STYLES = {
        'p': 'margin: 0 0 12px 0; line-height: 1.6;',
        'ul': 'margin: 0 0 12px 24px; padding: 0;',
        'ol': 'margin: 0 0 12px 24px; padding: 0;',
        'li': 'margin-bottom: 6px; line-height: 1.6;',
        'h1': 'margin: 20px 0 12px 0; font-size: 22px; font-weight: bold; color: #111111;',
        'h2': 'margin: 18px 0 10px 0; font-size: 18px; font-weight: bold; color: #333333;',
        'h3': 'margin: 16px 0 8px 0; font-size: 16px; font-weight: bold; color: #444444;',
        'blockquote': 'border-left: 4px solid #dfe2e5; margin: 0 0 12px 0; padding: 0 1em; color: #6a737d;',
        'code': 'background-color: #f6f8fa; padding: 2px 4px; border-radius: 3px; font-family: monospace;',
        'strong': 'color: #111111; font-weight: bold;'
    }
    
    # 注入样式
    for tag_name, style in STYLES.items():
        for element in soup.find_all(tag_name):
            existing_style = element.get('style', '')
            if existing_style:
                element['style'] = f"{style} {existing_style}"
            else:
                element['style'] = style
                
    return str(soup)

def build_email_body(content: str, use_signature: bool = True) -> HTMLBody:
    """Build the final HTMLBody with full pipeline: cleaning, parsing, inlining and signature."""
    # 获取初步 HTML 内容
    raw_html = markdown_to_html(content)
    
    # 注入内联 CSS
    styled_html = inject_inline_styles(raw_html)
    
    # 组装签名
    signature_html = ""
    if use_signature and EWS_EMAIL_SIGNATURE:
        sig_lines = EWS_EMAIL_SIGNATURE.strip().split('\n')
        sig_html_lines = []
        for line in sig_lines:
            line_txt = line.strip()
            if line_txt == "---":
                sig_html_lines.append('<hr style="border:none;border-top:1px solid #dddddd;margin:8px 0;" />')
            elif line_txt:
                sig_html_lines.append(f'<div style="font-family: Arial, sans-serif; font-size: 12px; color: #888888; line-height: 1.5;">{line_txt}</div>')
        
        signature_html = f'<div style="margin-top:24px;padding-top:14px;border-top:1px solid #eeeeee;">{"".join(sig_html_lines)}</div>'
    
    # 阶段 4: 全局自适应包装 (Global Wrapper)
    # 使用通用的现代化字体栈
    font_stack = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol"'
    
    final_html = f"""
    <div style="font-family: {font_stack}; font-size: 14.5px; color: #333333; line-height: 1.7; max-width: 800px; margin: 0 auto;">
        {styled_html}
        {signature_html}
    </div>
    """
    
    # exchangelib 会自动处理 HTMLBody 的封装
    return HTMLBody(final_html)
