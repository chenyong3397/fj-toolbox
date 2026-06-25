# -*- coding: utf-8 -*-
"""
企业资质办理状态监控 Blueprint
挂载路径: /api/company_monitor

功能：搜索企业关键词，查询资质办理的当前状态，
      监控状态变化（审批中/通过/不予许可/撤回/终止）
"""
import os
import json
import threading
from datetime import datetime

import requests
import urllib3
from flask import Blueprint, request, jsonify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

bp = Blueprint('company_monitor', __name__, url_prefix='/api/company_monitor')


def get_info():
    """模块信息（供 /modules 接口使用）"""
    return {
        'name': '审批状态',
        'desc': '搜索企业，查看资质办理当前状态与变更记录',
        'icon': '📡',
        'page': '/pages/monitor/monitor',
        'url_prefix': '/api/company_monitor',
        'bg': '#1A7F37'
    }


# ============================================================
# 配置
# ============================================================
API_URL = "https://220.160.52.164:8813/credit/publicity-home/publicity"
DEFAULT_KEYWORD = "环宇工程"

STATUS_MAP = {
    "APPROVING": "审批中",
    "PASS": "通过/办结",
    "REJECT": "不予许可",
    "WITHDRAW": "撤回",
    "STOP": "终止",
    "NO_PASS": "不予许可",
}

# status 数组 type → 中文
STATUS_TYPE_MAP = {
    "1": "办理中",
    "2": "补正",
    "3": "予以许可",
    "4": "不予许可",
    "5": "撤回",
}

# ============================================================
# 全局状态（监控历史存储在内存 + 文件）
# ============================================================
MONITOR_HISTORY_FILE = None
history_lock = threading.Lock()


def _get_history_file():
    """获取监控历史文件路径"""
    global MONITOR_HISTORY_FILE
    if MONITOR_HISTORY_FILE is None:
        bp_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.normpath(os.path.join(bp_dir, '..', 'output'))
        os.makedirs(output_dir, exist_ok=True)
        MONITOR_HISTORY_FILE = os.path.join(output_dir, 'company_monitor_history.json')
    return MONITOR_HISTORY_FILE


def load_history():
    """加载监控历史"""
    hf = _get_history_file()
    if os.path.exists(hf):
        try:
            with open(hf, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []  # [{"time": "...", "keyword": "...", "company": "...", "status": "...", "node": "...", "code": "..."}]


def save_history(records):
    """覆盖写入监控历史"""
    with history_lock:
        hf = _get_history_file()
        with open(hf, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)


# ============================================================
# 核心：查询企业状态
# ============================================================
def query_company_status(keyword):
    """
    查询企业办理状态
    返回: {"company": "...", "code": "...", "receive_time": "...",
            "node_type": "...", "check_status": "...", "status_cn": "...",
            "detail_status": "...", "status_type": "...", "status_type_cn": "...",
            "transact_type": "...", "app_types": [...], "qualify_names": [...],
            "audit_officer": "...", "dou_num": "...", "statement": bool,
            "all_records": [...], "total": int}
    """
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://220.160.52.164:8813/gaia/creditFiles.html",
        "Accept": "application/json, text/plain, */*",
    })
    r = s.post(API_URL, data={
        "pageNum": 1, "pageSize": 100, "companyName": keyword
    }, timeout=20)

    data = r.json()
    raw_list = data.get("data", {}).get("list", []) if isinstance(data.get("data"), dict) else []

    # 筛选：精确匹配 keyword 在 companyName 中
    target_items = [item for item in raw_list if keyword in item.get("companyName", "")]
    if not target_items:
        target_items = raw_list

    if not target_items:
        return None

    # 按受理时间倒序
    target_items.sort(key=lambda x: x.get("receiveTime", ""), reverse=True)
    latest = target_items[0]
    latest_code = latest.get("code", "")

    # 收集当前申请（最新 code）的所有并行记录
    current_items = [item for item in target_items if item.get("code") == latest_code]
    # 按审核机关去重（同一 code + 同一 auditOfficer 只保留一条）
    seen_officers = set()
    unique_current = []
    for item in current_items:
        officer = item.get("auditOfficerName", "") or "__no_officer__"
        if officer not in seen_officers:
            seen_officers.add(officer)
            unique_current.append(item)
    current_items = unique_current

    company = latest.get("companyName", "")
    code = latest_code
    receive_time = latest.get("receiveTime", "")
    node_type = latest.get("nodeType", "")
    check_status = latest.get("checkStatus", "")
    status_cn = STATUS_MAP.get(check_status, check_status)

    # ===== 页面实际展示的详细字段（多条并行状态） =====
    detail_statuses = []
    for item in current_items:
        s_list = item.get("status", [])
        s_first = s_list[0] if s_list else {}
        detail_statuses.append({
            "detail_status": s_first.get("name", ""),
            "status_type": s_first.get("type", ""),
            "status_type_cn": STATUS_TYPE_MAP.get(s_first.get("type", ""), ""),
            "audit_officer": item.get("auditOfficerName", ""),
            "node_type": item.get("nodeType", ""),
            "dou_num": s_first.get("douNum", ""),
            "app_types": item.get("appTypeName", []),
            "qualify_names": item.get("qualifyName", []),
            "transact_type": item.get("transactTypeName", ""),
            "statement": item.get("statement", False),
        })

    # 向后兼容的单字段
    first_detail = detail_statuses[0] if detail_statuses else {}
    detail_status = first_detail.get("detail_status", "")
    status_type = first_detail.get("status_type", "")
    status_type_cn = first_detail.get("status_type_cn", "")
    dou_num = first_detail.get("dou_num", "")

    transact_type = latest.get("transactTypeName", "")
    app_types = latest.get("appTypeName", [])
    qualify_names = latest.get("qualifyName", [])
    audit_officer = latest.get("auditOfficerName", "")
    statement = latest.get("statement", False)

    # 所有记录（用于历史展示，也包含页面字段）
    all_records = []
    for item in target_items[:50]:
        s_raw = item.get("checkStatus", "")
        s_list = item.get("status", [])
        s_first = s_list[0] if s_list else {}
        all_records.append({
            "company": item.get("companyName", ""),
            "code": item.get("code", ""),
            "receive_time": item.get("receiveTime", ""),
            "node_type": item.get("nodeType", ""),
            "check_status": s_raw,
            "status_cn": STATUS_MAP.get(s_raw, s_raw),
            "detail_status": s_first.get("name", ""),
            "status_type_cn": STATUS_TYPE_MAP.get(s_first.get("type", ""), ""),
            "dou_num": s_first.get("douNum", ""),
            "transact_type": item.get("transactTypeName", ""),
            "app_types": item.get("appTypeName", []),
            "qualify_names": item.get("qualifyName", []),
            "audit_officer": item.get("auditOfficerName", ""),
            "statement": item.get("statement", False),
        })

    return {
        "company": company,
        "code": code,
        "receive_time": receive_time,
        "node_type": node_type,
        "check_status": check_status,
        "status_cn": status_cn,
        # 多条并行状态（同一 code 对应多个审核机关）
        "detail_statuses": detail_statuses,
        # 向后兼容的单字段
        "detail_status": detail_status,
        "status_type": status_type,
        "status_type_cn": status_type_cn,
        "dou_num": dou_num,
        "transact_type": transact_type,
        "app_types": app_types,
        "qualify_names": qualify_names,
        "audit_officer": audit_officer,
        "statement": statement,
        "all_records": all_records,
        "total": len(target_items),
    }


