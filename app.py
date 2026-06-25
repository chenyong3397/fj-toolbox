#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多功能小程序后端 - 最小化可用版本
确保能成功部署到Render
"""

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({
        'service': '多功能小程序后端API',
        'version': '2.0',
        'status': 'running',
        'message': '服务正常运行'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
