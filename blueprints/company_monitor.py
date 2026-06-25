# -*- coding: utf-8 -*-
"""企业审批监控模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('company_monitor', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'company_monitor', 'status': 'active'})

@bp.route('/search')
def search():
    """查询企业资质办理状态"""
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

@bp.route('/status')
def status():
    """兼容旧接口"""
    return search()
