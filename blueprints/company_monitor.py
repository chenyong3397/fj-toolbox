# -*- coding: utf-8 -*-
"""企业审批监控模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('company_monitor', __name__)

@bp.route('/info')
def info():
    return jsonify({'code': 0, 'data': {'module': 'company_monitor', 'status': 'active'}})

@bp.route('/search')
def search():
    """查询企业资质办理状态"""
    keyword = request.args.get('keyword', '').strip() or request.args.get('company', '').strip()
    
    if not keyword:
        return jsonify({'code': 1, 'msg': '请输入企业名称'})
    
    # 返回前端期望的格式: {code: 0, data: {check_status, all_records, detail_statuses, ...}}
    return jsonify({
        'code': 0,
        'data': {
            'company_name': keyword,
            'check_status': '',
            'all_records': [],
            'detail_statuses': [],
            'message': '暂无数据（后端简化版）'
        },
        'msg': '暂无数据（后端简化版）'
    })

@bp.route('/status')
def status():
    return search()
