# -*- coding: utf-8 -*-
"""
岗位证查询 Blueprint
挂载路径: /api/cert_position

数据来源: 福建省建设人才与科技发展中心
原始页面: http://220.160.52.118:9084/portalWeb/fwZhcx/toFwZhcxPage?code=zscx
查询接口: POST /portalWeb/fwZhcx/findCertificate
所需参数: name(姓名) + idenNum(身份证号)
"""

import requests
import urllib3
from flask import Blueprint, request, jsonify, Response

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

bp = Blueprint('cert_position', __name__, url_prefix='/api/cert_position')

# ============================================================
# 配置
# ============================================================
BASE_URL = "http://220.160.52.118:9084"
SEARCH_URL = f"{BASE_URL}/portalWeb/fwZhcx/findCertificate"
PHOTO_URL = f"{BASE_URL}/portalWeb/fwZhcx/findPhotoByPersonGuid"
SPECIALTY_URL = f"{BASE_URL}/baseData/findMsgByPersonGuidByJczzyPr"


def get_info():
    """模块信息（供 /modules 接口使用）"""
    return {
        'name': '岗位证',
        'desc': '输入姓名和身份证号，查询岗位证书信息',
        'icon': '🪪',
        'page': '/pages/cert_position/cert_position',
        'bg': '#26A69A'
    }


def create_session():
    """创建带浏览器 headers 的会话"""
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/portalWeb/fwZhcx/toFwZhcxPage?code=zscx",
    })
    return s


# ============================================================
# API 端点
# ============================================================

@bp.route('/info', methods=['GET'])
def info():
    """功能说明接口"""
    return jsonify({
        'code': 0,
        'feature': 'cert_position',
        'name': '岗位证',
        'description': '输入姓名和身份证号，查询岗位证书信息',
        'endpoints': {
            'GET /info': '功能说明',
            'POST /search': '查询岗位证（name, idenNum）',
            'POST /specialty': '查询证书专业详情（certificateGuid）',
            'GET /photo': '获取人员照片（personGuid）',
        }
    })


@bp.route('/search', methods=['POST'])
def search():
    """
    查询岗位证书
    参数: name (姓名), idenNum (身份证号)
    """
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    iden_num = (data.get('idenNum') or data.get('idCard') or '').strip()

    if not name or not iden_num:
        return jsonify({'code': -1, 'msg': '请填写姓名和身份证号'})

    session = create_session()
    try:
        resp = session.post(SEARCH_URL, data={'name': name, 'idenNum': iden_num}, timeout=20)
        if resp.status_code != 200:
            return jsonify({'code': -1, 'msg': f'服务器返回异常({resp.status_code})'})

        result = resp.json()
        ext_code = str(result.get('code', ''))

        if ext_code == '200':
            # 未查询到结果
            return jsonify({'code': 0, 'msg': '没有符合条件的证件', 'data': [], 'total': 0})

        if ext_code != '100':
            return jsonify({'code': -1, 'msg': result.get('msg', '查询失败')})

        raw_list = result.get('result', [])
        total = result.get('total', len(raw_list))

        # 标准化每条证书数据
        certs = []
        for item in raw_list:
            cert = {
                'userName': item.get('userName', ''),
                'sex': '女' if str(item.get('sex', '')) == '0' else '男',
                'certificateType': item.get('certificateType', ''),
                'positionName': item.get('positionName', ''),
                'birthday': item.get('birthday', ''),
                'starTime': item.get('starTime', ''),
                'certificateNum': item.get('certificateNum', ''),
                'endTime': item.get('endTime', ''),
                'certificateOrgan': item.get('certificateOrgan', ''),
                'reviewTime': item.get('reviewTime', ''),
                'workUnit': item.get('workUnit', ''),
                'certificateStatus': item.get('certificateStatus', ''),
                'regioncode': item.get('regioncode', ''),
                'personGuid': item.get('personGuid', ''),
                'certificateGuid': item.get('certificateGuid', ''),
                'careerCode': item.get('careerCode', ''),
                'hasSpecialty': str(item.get('careerCode', '')).startswith('17'),
                'skillLevelId': item.get('skillLevelId', ''),
            }
            certs.append(cert)

        return jsonify({
            'code': 0,
            'msg': f'共找到 {total} 条信息',
            'data': certs,
            'total': total
        })

    except requests.exceptions.Timeout:
        return jsonify({'code': -1, 'msg': '查询超时，请稍后重试'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': f'查询失败：{str(e)}'})


@bp.route('/photo', methods=['GET'])
def photo():
    """
    获取人员照片
    参数: personGuid
    返回: 图片二进制流
    """
    person_guid = request.args.get('personGuid', '').strip()
    if not person_guid:
        return jsonify({'code': -1, 'msg': '缺少 personGuid 参数'})

    session = create_session()
    try:
        resp = session.get(PHOTO_URL, params={'personGuid': person_guid}, timeout=15)
        if resp.status_code == 200 and resp.content:
            return Response(resp.content, mimetype='image/jpeg')
        else:
            return jsonify({'code': -1, 'msg': '未找到照片'})
    except Exception:
        return jsonify({'code': -1, 'msg': '照片获取失败'})


@bp.route('/specialty', methods=['POST'])
def specialty():
    """
    查询证书专业详情（仅 careerCode 以 17 开头的检测试验人员证书）
    参数: certificateGuid
    返回: rows 数组 [{dname, xname, certificatetime}]
    原始接口: POST /baseData/findMsgByPersonGuidByJczzyPr
    """
    data = request.get_json(silent=True) or {}
    cert_guid = (data.get('certificateGuid') or '').strip()

    if not cert_guid:
        return jsonify({'code': -1, 'msg': '缺少 certificateGuid 参数'})

    session = create_session()
    try:
        resp = session.post(SPECIALTY_URL, data={'certificateGuid': cert_guid}, timeout=20)
        if resp.status_code != 200:
            return jsonify({'code': -1, 'msg': f'服务器返回异常({resp.status_code})'})

        result = resp.json()
        rows = result.get('rows', [])
        total = result.get('total', len(rows))

        records = []
        for r in rows:
            records.append({
                'majorName': r.get('dname', ''),       # 大专业
                'minorName': r.get('xname', ''),       # 小专业
                'entryTime': r.get('certificatetime', '')  # 入库时间
            })

        return jsonify({'code': 0, 'data': records, 'total': total})

    except requests.exceptions.Timeout:
        return jsonify({'code': -1, 'msg': '查询超时，请稍后重试'})
    except Exception as e:
        return jsonify({'code': -1, 'msg': f'查询失败：{str(e)}'})
