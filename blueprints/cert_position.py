# -*- coding: utf-8 -*-
"""岗位证查询模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('cert_position', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'cert_position', 'status': 'active'})

@bp.route('/search', methods=['POST'])
def search():
    """查询岗位证"""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '')
    id_card = data.get('idCard', '')
    
    if not name or not id_card:
        return jsonify({
            'success': False,
            'message': '请输入姓名和身份证号'
        }), 400
    
    return jsonify({
        'success': True,
        'message': '查询成功',
        'data': {
            'name': name,
            'idCard': id_card,
            'result': '暂无数据（后端简化版）'
        }
    })

@bp.route('/photo')
def photo():
    """获取人员照片"""
    return jsonify({'success': False, 'message': '暂无照片'})
