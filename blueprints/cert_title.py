# -*- coding: utf-8 -*-
"""职称证查询模块 - 简化版"""

from flask import Blueprint, jsonify, request

bp = Blueprint('cert_title', __name__, url_prefix='/api/cert_title')

@bp.route('/info')
def info():
    """模块信息"""
    return jsonify({
        'module': 'cert_title',
        'status': 'active',
        'version': '1.0'
    })

@bp.route('/query')
def query():
    """查询接口（简化版）"""
    name = request.args.get('name', '')
    id_card = request.args.get('idCard', '')
    
    return jsonify({
        'success': True,
        'message': '查询成功（简化版）',
        'data': {
            'name': name,
            'idCard': id_card[-4:] if id_card else '',
            'result': '测试数据'
        }
    })
