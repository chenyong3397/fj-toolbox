# -*- coding: utf-8 -*-
"""技术人员查询模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('tech_staff', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'tech_staff', 'status': 'active'})

@bp.route('/search')
def search():
    """搜索企业"""
    keyword = request.args.get('keyword', '') or request.args.get('company', '')
    
    if not keyword:
        return jsonify({
            'success': False,
            'message': '请输入企业名称'
        }), 400
    
    return jsonify({
        'success': True,
        'message': '查询成功',
        'data': {
            'keyword': keyword,
            'result': '暂无数据（后端简化版）'
        }
    })

@bp.route('/technicians')
def technicians():
    """获取企业技术人员详情"""
    company = request.args.get('company', '')
    
    return jsonify({
        'success': True,
        'message': '查询成功',
        'data': {
            'company': company,
            'technicians': []
        }
    })

@bp.route('/export')
def export():
    """导出Excel"""
    return jsonify({
        'success': False,
        'message': '导出功能暂未开放'
    })
