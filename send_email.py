#!/usr/bin/env python3
"""
AI 资讯日报生成器
每天抓取多个来源的AI资讯，汇总发送邮件（全中文）
数据源：36氪 · IT之家 · 量子位 · Hugging Face Blog
"""

import smtplib
import ssl
import re
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict

# ============== 配置区 ==============
import os
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "blc1141818036@163.com")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "blc1141818036@163.com")
SMTP_AUTH_CODE = os.environ.get("SMTP_AUTH_CODE", "JNbHVWahT3VSkN9Q")

# 本地用代理，GitHub Actions不需要
PROXY = os.environ.get("HTTP_PROXY", "")  # GitHub Actions中自动为空
# ===================================

if PROXY:
    import urllib.request
    proxy_handler = urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY})
    _opener = urllib.request.build_opener(proxy_handler)
    def _get(url: str, headers: dict = None) -> bytes:
        defaults = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        if headers:
            defaults.update(headers)
        req = urllib.request.Request(url, headers=defaults)
        return _opener.open(req, timeout=20).read()
else:
    import urllib.request
    def _get(url: str, headers: dict = None) -> bytes:
        defaults = {'User-Agent': 'Mozilla/5.0'}
        if headers:
            defaults.update(headers)
        req = urllib.request.Request(url, headers=defaults)
        return urllib.request.urlopen(req, timeout=20).read()


AI_KEYWORDS = ['AI', '人工智能', 'LLM', 'GPT', '大模型', '智能', '机器人',
                '芯片', '算法', '深度学习', '自动驾驶', '英伟达', 'OpenAI',
                '阿里', '百度', '字节', '模型', 'ChatGPT', 'Gemini', 'Claude',
                '神经网络', '机器学习', 'Scaling', 'AGI', '具身', '视频生成',
                '文生图', '多模态', '推理', '算力', 'transformer', 'diffusion',
                '开源', '推理', 'agent', 'RAG', '向量', '微调', 'RLHF']


def fetch_36kr() -> List[Dict]:
    """36氪 AI 相关新闻"""
    url = "https://www.36kr.com/feed"
    try:
        content = _get(url).decode('utf-8')
        items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
        results = []
        for item in items:
            title_m = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item)
            link_m = re.search(r'<link><!\[CDATA\[(.*?)\]\]></link>', item)
            date_m = re.search(r'<pubDate>(.*?)</pubDate>', item)
            if title_m:
                title = title_m.group(1).strip()
                if any(k.lower() in title.lower() for k in AI_KEYWORDS):
                    results.append({
                        'source': '36氪',
                        'title': title,
                        'url': link_m.group(1) if link_m else '',
                        'date': date_m.group(1)[:10] if date_m else '',
                    })
        return results[:10]
    except Exception as e:
        print(f"[36kr] 获取失败: {e}")
        return []


def fetch_ithome() -> List[Dict]:
    """IT之家 AI 相关新闻"""
    url = "https://www.ithome.com/rss/"
    try:
        content = _get(url).decode('utf-8')
        titles = re.findall(r'<item>.*?<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>.*?<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>', content, re.DOTALL)
        results = []
        for title, link in titles:
            title = title.strip()
            if any(k.lower() in title.lower() for k in AI_KEYWORDS):
                results.append({
                    'source': 'IT之家',
                    'title': title,
                    'url': link.strip(),
                    'date': '',
                })
        return results[:10]
    except Exception as e:
        print(f"[IT之家] 获取失败: {e}")
        return []


def fetch_ifanr() -> List[Dict]:
    """爱范儿 AI 相关新闻"""
    url = "https://www.ifanr.com/feed"
    try:
        content = _get(url).decode('utf-8')
        items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
        results = []
        for item in items:
            title_m = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item)
            link_m = re.search(r'<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>', item)
            date_m = re.search(r'<pubDate>(.*?)</pubDate>', item)
            if title_m:
                title = title_m.group(1).strip()
                if any(k.lower() in title.lower() for k in AI_KEYWORDS):
                    results.append({
                        'source': '爱范儿',
                        'title': title,
                        'url': link_m.group(1) if link_m else '',
                        'date': date_m.group(1)[:10] if date_m else '',
                    })
        return results[:10]
    except Exception as e:
        print(f"[爱范儿] 获取失败: {e}")
        return []


