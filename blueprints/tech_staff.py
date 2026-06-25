# -*- coding: utf-8 -*-
"""技术人员查询 - 简化版"""

from flask import Blueprint, jsonify

bp = Blueprint('tech_staff', __name__)

@bp.route('/info')
def info():
    return jsonify({'module': 'tech_staff', 'status': 'active'})

@bp.route('/technicians')
def technicians():
    return jsonify({'success': True, 'message': '技术人员查询（简化版）', 'data': []})
