from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import List, Dict, Tuple, Any

import asyncio
import json
import os
import platform
import requests
import shutil

from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI

# Constants
DEEPSEEK_API_KEY = "API_KEY"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MAX_CONTENT_LENGTH = 1000
REQUEST_TIMEOUT = 10
AI_FOLDER_NAME = 'AI整理'

# Browser profile paths
BROWSER_PROFILES = ['Default', 'Profile 1', 'Profile 2', 'Profile 3']

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def get_browser_paths() -> List[Tuple[str, str]]:
    """
    Get bookmark file paths for different browsers based on the operating system.
    
    Returns:
        List[Tuple[str, str]]: List of tuples containing (browser_name, bookmark_path)
    """
    system = platform.system()
    user_home = str(Path.home())
    paths = []

    if system == 'Windows':
        chrome_base = os.path.join(user_home, 'AppData', 'Local', 'Google',
                                   'Chrome', 'User Data')
        edge_base = os.path.join(user_home, 'AppData', 'Local', 'Microsoft',
                                 'Edge', 'User Data')

        for profile in BROWSER_PROFILES:
            chrome_path = os.path.join(chrome_base, profile, 'Bookmarks')
            edge_path = os.path.join(edge_base, profile, 'Bookmarks')

            if os.path.exists(chrome_path):
                paths.append(('chrome', chrome_path))
            if os.path.exists(edge_path):
                paths.append(('edge', edge_path))

    elif system == 'Darwin':  # macOS
        chrome_base = os.path.join(user_home, 'Library', 'Application Support',
                                   'Google', 'Chrome')
        edge_base = os.path.join(user_home, 'Library', 'Application Support',
                                 'Microsoft Edge')

        for profile in BROWSER_PROFILES:
            chrome_path = os.path.join(chrome_base, profile, 'Bookmarks')
            edge_path = os.path.join(edge_base, profile, 'Bookmarks')

            if os.path.exists(chrome_path):
                paths.append(('chrome', chrome_path))
            if os.path.exists(edge_path):
                paths.append(('edge', edge_path))

        safari_path = os.path.join(user_home, 'Library', 'Safari',
                                   'Bookmarks.plist')
        if os.path.exists(safari_path):
            paths.append(('safari', safari_path))

    elif system == 'Linux':
        chrome_base = os.path.join(user_home, '.config', 'google-chrome')
        edge_base = os.path.join(user_home, '.config', 'microsoft-edge')

        for profile in BROWSER_PROFILES:
            chrome_path = os.path.join(chrome_base, profile, 'Bookmarks')
            edge_path = os.path.join(edge_base, profile, 'Bookmarks')

            if os.path.exists(chrome_path):
                paths.append(('chrome', chrome_path))
            if os.path.exists(edge_path):
                paths.append(('edge', edge_path))

    return paths


