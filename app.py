#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多功能小程序后端API - 改进版
支持模块化加载，具有容错能力
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import importlib.util

app = Flask(__name__)
CORS(app)

# 配置
PORT = int(os.environ.get('PORT', 5000))

# 功能模块列表
MODULES = [
    'cert_title',      # 职称证查询
    'cert_position',   # 岗位证查询
    'cert_registration', # 注册证查询
    'company_monitor', # 企业审批
    'tech_staff',      # 技术人员
    'qualify_abnormal' # 资质异常
]

def load_module(module_name):
    """安全加载模块"""
    try:
        spec = importlib.util.spec_from_file_location(
            module_name,
            os.path.join(os.path.dirname(__file__), 'blueprints', f'{module_name}.py')
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 注册blueprint
        bp = getattr(module, 'bp', None)
        if bp:
            app.register_blueprint(bp, url_prefix=f'/api/{module_name}')
            print(f"[OK] 加载模块: {module_name}")
            return True
        else:
            print(f"[WARN] 模块 {module_name} 没有bp对象")
            return False
    except Exception as e:
        print(f"[ERROR] 加载模块 {module_name} 失败: {e}")
        return False

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

if __name__ == '__main__':
    # 加载所有模块
    print("正在加载功能模块...")
    for module_name in MODULES:
        load_module(module_name)
    
    print(f"启动服务器: 0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