# ============================================================
# API 端点
# ============================================================

@bp.route('/search', methods=['GET'])
def search():
    """搜索企业并查看当前状态（无需token）"""
    keyword = request.args.get('keyword', DEFAULT_KEYWORD).strip()
    if not keyword:
        return jsonify({'code': -1, 'msg': '请输入搜索关键词'})

    try:
        result = query_company_status(keyword)
    except Exception as e:
        return jsonify({'code': -1, 'msg': f'查询失败：{str(e)}', 'data': None})

    if result is None:
        return jsonify({'code': 0, 'msg': f'未找到包含"{keyword}"的企业记录', 'data': None})

    # 记录到监控历史
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    history = load_history()

    # 检查是否需要添加新记录（状态变化 或 首次搜索 或 超过1小时）
    state_key = f"{result['code']}|{result['check_status']}|{result['node_type']}"
    should_record = True
    if history:
        last_entry = history[0]
        last_key = f"{last_entry.get('code','')}|{last_entry.get('check_status','')}|{last_entry.get('node_type','')}"
        last_time_str = last_entry.get('time', '')
        try:
            last_time = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')
            if state_key == last_key and (datetime.now() - last_time).seconds < 3600:
                should_record = False
        except Exception:
            pass

    if should_record:
        new_entry = {
            "time": now,
            "keyword": keyword,
            "company": result["company"],
            "code": result["code"],
            "receive_time": result["receive_time"],
            "node_type": result["node_type"],
            "check_status": result["check_status"],
            "status_cn": result["status_cn"],
        }

        # 标记是否为状态变化
        if history:
            last_entry = history[0]
            last_key = f"{last_entry.get('code','')}|{last_entry.get('check_status','')}|{last_entry.get('node_type','')}"
            if state_key != last_key:
                new_entry["is_changed"] = True
                new_entry["prev_status"] = last_entry.get("status_cn", "")

        history.insert(0, new_entry)
        # 最多保留 200 条
        if len(history) > 200:
            history = history[:200]
        save_history(history)

    return jsonify({'code': 0, 'data': result, 'history': history[:50]})


@bp.route('/history', methods=['GET'])
def get_history():
    """获取监控历史记录（无需token）"""
    keyword = request.args.get('keyword', '').strip()
    history = load_history()

    if keyword:
        history = [h for h in history if keyword in h.get('keyword', '') or keyword in h.get('company', '')]

    return jsonify({'code': 0, 'data': history[:50]})


@bp.route('/status', methods=['GET'])
def quick_status():
    """快速查询状态（使用默认关键词"环宇工程"）"""
    try:
        result = query_company_status(DEFAULT_KEYWORD)
    except Exception as e:
        return jsonify({'code': -1, 'msg': f'查询失败：{str(e)}'})

    if result is None:
        return jsonify({'code': 0, 'msg': '暂无数据', 'data': None})

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({'code': 0, 'data': result, 'query_time': now})