def parse_chrome_edge_bookmarks(bookmark_file: str) -> List[Dict[str, str]]:
    """
    Parse Chrome/Edge bookmark file and extract bookmark information.
    
    Args:
        bookmark_file: Path to the bookmark file
        
    Returns:
        List of dictionaries containing bookmark information
    """
    bookmarks = []
    try:
        with open(bookmark_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        def process_nodes(node: Dict[str, Any]) -> None:
            if node.get('type') == 'url':
                timestamp = int(node.get('date_added',
                                         0)) / 1000000 - 11644473600
                bookmarks.append({
                    'title':
                    node.get('name', ''),
                    'url':
                    node.get('url', ''),
                    'date_added':
                    datetime.fromtimestamp(timestamp).strftime(
                        '%Y-%m-%d %H:%M:%S'),
                    'browser':
                    'Chrome' if 'Chrome' in bookmark_file else 'Edge'
                })

            for child in node.get('children', []):
                process_nodes(child)

        for root in data['roots'].values():
            process_nodes(root)

    except Exception as e:
        print(f"Error parsing Chrome/Edge bookmarks: {e}")

    return bookmarks


def parse_safari_bookmarks(bookmark_file):
    bookmarks = []
    # Safari的书签文件是二进制plist格式，需要特殊处理
    try:
        import plistlib
        with open(bookmark_file, 'rb') as f:
            data = plistlib.load(f)

        def process_safari_nodes(node):
            if 'WebBookmarkType' in node:
                if node['WebBookmarkType'] == 'WebBookmarkTypeLeaf':
                    if 'URLString' in node:
                        bookmarks.append({
                            'title':
                            node.get('Title', ''),
                            'url':
                            node.get('URLString', ''),
                            'date_added':
                            datetime.fromtimestamp(
                                node.get('DateAdded',
                                         datetime.now().timestamp())).strftime(
                                             '%Y-%m-%d %H:%M:%S'),
                            'browser':
                            'Safari'
                        })

                children = node.get('Children', [])
                for child in children:
                    process_safari_nodes(child)

        process_safari_nodes(data)

    except Exception as e:
        print(f"Error parsing Safari bookmarks: {e}")

    return bookmarks


def get_url_content(url: str) -> dict:
    """获取URL内容并解析正文"""
    try:
        timeout = 10  # 10秒超时
        headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url,
                                headers=headers,
                                timeout=timeout,
                                verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 移除script、style等标签
            for script in soup(['script', 'style', 'header', 'footer', 'nav']):
                script.decompose()

            # 获取正文内容
            content = ''
            # 优先查找article标签
            article = soup.find('article')
            if article:
                content = article.get_text(strip=True)
            else:
                # 查找main标签
                main = soup.find('main')
                if main:
                    content = main.get_text(strip=True)
                else:
                    # 查找最长的<div>标签内容作为正文
                    divs = soup.find_all('div')
                    if divs:
                        content = max((d.get_text(strip=True) for d in divs),
                                      key=len)
                    else:
                        # 如果都没有,获取body下所有文本
                        content = soup.body.get_text(
                            strip=True) if soup.body else ''

            # 清理空白字符
            content = ' '.join(content.split())

            # 截取前1000个字符
            if len(content) > 1000:
                content = content[:1000] + '...'

            return {'content': content, 'status': 'success'}
        else:
            return {'status': 'error', 'error': f'HTTP {response.status_code}'}

    except requests.Timeout:
        return {'status': 'error', 'error': 'Timeout'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def get_tags_from_openai(content: dict) -> List[str]:
    """使用OpenAI API分析内容并生成标签"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role":
                    "system",
                    "content":
                    "你是一个打标签专家，根据用户输入的内容给出最合适的一个标签，用中文表达，标签要简约3-5个字，如果是error则返回错误"
                },
                {
                    "role": "user",
                    "content": content["content"]
                },
            ],
            stream=False)

        # 解析返回的标签
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error getting tags from OpenAI: {e}")
        return []


def async_route(f):

    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapped


@app.route('/api/analyze-bookmarks', methods=['POST'])
def analyze_bookmarks():
    browser_paths = get_browser_paths()
    all_bookmarks = []
    result = {
        'bookmarks': [],
        'stats': {
            'total': 0,
            'by_browser': {
                'Chrome': 0,
                'Edge': 0,
                'Safari': 0
            }
        }
    }

    # 获取所有浏览器的书签
    for browser, path in browser_paths:
        if browser in ['chrome', 'edge']:
            bookmarks = parse_chrome_edge_bookmarks(path)
            browser_name = 'Chrome' if browser == 'chrome' else 'Edge'
            result['stats']['by_browser'][browser_name] += len(bookmarks)
            all_bookmarks.extend(bookmarks)
        elif browser == 'safari':
            bookmarks = parse_safari_bookmarks(path)
            result['stats']['by_browser']['Safari'] = len(bookmarks)
            all_bookmarks.extend(bookmarks)

    # 更新总数
    result['stats']['total'] = len(all_bookmarks)

    # 按时间排序书签
    all_bookmarks.sort(key=lambda x: x['date_added'], reverse=True)

    # 异步获取URL内容
    contents = []
    for bookmark in all_bookmarks:
        print(bookmark['url'])
        if bookmark['url'].startswith(('http://', 'https://')):
            contents.append(get_url_content(bookmark['url']))

    for bookmark, content in zip(all_bookmarks[:10], contents):
        if content and content['status'] == 'success':
            bookmark['page_content'] = content
            # 获取AI标签
            tags = get_tags_from_openai(content)
            bookmark['ai_tags'] = tags
        else:
            bookmark['ai_tags'] = ["error"]

    result['bookmarks'] = all_bookmarks
    return jsonify(result)


def remove_bookmark_by_url(bookmark_tree, url_to_remove, in_ai_folder=False):
    """
    递归删除书签树中指定URL的书签，但跳过AI整理文件夹中的书签
    
    Args:
        bookmark_tree: 书签树节点
        url_to_remove: 要删除的URL
        in_ai_folder: 是否在AI整理文件夹中
    
    Returns:
        tuple: (是否保留该节点, 更新后的节点)
    """
    # 如果是书签节点
    if bookmark_tree.get('type') == 'url':
        # 如果在AI整理文件夹中，保留书签
        if in_ai_folder:
            return True, bookmark_tree
        if bookmark_tree.get('url') == url_to_remove:
            print(bookmark_tree.get('url'))
        # 如果URL匹配且不在AI整理文件夹中，删除书签
        return bookmark_tree.get('url') != url_to_remove, bookmark_tree

    # 如果是文件夹节点
    if bookmark_tree.get('type') == 'folder' and 'children' in bookmark_tree:
        # 检查是否是AI整理文件夹
        is_ai_folder = bookmark_tree.get('name') == 'AI整理'
        current_in_ai = is_ai_folder or in_ai_folder

        # 处理所有子节点
        new_children = []
        for child in bookmark_tree['children']:
            keep_child, updated_child = remove_bookmark_by_url(
                child, url_to_remove, current_in_ai)
            if keep_child:
                new_children.append(updated_child)

        bookmark_tree['children'] = new_children
        return True, bookmark_tree

    return True, bookmark_tree


@app.route('/api/organize-bookmarks', methods=['POST'])
def organize_bookmarks():
    try:
        browser_paths = get_browser_paths()
        results = {}

        bookmarks_data = request.json.get('bookmarks', [])

        # 按标签对书签进行分组，同时记录URL以便后续删除
        bookmarks_by_tag = {}
        urls_to_remove = set()
        for bookmark in bookmarks_data:
            tag = bookmark.get('ai_tags')
            if not tag:
                continue
            if isinstance(tag, list):
                tag = tag[0]
            if tag not in bookmarks_by_tag:
                bookmarks_by_tag[tag] = []
            bookmarks_by_tag[tag].append(bookmark)
            urls_to_remove.add(bookmark['url'])

        for browser, path in browser_paths:
            if browser in ['chrome', 'edge']:
                try:
                    browser_name = 'Chrome' if browser == 'chrome' else 'Edge'
                    results[browser] = {
                        'success': False,
                        'message': f'请先关闭 {browser_name} 浏览器'
                    }

                    backup_path = path + '.bak'
                    shutil.copy2(path, backup_path)

                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    bookmark_bar = data['roots']['bookmark_bar']
                    current_timestamp = int(datetime.now().timestamp() *
                                            1000000 + 11644473600)

                    # 查找现有的AI整理文件夹
                    ai_folder = None
                    for child in bookmark_bar['children']:
                        if child.get('type') == 'folder' and child.get(
                                'name') == 'AI整理':
                            ai_folder = child
                            break

                    # 如果没有找到AI整理文件夹，创建一个新的
                    if not ai_folder:
                        ai_folder = {
                            'date_added': str(current_timestamp),
                            'date_modified': str(current_timestamp),
                            'id':
                            str(len(bookmark_bar.get('children', [])) + 1),
                            'name': 'AI整理',
                            'type': 'folder',
                            'children': []
                        }
                        bookmark_bar['children'].append(ai_folder)

                    # 处理每个标签
                    for tag, tag_bookmarks in bookmarks_by_tag.items():
                        # 在AI整理文件夹中查找现有的标签文件夹
                        tag_folder = None
                        for child in ai_folder['children']:
                            if child.get('type') == 'folder' and child.get(
                                    'name') == tag:
                                tag_folder = child
                                break

                        # 如果没有找到标签文件夹，创建一个新的
                        if not tag_folder:
                            tag_folder = {
                                'date_added': str(current_timestamp),
                                'date_modified': str(current_timestamp),
                                'id':
                                f"{ai_folder['id']}-{len(ai_folder['children'])}",
                                'name': tag,
                                'type': 'folder',
                                'children': []
                            }
                            ai_folder['children'].append(tag_folder)

                        # 添加书签到标签文件夹，但跳过已存在的URL
                        existing_urls = {
                            child.get('url')
                            for child in tag_folder['children']
                            if child.get('type') == 'url'
                        }

                        for bookmark in tag_bookmarks:
                            # 如果URL已存在，跳过
                            if bookmark['url'] in existing_urls:
                                continue

                            bookmark_entry = {
                                'date_added': str(current_timestamp),
                                'id':
                                f"{tag_folder['id']}-{len(tag_folder['children'])}",
                                'name': bookmark['title'],
                                'type': 'url',
                                'url': bookmark['url']
                            }
                            tag_folder['children'].append(bookmark_entry)

                    # 添加书签到AI整理文件夹后，删除原始位置的书签
                    for url in urls_to_remove:
                        _, updated_bookmark_bar = remove_bookmark_by_url(
                            bookmark_bar, url)
                        bookmark_bar = updated_bookmark_bar  # 更新书签栏

                    # 更新修改时间
                    data['roots']['bookmark_bar'] = bookmark_bar
                    data['roots']['bookmark_bar']['date_modified'] = str(
                        current_timestamp)
                    data['roots']['sync_transaction_version'] = str(
                        current_timestamp)

                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    results[browser] = {
                        'success': True,
                        'message': f'成功整理书签。请重启 {browser_name} 浏览器以查看更改。'
                    }

                except Exception as e:
                    results[browser] = {'success': False, 'message': str(e)}

        return jsonify({
            'status': 'success',
            'message': '书签整理完成，请重启浏览器查看更改',
            'details': results
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'整理书签时发生错误: {str(e)}'
        }), 500


@app.route('/')
def index():
    return app.send_static_file('index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
