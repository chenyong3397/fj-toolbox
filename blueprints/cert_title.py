# -*- coding: utf-8 -*-
"""
职称证 Blueprint — 对接全国人力资源和社会保障政务服务平台
数据源: https://www.12333.gov.cn
服务: 全国职称评审信息查询（试运行）
页面: /portal/service_catalog/cert/zcpszscx?pfaId=202111221400000010
挂载路径: /api/cert_title

修复历史：
  v2 (2026-06-25): 修正查询参数（补 age303/age306/accountType/age304/agb017），
                   验证码字段名改为 captcha，集成 ddddocr 自动 OCR + 最多3次重试
"""

import json
import time
import base64
import io
import re
import ssl
import numpy as np
from PIL import Image
from flask import Blueprint, request, jsonify
import requests
from requests.adapters import HTTPAdapter
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad

bp = Blueprint('cert_title', __name__, url_prefix='/api/cert_title')

# ============================================================
# 配置
# ============================================================
BASE = 'https://www.12333.gov.cn'
PORTAL = f'{BASE}/portal'
QUERY_URL = f'{BASE}/service_catalog/cert/zcpszscx'         # AJAX POST 地址（无 /portal）
QUERY_PAGE_URL = f'{PORTAL}/service_catalog/cert/zcpszscx'  # 查询页面 GET 地址（有 /portal）
PFA_ID = '202111221400000010'
CAPTCHA_URL = f'{BASE}/randomCaptcha.sjson'

# 法人登录账号
UNIT_USERNAME = 'liuxinglong94vip'
UNIT_PASSWORD = 'Liu94vip'

