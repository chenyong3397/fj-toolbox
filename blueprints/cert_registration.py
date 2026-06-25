# -*- coding: utf-8 -*-
"""
注册证 Blueprint — 对接四库一平台从业人员查询
数据源: https://jzsc.mohurd.gov.cn
API:  /APi/webApi/dataservice/query/staff/list (搜索)
      /APi/webApi/dataservice/query/staff/staffDetailAndTrack (详情)
挂载路径: /api/cert_registration
"""

import json
import requests
from flask import Blueprint, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

bp = Blueprint('cert_registration', __name__)

# ── 四库一平台配置 ──
JZSC_BASE = 'https://jzsc.mohurd.gov.cn'
JZSC_SEARCH = f'{JZSC_BASE}/APi/webApi/dataservice/query/staff/list'
JZSC_DETAIL = f'{JZSC_BASE}/APi/webApi/dataservice/query/staff/staffDetailAndTrack'

# AES 加解密配置
AES_KEY = b'Dt8j9wGw%6HbxfFn'
AES_IV = b'0123456789ABCDEF'

JZSC_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://jzsc.mohurd.gov.cn/data/person',
    'v': '231012'
}

SESSION = requests.Session()
SESSION.headers.update(JZSC_HEADERS)


def jzsc_decrypt(hex_str):
    """解密四库一平台 AES 加密响应"""
    if not hex_str:
        return None
    try:
        binary = bytes.fromhex(hex_str.strip())
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        plaintext = unpad(cipher.decrypt(binary), 16)
        return json.loads(plaintext)
    except Exception:
        return None


def jzsc_get(url, params):
    """调用四库一平台 GET 接口并解密"""
    try:
        resp = SESSION.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return {'code': -1, 'msg': f'上游服务返回 {resp.status_code}'}
        data = jzsc_decrypt(resp.text)
        if data is None:
            return {'code': -1, 'msg': '数据解密失败'}
        return data
    except requests.RequestException as e:
        return {'code': -1, 'msg': f'网络请求失败: {str(e)}'}


def get_info():
    """模块信息（供 /modules 接口使用）"""
    return {
        'name': '注册证',
        'desc': '查询建设行业注册人员证书信息（四库一平台）',
        'icon': '📘',
        'page': '/pages/cert_registration/cert_registration',
        'bg': '#5C6BC0'
    }


@bp.route('/info', methods=['GET'])
def info():
    return jsonify({
        'code': 0,
        'feature': 'cert_registration',
        'name': '注册证',
        'description': '从业人员注册证书查询（对接四库一平台）',
        'endpoints': {
            'POST /search': '搜索注册人员（name 姓名, idCard 身份证号, page 页码, pageSize 每页条数）',
            'POST /detail': '获取注册人员详情（ryId 人员ID）',
        }
    })


@bp.route('/search', methods=['POST'])
def search():
    """搜索注册人员"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name', '') or '').strip()
    id_card = (data.get('idCard', '') or '').strip()
    page = data.get('page', 0)
    page_size = data.get('pageSize', 15)

    if not name and not id_card:
        return jsonify({'code': -1, 'msg': '请输入姓名或身份证号'})

    # complexname 支持姓名或身份证号模糊搜索
    complexname = name if name else id_card

    params = {
        'complexname': complexname,
        'pg': page,
        'pgsz': page_size,
        'total': 0
    }

    result = jzsc_get(JZSC_SEARCH, params)

    if result.get('code') != 200:
        return jsonify({'code': -1, 'msg': result.get('message', '查询失败')})

    data_block = result.get('data', {})
    raw_list = data_block.get('list', [])

    items = []
    for item in raw_list:
        items.append({
            'ryId': item.get('RY_ID', ''),
            'name': item.get('RY_NAME', ''),
            'idCard': item.get('RY_CARDNO', ''),
            'regType': item.get('REG_TYPE', ''),
            'regTypeName': item.get('REG_TYPE_NAME', ''),
            'regSealCode': item.get('REG_SEAL_CODE', ''),
            'regQymc': item.get('REG_QYMC', ''),
            'regQyId': item.get('REG_QYID', ''),
            'regSdate': item.get('REG_SDATE'),
        })

    return jsonify({
        'code': 0,
        'data': {
            'list': items,
            'total': data_block.get('total', 0),
            'page': data_block.get('pageNum', page),
            'pageSize': data_block.get('pageSize', page_size)
        }
    })


@bp.route('/detail', methods=['POST'])
def detail():
    """获取注册人员详情"""
    data = request.get_json(silent=True) or {}
    ry_id = (data.get('ryId', '') or '').strip()

    if not ry_id:
        return jsonify({'code': -1, 'msg': '缺少人员ID'})

    result = jzsc_get(JZSC_DETAIL, {'staffId': ry_id})

    if result.get('code') != 200:
        return jsonify({'code': -1, 'msg': result.get('message', '详情查询失败')})

    data_block = result.get('data', {})

    # 人员基本信息
    staff = data_block.get('staffMap', {})
    if not staff:
        return jsonify({'code': -1, 'msg': '未找到该人员信息'})

    basic_info = {
        'ryId': staff.get('RY_ID', ''),
        'name': staff.get('RY_NAME', ''),
        'gender': staff.get('RY_SEX_NAME', ''),
        'idCard': staff.get('RY_CARDNO', ''),
        'cardType': staff.get('RY_CARDTYPE_NAME', ''),
        'status': staff.get('RY_STATUS_NAME', ''),
    }

    # 注册证书列表
    cert_list = []
    for cert in data_block.get('regCertList', []):
        cert_info = {
            'regId': cert.get('REG_ID', ''),
            'regCertNo': cert.get('REG_CERTNO', ''),
            'regTypeName': cert.get('REG_TYPE_NAME', ''),
            'regProfName': cert.get('REG_PROF_NAME', ''),
            'regSealCode': cert.get('REG_SEAL_CODE', ''),
            'regQymc': cert.get('QY_NAME', ''),
            'regQyId': cert.get('REG_QYID', ''),
            'regSdate': cert.get('REG_SDATE'),
            'regEdate': cert.get('REG_EDATE'),
            'regStatus': cert.get('REG_STATUS_NAME', ''),
            'changeNum': cert.get('CHANGE_NUM', '0'),
            # 注册轨迹
            'trackList': [{
                'trackTime': t.get('TRACK_TIME'),
                'regMode': t.get('REG_MODE_NAME', ''),
                'regProfName': t.get('REG_PROF_NAME', ''),
                'compName': t.get('COMP_NAME', ''),
            } for t in cert.get('regTrackList', [])]
        }
        cert_list.append(cert_info)

    return jsonify({
        'code': 0,
        'data': {
            'basicInfo': basic_info,
            'certList': cert_list
        }
    })