def fetch_qbitai() -> List[Dict]:
    """量子位 AI 新闻（从官网抓取）"""
    url = "https://www.qbitai.com/"
    try:
        content = _get(url).decode('utf-8')
        # 匹配文章链接和标题：<a href="https://www.qbitai.com/2026/04/xxxx.html">标题</a>
        pattern = r'<a[^>]*href="(https?://www\.qbitai\.com/\d+/\d+/[^"]+\.html)"[^>]*>\s*(?:<[^>]+>)*\s*([^<]{8,})'
        matches = re.findall(pattern, content)
        seen = set()
        results = []
        for link, title in matches:
            title = title.strip()
            if title not in seen and len(title) > 5:
                seen.add(title)
                results.append({
                    'source': '量子位',
                    'title': title,
                    'url': link,
                    'date': '',
                })
        return results[:12]
    except Exception as e:
        print(f"[量子位] 获取失败: {e}")
        return []


def fetch_huggingface() -> List[Dict]:
    """Hugging Face Blog（开源AI前沿）"""
    url = "https://huggingface.co/blog/feed.xml"
    try:
        content = _get(url).decode('utf-8')
        items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
        if not items:
            # Atom格式
            items = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)
        results = []
        for item in items:
            title_m = re.search(r'<title[^>]*>(.*?)</title>', item, re.DOTALL)
            link_m = re.search(r'<link[^>]*href="([^"]+)"', item)
            if not link_m:
                link_m = re.search(r'<link>(.*?)</link>', item)
            date_m = re.search(r'<pubDate>(.*?)</pubDate>', item)
            if not date_m:
                date_m = re.search(r'<updated>(.*?)</updated>', item)
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
                results.append({
                    'source': 'HuggingFace',
                    'title': title,
                    'url': link_m.group(1) if link_m else '',
                    'date': date_m.group(1)[:10] if date_m else '',
                })
        return results[:8]
    except Exception as e:
        print(f"[HuggingFace] 获取失败: {e}")
        return []


def generate_digest() -> str:
    """生成全中文资讯日报"""
    today = datetime.now().strftime('%Y-%m-%d')

    kr36 = fetch_36kr()
    ithome = fetch_ithome()
    qbitai = fetch_qbitai()
    hf = fetch_huggingface()

    total = len(kr36) + len(ithome) + len(qbitai) + len(hf)

    html = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 850px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #1a73e8;">🤖 AI 资讯日报</h1>
        <p style="color: #666;">📅 {today} &nbsp;|&nbsp; 共 {total} 条 &nbsp;|&nbsp; 来源：36氪 · IT之家 · 量子位 · HuggingFace</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    """

    sections = [
        ('📰 36氪 AI 动态', '#ff6d00', kr36),
        ('💻 IT之家 AI 动态', '#e91e63', ithome),
        ('🔬 量子位 AI 动态', '#7c4dff', qbitai),
        ('🤗 HuggingFace 动态', '#ff9800', hf),
    ]

    for title, color, data in sections:
        html += f'<h2 style="color: {color};">{title}</h2>'
        if data:
            html += '<ul style="line-height:2.0;">'
            for n in data:
                date_span = f' <span style="color:#999;font-size:12px;">{n["date"]}</span>' if n.get("date") else ''
                html += f'<li><a href="{n["url"]}" style="text-decoration:none;color:#333;font-size:15px;">{n["title"]}</a>{date_span}</li>'
            html += '</ul>'
        else:
            html += '<p style="color:#999;">今日无数据</p>'

    html += f"""
        <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
        <p style="color:#999;font-size:12px;">
            本日报由 AI 自动生成 &nbsp;|&nbsp; 抓取时间: {datetime.now().strftime('%H:%M:%S')}
        </p>
    </body></html>
    """
    return html


def send_email(html_content: str) -> bool:
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🤖 AI 资讯日报 {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.163.com", 465, context=context) as server:
            server.login(EMAIL_SENDER, SMTP_AUTH_CODE)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print(f"[邮件] 发送成功 -> {EMAIL_RECEIVER}")
        return True
    except Exception as e:
        print(f"[邮件] 发送失败: {e}")
        return False


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始抓取AI资讯...")
    digest = generate_digest()

    # 保存预览
    with open('/root/ai_news_digest/preview.html', 'w', encoding='utf-8') as f:
        f.write(digest)
    print("[预览] 已保存到 /root/ai_news_digest/preview.html")

    send_email(digest)


if __name__ == "__main__":
    main()
