# -*- coding: utf-8 -*-
"""技术人员查询模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('tech_staff', __name__)

@bp.route('/info')
def info():
    return jsonify({'code': 0, 'data': {'module': 'tech_staff', 'status': 'active'}})

@bp.route('/search')
def search():
    """搜索企业"""
    keyword = request.args.get('keyword', '').strip() or request.args.get('company', '').strip()
    
    if not keyword:
        return jsonify({'code': 1, 'msg': '请输入企业名称'})
    
    return jsonify({
        'code': 0,
        'data': [],
        'total': 0,
        'msg': '暂无数据（后端简化版）'
    })

@bp.route('/technicians')
def technicians():
    """获取企业技术人员详情"""
    company = request.args.get('company', '')
    
    return jsonify({
        'code': 0,
        'data': {
            'total': 0,
            'technicians': [],
            'stats': {}
        },
        'msg': '暂无数据（后端简化版）'
    })

@bp.route('/export')
def export():
    """导出Excel"""
    return jsonify({'code': 1, 'msg': '导出功能暂未开放'})
