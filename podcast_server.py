from flask import Flask, render_template_string, send_from_directory, make_response, request
import os
import logging
import mimetypes
from config import episodes_dir, port, log_level, log_format, log_datefmt

# 配置日志记录
logging.basicConfig(level=log_level, format=log_format, datefmt=log_datefmt)

app = Flask(__name__)

RSS_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Your Podcast Name</title>
        <link>{{ domain }}podcast</link>
        <description>This is a description of your podcast.</description>
        {% for file in files %}
        <item>
            <title>{{ file['title'] }}</title>
            <link>{{ file['url'] }}</link>
            <description>Description for this episode.</description>
            <enclosure url="{{ file['url'] }}" length="{{ file['size'] }}" type="{{ file['type'] }}"/>
            <guid>{{ file['url'] }}</guid>
        </item>
        {% endfor %}
    </channel>
</rss>
"""


@app.route('/podcast/')
def podcast_feed():
    real_ip = get_real_ip()
    domain = request.host_url  # 动态获取访问的域名或 IP
    logging.info(f"{real_ip} -> {domain} Generating RSS feed from directory: {episodes_dir}")
    files = []
    if os.path.exists(episodes_dir):
        file_list = sorted(os.listdir(episodes_dir), key=lambda f: os.path.getmtime(os.path.join(episodes_dir, f)), reverse=True)
        for filename in file_list:
            if filename.startswith('.'):
                continue
            filetype = filename.split(".")[1]
            if filetype in ['aac', 'm4a', 'wav', 'mp3', 'webm', 'mp4']:  # 支持多种音频格式
                filepath = os.path.join(episodes_dir, filename)
                file_url = f"{domain}podcast/music/{filename}"
                file_size = os.path.getsize(filepath)
                mime_type, _ = mimetypes.guess_type(filepath)  # 获取 MIME 类型
                if not mime_type:
                    mime_type = "audio/mpeg"  # 兜底默认值
                files.append({
                    'title': os.path.splitext(filename)[0],
                    'url': file_url,
                    'size': file_size,
                    'mtime': os.path.getmtime(filepath),
                    'type': mime_type  # 添加 type 字段
                })

        # 按修改时间倒序排序（最新的文件排在最前面）
        files.sort(key=lambda x: x['mtime'], reverse=True)

    response = make_response(render_template_string(RSS_TEMPLATE, files=files, domain=domain))
    response.headers['Content-Type'] = 'application/rss+xml; charset=utf-8'
    logging.debug(f"Generated RSS feed with {len(files)} items")
    return response


def get_real_ip():
    # 先检查 'X-Forwarded-For' 头部字段
    real_ip = request.headers.get('X-Forwarded-For')
    if not real_ip:
        # 如果没有 'X-Forwarded-For' 头部，使用 'X-Real-IP' 或直接获取请求来源
        real_ip = request.headers.get('X-Real-IP', request.remote_addr)

    return real_ip


@app.route('/podcast/music/<path:filename>')
def serve_episodes(filename):
    real_ip = get_real_ip()
    domain = request.host_url  # 动态获取访问的域名或 IP
    logging.debug(f"{real_ip} -> {domain} Attempting to serve file: {episodes_dir}{filename}")
    if not os.path.exists(os.path.join(episodes_dir, filename)):
        logging.error(f"File not found: {filename}")
        return "File not found", 404
    
    try:
        return send_from_directory(episodes_dir, filename)
    except Exception as e:
        logging.error(f"Error serving file {filename}: {str(e)}")
        return "Internal Server Error", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)