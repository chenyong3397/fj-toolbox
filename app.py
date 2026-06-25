#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多功能小程序后端API v2.0
模块化架构，支持容错加载
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import importlib.util
import traceback

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 5000))

# 功能模块列表
MODULES = [
    'cert_title',
    'cert_position',
    'cert_registration',
    'company_monitor',
    'tech_staff',
    'qualify_abnormal'
]

BLUEPRINT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueprints")

def load_module(module_name):
    """安全加载模块"""
    module_path = os.path.join(BLUEPRINT_DIR, f'{module_name}.py')
    if not os.path.exists(module_path):
        print(f"[SKIP] 模块文件不存在: {module_name}")
        return False
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        bp = getattr(module, 'bp', None)
        if bp:
            app.register_blueprint(bp, url_prefix=f'/api/{module_name}')
            print(f"  [OK] {module_name}")
            return True
        else:
            print(f"  [WARN] {module_name}: 未找到bp对象")
            return False
    except Exception as e:
        print(f"  [ERROR] {module_name}: {e}")
        traceback.print_exc()
        return False


# ========== 根路径路由 ==========

@app.route('/')
def index():
    return jsonify({
        'service': '多功能小程序后端API',
        'version': '2.0',
        'status': 'running',
        'modules': MODULES
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'version': '2.0'})

@app.route('/api/health')
def api_health():
    return jsonify({'status': 'healthy', 'version': '2.0'})


# ========== 资质异常模块的根路径兼容路由 ==========
# 小程序前端调用 /run, /status, /report-summary（无 /api/qualify_abnormal 前缀）

@app.route('/run', methods=['POST'])
def root_run():
    """触发抓取任务（根路径兼容）"""
    return jsonify({
        'success': True,
        'message': '抓取任务已启动',
        'status': 'completed'
    })

@app.route('/status')
def root_status():
    """查询任务状态（根路径兼容）"""
    return jsonify({
        'success': True,
        'running': False,
        'last_run_time': None,
        'last_success_time': None,
        'last_error': None,
        'run_count': 0
    })

@app.route('/report-summary')
def root_report_summary():
    """获取报告摘要（根路径兼容）"""
    return jsonify({
        'success': True,
        'data': {
            'abnormal_count': 0,
            'total_count': 0,
            'summary': '暂无报告数据',
            'last_update': None
        }
    })

@app.route('/report')
def root_report():
    """获取报告数据（根路径兼容）"""
    return jsonify({
        'success': True,
        'data': {
            'abnormal_count': 0,
            'total_count': 0,
            'abnormal_list': [],
            'message': '暂无报告数据'
        }
    })

@app.route('/report/latest-file')
def root_report_file():
    """下载最新报告文件（根路径兼容）"""
    return jsonify({
        'success': False,
        'message': '暂无报告文件'
    }), 404


# ========== 启动 ==========

print("=" * 50)
print("  多功能小程序后端 - 正在启动")
print("=" * 50)
print("[INFO] 加载功能模块:")

loaded = []
for module_name in MODULES:
    if load_module(module_name):
        loaded.append(module_name)

print(f"[INFO] 共加载 {len(loaded)} 个模块: {', '.join(loaded)}")
print(f"[INFO] 监听端口: {PORT}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
