# -*- coding: utf-8 -*-
"""资质异常监控模块"""

from flask import Blueprint, jsonify, request

bp = Blueprint('qualify_abnormal', __name__)

@bp.route('/info')
def info():
    return jsonify({'code': 0, 'data': {'module': 'qualify_abnormal', 'status': 'active'}})

@bp.route('/status')
def status():
    return jsonify({
        'code': 0,
        'data': {
            'running': False,
            'last_run_time': None,
            'last_success_time': None,
            'last_error': None,
            'run_count': 0
        }
    })

@bp.route('/report')
def report():
    return jsonify({
        'code': 0,
        'data': {
            'abnormal_count': 0,
            'total_count': 0,
            'abnormal_list': []
        }
    })

@bp.route('/report-summary')
def report_summary():
    """返回前端期望的格式"""
    return jsonify({
        'code': 0,
        'data': {
            'stats': {
                'total_companies': 0,
                'abnormal_count': 0,
                'abnormal_items': 0,
                'normal_count': 0,
                'error_count': 0,
                'abnormal_pct': '0%'
            },
            'changes': {
                'history': [],
                'changed_companies': []
            },
            'companies': [],
            'report_time': None
        }
    })

@bp.route('/run', methods=['POST'])
def run():
    return jsonify({
        'code': 0,
        'data': {
            'status': 'completed',
            'message': '抓取任务已完成（简化版）'
        }
    })
