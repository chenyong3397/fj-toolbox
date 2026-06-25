# -*- coding: utf-8 -*-
"""岗位证查询模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('cert_position', __name__)

@bp.route('/info')
def info():
    return jsonify({'code': 0, 'data': {'module': 'cert_position', 'status': 'active'}})

@bp.route('/search', methods=['POST'])
def search():
    """查询岗位证"""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    iden_num = data.get('idenNum', '').strip() or data.get('idCard', '').strip()
    
    if not name or not iden_num:
        return jsonify({'code': 1, 'msg': '请填写姓名和身份证号'})
    
    return jsonify({
        'code': 0,
        'data': [],
        'total': 0,
        'msg': '暂无数据（后端简化版）'
    })

@bp.route('/photo')
def photo():
    """获取人员照片"""
    return jsonify({'code': 1, 'msg': '暂无照片'})
