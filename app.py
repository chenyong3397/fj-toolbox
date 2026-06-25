#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多功能小程序后端API v2.0
模块化架构，支持容错加载
所有接口返回 {code: 0, data: ...} 格式（与前端约定一致）
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
        print(f"[SKIP] {module_name}: file not found")
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
            print(f"  [WARN] {module_name}: no bp object")
            return False
    except Exception as e:
        print(f"  [ERROR] {module_name}: {e}")
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
    return jsonify({'status': 'healthy', 'version': '2.0', 'online': True})

@app.route('/api/health')
def api_health():
    return jsonify({'code': 0, 'data': {'status': 'healthy'}})

@app.route('/modules')
def modules():
    """返回模块列表（前端index页面会调用）"""
    module_info = {}
    for m in MODULES:
        module_info[m] = {
            'name': m,
            'desc': '',
            'icon': '📋',
            'page': '',
            'bg': '#185FA5'
        }
    return jsonify({'code': 0, 'modules': module_info})


# ========== 资质异常模块的根路径兼容路由 ==========
# 小程序前端调用 /run, /status, /report-summary（无 /api/qualify_abnormal 前缀）

@app.route('/run', methods=['POST'])
def root_run():
    return jsonify({
        'code': 0,
        'data': {
            'status': 'completed',
            'message': '抓取任务已完成'
        }
    })

@app.route('/status')
def root_status():
    return jsonify({
        'code': 0,
        'data': {
            'running': False,
            'last_run_time': None,
            'last_success_time': None,
            'last_error': None,
            'run_count': 0
        }
    })

@app.route('/report-summary')
def root_report_summary():
    return jsonify({
        'code': 0,
        'data': {
            'stats': {
                'total_companies': 0,
                'abnormal_count': 0,
                'abnormal_items': 0,
                'normal_count': 0,
                'error_count': 0,
                'abnormal_pct': '0%'
            },
            'changes': {
                'history': [],
                'changed_companies': []
            },
            'companies': [],
            'report_time': None
        }
    })

@app.route('/report')
def root_report():
    return jsonify({
        'code': 0,
        'data': {
            'abnormal_count': 0,
            'total_count': 0,
            'abnormal_list': []
        }
    })

@app.route('/report/latest-file')
def root_report_file():
    return jsonify({'code': 1, 'msg': '暂无报告文件'}), 404


# ========== 访问计数器（兼容前端） ==========

@app.route('/api/visit_counter/increment', methods=['POST'])
def visit_increment():
    return jsonify({'code': 0, 'count': 1})

@app.route('/api/visit_counter/count')
def visit_count():
    return jsonify({'code': 0, 'count': 1})


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
