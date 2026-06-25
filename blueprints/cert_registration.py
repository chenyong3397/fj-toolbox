# -*- coding: utf-8 -*-
"""注册证查询 - 简化版"""

from flask import Blueprint, jsonify

bp = Blueprint('cert_registration', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'cert_registration', 'status': 'active'})

@bp.route('/query')
def query():
    return jsonify({'success': True, 'message': '注册证查询（简化版）', 'data': []})
