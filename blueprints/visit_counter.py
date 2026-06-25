# -*- coding: utf-8 -*-
"""
访问计数器模块
- GET  /api/visit_counter/count     获取当前访问总人数
- POST /api/visit_counter/increment 递增访问计数并返回最新值
"""

import os
import json
import threading
from flask import Blueprint, jsonify, request

bp = Blueprint('visit_counter', __name__)

# 计数器持久化文件
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
COUNTER_FILE = os.path.join(DATA_DIR, 'visit_counter.json')

_lock = threading.Lock()


def _ensure_dir():
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)


def _load_count():
    """从文件加载计数，文件不存在则返回 0"""
    _ensure_dir()
    try:
        if os.path.isfile(COUNTER_FILE):
            with open(COUNTER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return int(data.get('count', 0))
    except Exception:
        pass
    return 0


def _save_count(count):
    """将计数写入文件"""
    _ensure_dir()
    try:
        with open(COUNTER_FILE, 'w', encoding='utf-8') as f:
            json.dump({'count': count, 'updated_at': __import__('datetime').datetime.now().isoformat()}, f)
    except Exception:
        pass


@bp.route('/count', methods=['GET'])
def get_count():
    """获取当前访问总人数（无需Token）"""
    count = _load_count()
    return jsonify({'code': 0, 'count': count})


@bp.route('/increment', methods=['GET', 'POST'])
def increment():
    """递增访问计数（无需Token），返回递增后的值"""
    with _lock:
        count = _load_count() + 1
        _save_count(count)
    return jsonify({'code': 0, 'count': count})