# 登录页 RSA 公钥（1024-bit，用于 CAS 法人登录密码加密）
LOGIN_PUBKEY_PEM = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDAN9usVMGLuk/jrz8nZt48dhwn
8+4OPb2CwGVPZQoWtGetrSIKyC8SNZErmgCQdGdDfgnfmtLj9vEzVbtABfhM/nl3
tCbYfz7dLDXd0XBCVP6bXKfyaroc6znfXum2j8rOu8qAKcGKviM41qi85G5/Xvgu
8ZtdC1B5tokZjqDlNQIDAQAB
-----END PUBLIC KEY-----"""

# 查询页 RSA 公钥缓存（4096-bit，用于加密查询表单中的姓名/证件号）
_QUERY_PUBKEY_PEM = None
_QUERY_PUBKEY_EXPIRY = 0

# 法人账户信息缓存（登录后从查询页提取）
_UNIT_USC_CODE = ''   # 统一社会信用代码（age304）
_UNIT_NAME = ''       # 单位名称（agb017）
_ACCOUNT_TYPE = 'UNIT'

# ddddocr 实例（延迟初始化）
_ocr = None


def get_ocr():
    """延迟初始化 ddddocr"""
    global _ocr
    if _ocr is None:
        try:
            import ddddocr
            _ocr = ddddocr.DdddOcr(show_ad=False)
            print("[cert_title] ddddocr loaded")
        except Exception as e:
            print(f"[cert_title] ddddocr init failed: {e}")
    return _ocr


class LegacySSLAdapter(HTTPAdapter):
    """兼容旧版 SSL (UNSAFE_LEGACY_RENEGOTIATION)"""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


# 全局 session 实例（模块级，重用 cookies 保持登录态）
_login_session = None
_login_expiry = 0


def get_info():
    """模块信息（供 /modules 接口使用）"""
    return {
        'name': '职称证',
        'desc': '查询全国职称评审信息',
        'icon': '🎓',
        'page': '/pages/cert_title/cert_title',
        'bg': '#AB47BC'
    }


# ============================================================
# 工具函数
# ============================================================

def rsa_encrypt(plaintext, pubkey=None):
    """RSA PKCS1_v1_5 加密"""
    if pubkey is None:
        pubkey = LOGIN_PUBKEY_PEM
    key = RSA.import_key(pubkey)
    cipher = PKCS1_v1_5.new(key)
    encrypted = cipher.encrypt(plaintext.encode('utf-8'))
    return base64.b64encode(encrypted).decode('utf-8')


def get_query_pubkey(session):
    """获取查询页面的 RSA 公钥（4096-bit），同时提取法人账户信息"""
    global _QUERY_PUBKEY_PEM, _QUERY_PUBKEY_EXPIRY
    global _UNIT_USC_CODE, _UNIT_NAME, _ACCOUNT_TYPE
    now = time.time()

    if _QUERY_PUBKEY_PEM and now < _QUERY_PUBKEY_EXPIRY:
        return _QUERY_PUBKEY_PEM

    try:
        resp = session.get(
            f'{QUERY_PAGE_URL}?pfaId={PFA_ID}',
            headers={'Referer': f'{PORTAL}/service_catalog'},
            timeout=15
        )
        html = resp.content.decode('utf-8', errors='replace')

        # 提取 RSA 公钥
        pk_match = re.search(r"encrypt\.setPublicKey\('([^']+)'\)", html)
        if pk_match:
            b64key = pk_match.group(1)
            pem = '-----BEGIN PUBLIC KEY-----\n'
            for j in range(0, len(b64key), 64):
                pem += b64key[j:j+64] + '\n'
            pem += '-----END PUBLIC KEY-----'
            _QUERY_PUBKEY_PEM = pem
            _QUERY_PUBKEY_EXPIRY = now + 3600
            print(f"[cert_title] query pubkey loaded ({RSA.import_key(pem).size_in_bits()} bits)")

        # 提取法人账户信息（uscCode / unitName / accountType）
        usc_m = re.search(r"uscCode\s*=\s*[\"'](.*?)[\"']", html)
        unit_m = re.search(r"unitName\s*=\s*[\"'](.*?)[\"']", html)
        acc_m  = re.search(r"accountType\s*=\s*[\"'](.*?)[\"']", html)
        if usc_m:
            _UNIT_USC_CODE = usc_m.group(1)
        if unit_m:
            _UNIT_NAME = unit_m.group(1)
        if acc_m:
            _ACCOUNT_TYPE = acc_m.group(1)
        print(f"[cert_title] unit: uscCode={_UNIT_USC_CODE[:20]}, "
              f"unitName={_UNIT_NAME[:20]}, accountType={_ACCOUNT_TYPE}")

        return _QUERY_PUBKEY_PEM

    except Exception as e:
        print(f"[cert_title] query pubkey fetch error: {e}")

    return None


def aes_encrypt_ecb(plaintext, key_str):
    """AES-128-ECB PKCS7 加密"""
    key = key_str.encode('utf-8')[:16]
    cipher = AES.new(key, AES.MODE_ECB)
    padded = pad(plaintext.encode('utf-8'), 16)
    return base64.b64encode(cipher.encrypt(padded)).decode('utf-8')


def solve_slider_captcha(bg_b64, fg_b64):
    """登录滑块验证码破解（模板匹配）"""
    def decode(s):
        return base64.b64decode(s.split(',', 1)[1] if ',' in s else s)
    try:
        bg = np.array(Image.open(io.BytesIO(decode(bg_b64))).convert('L'), dtype=np.float32)
        fg = np.array(Image.open(io.BytesIO(decode(fg_b64))).convert('L'), dtype=np.float32)
        fw = fg.shape[1]
        sw = bg.shape[1] - fw
        if sw <= 0:
            return 0, 0
        best_x, best_s = 0, -1
        for x in range(0, sw, 3):
            s = np.corrcoef(bg[:, x:x+fw].flatten(), fg.flatten())[0, 1]
            if s > best_s:
                best_s, best_x = s, x
        for x in range(max(0, best_x-4), min(sw, best_x+5)):
            s = np.corrcoef(bg[:, x:x+fw].flatten(), fg.flatten())[0, 1]
            if s > best_s:
                best_s, best_x = s, x
        return best_x, best_s
    except Exception as e:
        print(f"[cert_title] slider captcha error: {e}")
        return 0, 0


def fetch_and_ocr_captcha(session):
    """
    获取图形验证码并用 ddddocr 自动识别
    返回 (captcha_code, captcha_bytes) 或 (None, None)
    """
    try:
        ts = int(time.time() * 1000)
        cap_resp = session.get(
            f'{CAPTCHA_URL}?{ts}',
            timeout=15,
            headers={'Referer': f'{QUERY_PAGE_URL}?pfaId={PFA_ID}'}
        )
        if cap_resp.status_code != 200 or not cap_resp.content:
            return None, None

        img_bytes = cap_resp.content
        ocr = get_ocr()
        if ocr is None:
            return None, img_bytes

        code = ocr.classification(img_bytes)
        # 清理识别结果：只保留字母数字，转小写
        code = re.sub(r'[^a-zA-Z0-9]', '', code).lower()
        print(f"[cert_title] ocr captcha: {code}")
        return code, img_bytes

    except Exception as e:
        print(f"[cert_title] captcha fetch/ocr error: {e}")
        return None, None


def create_12333_session():
    """创建带 SSL 适配的 12333 session"""
    s = requests.Session()
    s.mount('https://', LegacySSLAdapter())
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })
    return s


# ============================================================
# 登录管理
# ============================================================

def login_12333():
    """执行法人登录，返回已认证的 session（带缓存）"""
    global _login_session, _login_expiry

    now = time.time()
    if _login_session is not None and now < _login_expiry:
        return _login_session

    s = create_12333_session()

    try:
        page = s.get(f'{BASE}/cas/unitLogin', timeout=15)
        exec_match = re.search(r'name="execution"\s+value="([^"]+)"', page.text)
        execution = exec_match.group(1) if exec_match else 'e1s1'

        cap = s.post(
            f'{BASE}/usercenter/captcha/get',
            json={
                'captchaType': 'blockPuzzle',
                'clientUid': 'cert-title-py',
                'ts': int(now * 1000),
            },
            timeout=15
        )
        rep = cap.json().get('repData', {})
        token = rep.get('token', '')
        sk = rep.get('secretKey', '')
        bg = rep.get('originalImageBase64', '')
        fg = rep.get('jigsawImageBase64', '')

        if not token:
            print("[cert_title] slider captcha fetch failed")
            return None

        x_offset, _ = solve_slider_captcha(bg, fg)
        point_json = json.dumps({'x': float(x_offset), 'y': 5.0})
        cv = aes_encrypt_ecb(f'{token}---{point_json}', sk)
        ep = rsa_encrypt(UNIT_PASSWORD, LOGIN_PUBKEY_PEM)

        resp = s.post(
            f'{BASE}/cas/unitLogin',
            data={
                'type': '2',
                'execution': execution,
                '_eventId': 'submit',
                'captchaType': 'blockPuzzle',
                'captchaVerification': cv,
                'username': UNIT_USERNAME,
                'password': ep,
            },
            allow_redirects=False,
            timeout=15
        )

        if resp.status_code not in (302, 301):
            print(f"[cert_title] login failed: {resp.status_code}")
            return None

        final = s.get(
            resp.headers.get('Location', f'{BASE}/portal/index'),
            allow_redirects=True,
            timeout=15
        )
        print(f"[cert_title] login ok -> {final.url[:80]}")

        _login_session = s
        _login_expiry = now + 600  # 10 分钟
        return s

    except Exception as e:
        print(f"[cert_title] login error: {e}")
        return None


def _force_relogin():
    """强制下次请求重新登录（清理所有缓存）"""
    global _login_session, _login_expiry
    global _QUERY_PUBKEY_PEM, _QUERY_PUBKEY_EXPIRY
    global _UNIT_USC_CODE, _UNIT_NAME, _ACCOUNT_TYPE
    _login_session = None
    _login_expiry = 0
    _QUERY_PUBKEY_PEM = None
    _QUERY_PUBKEY_EXPIRY = 0
    _UNIT_USC_CODE = ''
    _UNIT_NAME = ''
    _ACCOUNT_TYPE = 'UNIT'
    print("[cert_title] force relogin: all caches cleared")


def _is_session_expired(msg):
    """检测 12333 返回的会话过期提示"""
    if not msg:
        return False
    keywords = ['未操作', '刷新', '长时间', '登录', '过期', '超时']
    return any(kw in msg for kw in keywords)


def get_session():
    """获取已登录的 session"""
    return login_12333()
    """获取已登录的 session"""
    return login_12333()


def _do_query(s, query_pubkey, name, cert_type, id_card, cert_no, captcha_code):
    """
    执行一次查询请求，返回 (raw_bytes, status_code)
    参数说明（与官网 JS 对齐）：
      age303 = "2"              — 查询类型（法人用户）
      age306 = "XTPTRSZWFW001" — 固定服务编码
      age304 = uscCode          — 法人统一社会信用代码
      agb017 = unitName         — 法人单位名称
      captcha                   — 图形验证码
      accountType = "UNIT"      — 账户类型
    """
    enc_name = rsa_encrypt(name, query_pubkey)
    enc_id   = rsa_encrypt(id_card, query_pubkey)

    params = {
        'pfaId':       PFA_ID,
        'aac058':      cert_type,
        'aac147':      enc_id,
        'aac003':      enc_name,
        'age116':      cert_no,
        'age306':      'XTPTRSZWFW001',
        'age303':      '2',
        'age304':      _UNIT_USC_CODE,
        'agb017':      _UNIT_NAME,
        'captcha':     captcha_code,
        'accountType': _ACCOUNT_TYPE or 'UNIT',
    }

    resp = s.post(
        QUERY_URL,
        data=params,
        timeout=30,
        headers={
            'Referer':         f'{QUERY_PAGE_URL}?pfaId={PFA_ID}',
            'Content-Type':    'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept':          'application/json, text/javascript, */*; q=0.01',
        }
    )
    return resp.content, resp.status_code


# ============================================================
# API 端点
# ============================================================

@bp.route('/info', methods=['GET'])
def info():
    return jsonify({
        'code': 0,
        'feature': 'cert_title',
        'name': '职称证',
        'description': '查询全国职称评审信息（试运行）',
        'endpoints': {
            'GET /info': '功能说明',
            'POST /search': '查询职称证（name, certType, idCard, certNo，验证码自动识别）',
        }
    })


@bp.route('/search', methods=['POST'])
def search():
    """
    查询职称评审信息（验证码由后端自动识别，最多重试3次）
    参数:
        name:     姓名（必填）
        certType: 证件类型，默认 '01'（居民身份证）
        idCard:   证件号码（必填）
        certNo:   证书编号（可选）
    """
    data = request.get_json(silent=True) or {}
    name      = (data.get('name', '')     or '').strip()
    cert_type = (data.get('certType', '') or '01').strip()
    id_card   = (data.get('idCard', '')   or '').strip()
    cert_no   = (data.get('certNo', '')   or data.get('certificateNo', '') or '').strip()

    if not name:
        return jsonify({'code': -1, 'msg': '请填写姓名'})
    if not id_card:
        return jsonify({'code': -1, 'msg': '请填写证件号码'})

    # 外层重试：处理会话过期自动重新登录（最多2轮）
    for retry_round in range(2):
        s = get_session()
        if s is None:
            return jsonify({'code': -1, 'msg': '上游登录失败，请稍后重试'})

        try:
            query_pubkey = get_query_pubkey(s)
            if not query_pubkey:
                return jsonify({'code': -1, 'msg': '无法获取加密公钥，请稍后重试'})

            last_msg = '查询失败'
            # 内层重试：验证码 OCR 最多3次
            for attempt in range(3):
                captcha_code, _ = fetch_and_ocr_captcha(s)
                if not captcha_code:
                    return jsonify({'code': -1, 'msg': '验证码识别服务不可用，请稍后重试'})

                raw_bytes, status = _do_query(s, query_pubkey, name, cert_type, id_card, cert_no, captcha_code)

                if status != 200:
                    last_msg = f'查询服务异常 ({status})'
                    continue

                # --- 解析响应 ---
                try:
                    result = json.loads(raw_bytes.decode('utf-8'))
                except Exception:
                    text = raw_bytes.decode('utf-8', errors='replace')
                    print(f"[cert_title] Non-JSON: {text[:200]}")
                    if '验证码' in text:
                        last_msg = '验证码错误'
                        continue
                    if _is_session_expired(text):
                        print(f"[cert_title] session expired (non-JSON), relogin...")
                        _force_relogin()
                        break  # 跳出内层，触发外层重新登录
                    return jsonify({'code': -1, 'msg': '查询服务繁忙，请稍后重试'})

                code_str = str(result.get('code', ''))
                msg_str  = result.get('message', result.get('msg', ''))

                # 会话过期/超时 → 强制重新登录
                if (code_str != '50' and _is_session_expired(msg_str)) or \
                   (code_str == str(result.get('status', '')) and _is_session_expired(msg_str)):
                    print(f"[cert_title] session expired (JSON code={code_str}): {msg_str}")
                    _force_relogin()
                    break  # 跳出内层，触发外层重新登录

                # 验证码错误 → 换一张重试
                if code_str == '50' or '验证码' in msg_str:
                    print(f"[cert_title] captcha wrong (attempt {attempt+1}): {captcha_code}")
                    last_msg = '验证码识别失败'
                    time.sleep(0.5)
                    continue

                # 查询成功
                if code_str not in ('0', '00'):
                    if code_str in ('10', '11'):
                        return jsonify({'code': -1, 'msg': msg_str or '查询参数有误'})
                    return jsonify({'code': -1, 'msg': msg_str or f'查询失败 (code={code_str})'})

                # --- 解析 data ---
                data_block = result.get('data', {})
                tips = data_block.get('tips', '')
                if tips:
                    return jsonify({'code': -1, 'msg': tips})

                # 12333 将证书列表放在 data.str 中（JSON 字符串），不是 data.list
                raw_str = data_block.get('str', '[]')
                try:
                    raw_list = json.loads(raw_str) if isinstance(raw_str, str) else raw_str
                except Exception:
                    raw_list = data_block.get('list', [])
                zccx_code = data_block.get('zccxCode', {})

                # 代码映射表
                cert_name_codes = zccx_code.get('AAC200', {})
                category_codes  = zccx_code.get('AGE002', {})
                level_codes     = zccx_code.get('AGE013', {})
                specialty_codes = zccx_code.get('AGZ066', {})
                cert_type_codes = zccx_code.get('AAC058', {})

                items = []
                for item in raw_list:
                    approve_raw = item.get('age007', '')
                    if isinstance(approve_raw, int) and approve_raw > 19000101:
                        approve_str = str(approve_raw)
                        approve_date = f'{approve_str[:4]}-{approve_str[4:6]}-{approve_str[6:8]}'
                    else:
                        approve_date = str(approve_raw)

                    items.append({
                        'name':           item.get('aac003', ''),
                        'idCard':         item.get('aac147', ''),
                        'certType':       cert_type_codes.get(item.get('aac058', ''), item.get('aac058', '')),
                        'certName':       cert_name_codes.get(item.get('aac200', ''), item.get('aac200', '')),
                        'category':       category_codes.get(item.get('age002', ''), item.get('age002', '')),
                        'level':          level_codes.get(item.get('age013', ''), item.get('age013', '')),
                        'levelCode':      item.get('age013', ''),
                        'specialty':      specialty_codes.get(item.get('agz066', ''), item.get('agz066', '')),
                        'specialtyDetail': item.get('age877', ''),
                        'certNo':         item.get('age116', ''),
                        'approveDate':    approve_date,
                        'committee':      item.get('age005', ''),
                        'onJobUnit':      item.get('agb017', ''),
                        'regionCode':     item.get('aab301', ''),
                    })

                return jsonify({
                    'code':  0,
                    'msg':   f'共找到 {len(items)} 条职称信息',
                    'data':  items,
                    'total': len(items)
                })

            # 内层循环耗尽（3次验证码均失败 或 触发 re-login break）
            if retry_round == 0 and last_msg == '查询失败':
                # 可能是会话过期触发的 break，外层会自动重试
                continue

        except requests.exceptions.Timeout:
            return jsonify({'code': -1, 'msg': '查询超时，请稍后重试'})
        except Exception as e:
            print(f"[cert_title] search error: {e}")
            return jsonify({'code': -1, 'msg': f'查询失败: {str(e)}'})

    # 外层重试耗尽
    return jsonify({'code': -1, 'msg': '登录会话已过期，请刷新页面重试'})


@bp.route('/cert_types', methods=['GET'])
def cert_types():
    """获取证件类型列表"""
    s = get_session()
    if s is None:
        return jsonify({'code': -1, 'msg': '登录失败'})

    try:
        resp = s.get(f'{QUERY_PAGE_URL}?pfaId={PFA_ID}', allow_redirects=True, timeout=15,
                     headers={'Referer': f'{PORTAL}/service_catalog'})
        if resp.status_code == 200:
            match = re.search(r'certTypes\s*=\s*(\{[^}]+\})', resp.text)
            if match:
                types = json.loads(match.group(1))
                return jsonify({'code': 0, 'data': types})

        return jsonify({'code': 0, 'data': {
            '01': '居民身份证',
            '02': '军官证',
            '03': '护照',
            '04': '港澳居民来往内地通行证',
            '05': '台湾居民来往大陆通行证',
            '06': '外国人永久居留身份证',
        }})

    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e)})
