# -*- coding: utf-8 -*-
"""岗位证查询 - 简化版"""

from flask import Blueprint, jsonify, request

bp = Blueprint('cert_position', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'cert_position', 'status': 'active'})

@bp.route('/query')
def query():
    return jsonify({'success': True, 'message': '岗位证查询（简化版）', 'data': []})
