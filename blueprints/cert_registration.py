# -*- coding: utf-8 -*-
"""注册证查询模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('cert_registration', __name__)

@bp.route('/info')
def info():
    return jsonify({'code': 0, 'data': {'module': 'cert_registration', 'status': 'active'}})

@bp.route('/search', methods=['POST'])
def search():
    """查询注册证"""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    id_card = data.get('idCard', '').strip()
    page = data.get('page', 0)
    page_size = data.get('pageSize', 15)
    
    if not name and not id_card:
        return jsonify({'code': 1, 'msg': '请输入姓名或身份证号'})
    
    # 返回前端期望的格式: {code: 0, data: {list: [...], total: N, page: N}}
    return jsonify({
        'code': 0,
        'data': {
            'list': [],
            'total': 0,
            'page': page,
            'pageSize': page_size
        },
        'msg': '暂无数据（后端简化版）'
    })
