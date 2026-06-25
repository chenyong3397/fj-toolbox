# -*- coding: utf-8 -*-
"""
新功能模板 Blueprint
使用方法：
  1. 复制此文件，重命名为你的功能名（如 weatcher_alert.py）
  2. 修改 bp = Blueprint(...) 中的名称
  3. 在 app.py 中此文件会被自动发现并注册
  4. 挂载路径自动为 /api/你的文件名

示例：文件名为 weatcher_alert.py → 挂载到 /api/weatcher_alert
"""

from flask import Blueprint, request, jsonify

# Blueprint 名称：建议与文件名一致
# url_prefix：由 app.py 自动设置为 /api/文件名（无 .py 后缀）
bp = Blueprint('feature_template', __name__)


def get_info():
    """模块信息（供 /modules 接口使用）"""
    return {
        'name': '功能模板',
        'desc': '新功能开发模板',
        'icon': '📋',
        'page': '/pages/feature_tpl/feature_tpl',
        'url_prefix': '/api/feature_template',
        'bg': '#607D8B'
    }

# ========== 在此添加你的路由 ==========

@bp.route('/info', methods=['GET'])
def info():
    """功能说明接口（每个功能建议保留此接口）"""
    return jsonify({
        'code': 0,
        'feature': 'feature_template',
        'description': '新功能模板，修改此文件以添加你的功能',
        'endpoints': {
            'GET /info': '功能说明',
            'POST /run': '执行功能（示例）',
            'GET /status': '查询状态（示例）',
        }
    })


@bp.route('/run', methods=['POST', 'GET'])
def run():
    """执行功能（示例）"""
    # TODO: 替换为你的实际逻辑
    return jsonify({
        'code': 0,
        'msg': '功能运行中（示例）',
        'hint': '请修改 blueprints/feature_template.py 中的 run() 函数'
    })


@bp.route('/status', methods=['GET'])
def status():
    """查询状态（示例）"""
    return jsonify({
        'code': 0,
        'running': False,
        'hint': '请修改 blueprints/feature_template.py 添加实际状态逻辑'
    })


# ========== 添加更多路由... ==========
# 参考以上格式，每个路由对应一个功能接口
