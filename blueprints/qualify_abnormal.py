# -*- coding: utf-8 -*-
"""资质异常监控模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('qualify_abnormal', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'qualify_abnormal', 'status': 'active'})

@bp.route('/status')
def status():
    """查询任务状态"""
    return jsonify({
        'success': True,
        'running': False,
        'last_run_time': None,
        'last_success_time': None,
        'last_error': None,
        'run_count': 0
    })

@bp.route('/report')
def report():
    """获取报告数据"""
    return jsonify({
        'success': True,
        'data': {
            'abnormal_count': 0,
            'total_count': 0,
            'abnormal_list': [],
            'message': '暂无报告数据'
        }
    })

@bp.route('/report-summary')
def report_summary():
    """获取报告摘要"""
    return jsonify({
        'success': True,
        'data': {
            'abnormal_count': 0,
            'total_count': 0,
            'summary': '暂无报告数据',
            'last_update': None
        }
    })

@bp.route('/run', methods=['POST'])
def run():
    """触发抓取任务"""
    return jsonify({
        'success': True,
        'message': '抓取任务已启动（简化版）',
        'status': 'completed'
    })
