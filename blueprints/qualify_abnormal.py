# -*- coding: utf-8 -*-
"""资质异常监控 - 简化版"""

from flask import Blueprint, jsonify

bp = Blueprint('qualify_abnormal', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'qualify_abnormal', 'status': 'active'})

@bp.route('/status')
def status():
    return jsonify({'success': True, 'message': '资质异常监控（简化版）', 'running': False})

@bp.route('/report')
def report():
    return jsonify({'success': True, 'message': '报告生成（简化版）', 'data': {'abnormal_count': 0}})
