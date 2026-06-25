# -*- coding: utf-8 -*-
"""职称证查询模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('cert_title', __name__)

@bp.route('/info')
def info():
    return jsonify({'code': 0, 'data': {'module': 'cert_title', 'status': 'active'}})

@bp.route('/search', methods=['POST'])
def search():
    """查询职称证"""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    id_card = data.get('idCard', '').strip()
    
    if not name or not id_card:
        return jsonify({'code': 1, 'msg': '请填写姓名和证件号码'})
    
    # 返回前端期望的格式: {code: 0, data: [...], total: N}
    return jsonify({
        'code': 0,
        'data': [],
        'total': 0,
        'msg': '暂无数据（后端简化版）'
    })
