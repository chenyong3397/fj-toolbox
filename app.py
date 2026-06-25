#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多功能小程序后端 - 主入口
自动发现并注册 blueprints/ 目录下所有功能模块

启动: python app.py
默认端口: 8080（可在 config.ini [api] 中修改）
"""

import sys
import os
import importlib.util
import logging
from datetime import datetime

# 强制 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    from flask import Flask, jsonify
    from flask_cors import CORS
except ImportError:
    print("[ERROR] 缺少依赖: flask, flask-cors")
    print("请运行: pip install flask flask-cors")
    sys.exit(1)

# ========== 加载配置 ==========
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
API_TOKEN = 'fj-qualify-2026'
PORT = int(os.environ.get('PORT', 5678))
HOST = '0.0.0.0'
WX_APPID = ''
WX_SECRET = ''


def load_config():
    global API_TOKEN, PORT, WX_APPID, WX_SECRET
    try:
        import configparser
        cp = configparser.ConfigParser()
        cp.read(CONFIG_FILE, encoding='utf-8')
        if cp.has_section('api'):
            API_TOKEN = cp.get('api', 'token', fallback=API_TOKEN)
            try:
                PORT = cp.getint('api', 'port', fallback=PORT)
            except Exception:
                PORT = int(os.environ.get('PORT', 5678))
            WX_APPID = cp.get('api', 'wx_appid', fallback='')
            WX_SECRET = cp.get('api', 'wx_secret', fallback='')
        print(f"[CONFIG] Token加载成功, Port={PORT}")
        if WX_APPID:
            print(f"[CONFIG] 微信小程序AppID已配置: {WX_APPID[:8]}...")
    except Exception as e:
        print(f"[WARN] 读取配置失败，使用默认: {e}")


load_config()

# ========== 创建 Flask 应用 ==========
app = Flask(__name__)
CORS(app, origins='*')

# ========== 自动发现并注册 Blueprint ==========
BLUEPRINT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueprints")
REGISTERED = []


def discover_blueprints():
    """自动发现 blueprints/ 目录下所有 .py 文件并注册"""
    if not os.path.isdir(BLUEPRINT_DIR):
        print(f"[WARN] blueprints 目录不存在: {BLUEPRINT_DIR}")
        return

    for filename in sorted(os.listdir(BLUEPRINT_DIR)):
        if not filename.endswith('.py') or filename == '__init__.py':
            continue
        module_name = filename[:-3]  # 去掉 .py
        module_path = os.path.join(BLUEPRINT_DIR, filename)
        url_prefix = f'/api/{module_name}'

        try:
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找模块中的 Blueprint 对象
            bp = getattr(module, 'bp', None)
            if bp is None:
                # 尝试按模块名查找
                bp = getattr(module, module_name, None)

            if bp is not None and hasattr(bp, 'name'):
                # 强制设置 url_prefix（以 /api/模块名 格式）
                bp.url_prefix = url_prefix
                app.register_blueprint(bp)
                REGISTERED.append(module_name)
                print(f"  [OK] 注册模块: {module_name:20s} -> {url_prefix}")
            else:
                print(f"  [SKIP] {filename}: 未找到 Blueprint 对象")

        except Exception as e:
            print(f"  [ERROR] 加载 {filename} 失败: {e}")


# 执行自动发现
print(f"{'=' * 50}")
print(f"  多功能小程序后端 - 正在启动")
print(f"{'=' * 50}")
print(f"[INFO] 发现并注册功能模块:")
discover_blueprints()

# 为 qualify_abnormal 模块注册根路径兼容（/run, /status 等）
try:
    import blueprints.qualify_abnormal as qa_module
    if hasattr(qa_module, 'register_root_routes'):
        qa_module.register_root_routes(app)
        print(f"  [OK] 已注册根路径兼容路由（/run, /status, /report ...）")
except Exception as e:
    print(f"  [WARN] 注册根路径兼容失败（不影响正常使用）: {e}")

print(f"[INFO] 共注册 {len(REGISTERED)} 个功能模块: {', '.join(REGISTERED)}")


# ========== 全局路由 ==========

@app.route('/')
def index():
    """服务说明（根路径）"""
    endpoints = {}
    for rule in app.url_map.iter_rules():
        if rule.rule != '/' and '<' not in rule.rule:
            methods = ', '.join(sorted([m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]))
            endpoints[f"{methods} {rule.rule}"] = app.view_functions[rule.endpoint].__doc__ or ''

    return jsonify({
        'service': '多功能小程序后端API',
        'version': '2.0',
        'status': 'running',
        'modules': REGISTERED,
        'endpoints': endpoints
    })


@app.route('/health')
def health():
    """健康检查（无需Token）"""
    return jsonify({'code': 0, 'online': True, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})


@app.route('/modules')
def list_modules():
    """列出所有已注册的功能模块"""
    modules_info = {}
    for name in REGISTERED:
        try:
            spec = importlib.util.spec_from_file_location(
                name, os.path.join(BLUEPRINT_DIR, f'{name}.py')
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # 尝试获取 info 接口
            info_func = getattr(module, 'get_info', None)
            if info_func:
                modules_info[name] = info_func()
            else:
                modules_info[name] = {'name': name, 'url_prefix': f'/api/{name}'}
        except Exception as e:
            modules_info[name] = {'name': name, 'error': str(e)}

    return jsonify({'code': 0, 'modules': modules_info})


# ========== 启动 ==========
if __name__ == '__main__':
    print(f"{'=' * 50}")
    print(f"  监听地址 : http://{HOST}:{PORT}")
    print(f"  Token    : {API_TOKEN}")
    print(f"  功能模块 : {', '.join(REGISTERED) if REGISTERED else '(无)'}")
    print(f"  接口列表 :")
    print(f"    GET  /               - 服务说明")
    print(f"    GET  /health         - 健康检查（无需Token）")
    print(f"    GET  /modules        - 列出所有功能模块")
    for name in REGISTERED:
        print(f"    --- /api/{name}/...   - {name} 功能接口")
    try:
        import urllib.request
        wan_ip = urllib.request.urlopen('http://4.ipw.cn', timeout=3).read().decode().strip()
    except Exception:
        wan_ip = '(获取公网IP失败，请检查网络)'
    print(f"    微信小程序访问地址: http://{wan_ip}:{PORT}")
    print(f"{'=' * 50}")
    print()

    app.run(host=HOST, port=PORT, debug=False, threaded=True)
