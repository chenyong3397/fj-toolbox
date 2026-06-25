# -*- coding: utf-8 -*-
"""企业审批监控 - 简化版"""

from flask import Blueprint, jsonify

bp = Blueprint('company_monitor', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'company_monitor', 'status': 'active'})

@bp.route('/status')
def status():
    return jsonify({'success': True, 'message': '企业审批监控（简化版）', 'data': []})
