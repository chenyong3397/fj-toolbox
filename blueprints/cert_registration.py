# -*- coding: utf-8 -*-
"""注册证查询模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('cert_registration', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'cert_registration', 'status': 'active'})

@bp.route('/search', methods=['POST'])
def search():
    """查询注册证"""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '')
    id_card = data.get('idCard', '')
    page = data.get('page', 1)
    
    if not name and not id_card:
        return jsonify({
            'success': False,
            'message': '请输入姓名或身份证号'
        }), 400
    
    return jsonify({
        'success': True,
        'message': '查询成功',
        'data': {
            'name': name,
            'idCard': id_card,
            'page': page,
            'result': '暂无数据（后端简化版）'
        }
    })
