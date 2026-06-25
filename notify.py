#!/usr/bin/env python3
"""
微信通知模块 - 支持 Server酱 / WxPusher 双渠道推送

配置说明（在 config.ini 中）:
  [notification]
  enabled = true
  on_change_only = false

  [serverchan]
  enabled = true
  sendkey = SCT你的key

  [wxpusher]
  enabled = true
  app_token = AT_你的appToken
  topic_ids = 12345
  uids = UID_xxx

获取方式：
  - Server酱: https://sct.ftqq.com/  扫码登录获取 SendKey
  - WxPusher: https://wxpusher.zjiecode.com/  创建应用获取 appToken
    需要在管理后台创建"主题(topic)"，并将 topicId 填入 topic_ids
    或用 uids 指定接收用户（扫码关注后获取 UID）
"""

import requests
import json
import logging
import configparser
import os

logger = logging.getLogger(__name__)


def generate_report_text(result, change_messages=None, no_change_msg=None):
    """
    根据抓取结果生成微信推送报告（Markdown 格式）

    Args:
        result: 抓取结果字典
        change_messages: 变化检测的消息列表（可选）
        no_change_msg: 无变化时的描述（可选）

    Returns:
        (title, content) 元组
    """
    scrape_time = result.get('scrape_time', '')
    total = result.get('total_companies', 0)
    abnormal_count = result.get('abnormal_count', 0)
    normal_count = result.get('normal_count', 0)
    error_count = result.get('error_count', 0)
    abnormal_companies = result.get('abnormal_companies', [])
    total_items = sum(len(c.get('abnormalItems', [])) for c in abnormal_companies)
    pct = abnormal_count / max(total, 1) * 100

    # 标题
    title = f"质量检测资质异常报告 {scrape_time[:10]}"

    # 正文（Markdown）
    lines = []
    lines.append(f"## 福建省质量检测企业资质异常报告\n")
    lines.append(f"**查询时间：** {scrape_time}\n")
    lines.append(f"**数据来源：** 福建省建设行业信息公开平台\n")
    lines.append(f"**查询范围：** 省内企业 → 质量检测 → 资质异常\n")
    lines.append(f"---\n")

    # 统计概览
    lines.append(f"### 统计概览\n")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 质量检测企业总数 | {total} |")
    lines.append(f"| 资质异常企业数 | **{abnormal_count}** |")
    lines.append(f"| 资质异常项数 | {total_items} |")
    lines.append(f"| 正常企业数 | {normal_count} |")
    lines.append(f"| 查询失败数 | {error_count} |")
    lines.append(f"| 异常占比 | {pct:.1f}% |")
    lines.append(f"\n")

    # 变化检测
    if change_messages:
        lines.append(f"### 变化检测\n")
        for msg in change_messages:
            lines.append(f"{msg}\n")
        lines.append(f"---\n")

    if no_change_msg:
        lines.append(f"### 变化检测\n")
        lines.append(f"{no_change_msg}\n")
        lines.append(f"---\n")

    # 异常企业列表
    if abnormal_companies:
        lines.append(f"### 异常企业列表（{abnormal_count} 家）\n")
        for i, comp in enumerate(abnormal_companies, 1):
            items = comp.get('abnormalItems', [])
            lines.append(f"**{i}. {comp['companyName']}**（{len(items)} 项异常）\n")

            # 按 (核查批次, 核查单位, 核查截止) 分组，相同的信息合并显示
            groups = {}          # key -> [qualify_name, ...]
            group_order = []     # 保持插入顺序
            for item in items:
                detail = item.get('detail') or {}
                qualify_name = item.get('qualifyName', '').replace('专项资质', '')
                check_batch = detail.get('name', '')
                check_officer = detail.get('checkOfficerName', '')
                check_end = detail.get('checkEndTime', '')
                key = (check_batch, check_officer, check_end)
                if key not in groups:
                    groups[key] = []
                    group_order.append(key)
                groups[key].append(qualify_name)

            for key in group_order:
                check_batch, check_officer, check_end = key
                qualify_names = groups[key]
                if len(qualify_names) > 1:
                    qualify_str = '、'.join(qualify_names)
                    lines.append(f"  - 异常资质（{len(qualify_names)} 项）：{qualify_str}")
                else:
                    qualify_str = qualify_names[0] if qualify_names else ''
                    lines.append(f"  - 异常资质：{qualify_str}")
                if check_batch:
                    lines.append(f"  - 核查批次：{check_batch}")
                if check_officer:
                    lines.append(f"  - 核查单位：{check_officer}")
                if check_end:
                    lines.append(f"  - 核查截止：{check_end}")
                lines.append("")
            lines.append("")
    else:
        lines.append(f"### 异常企业列表\n")
        lines.append(f"本次查询未发现资质异常企业。\n")

    content = '\n'.join(lines)
    return title, content


def send_serverchan(sendkey, title, content):
    """
    通过 Server酱 发送消息到微信

    Args:
        sendkey: Server酱的 SendKey
        title: 消息标题
        content: Markdown 内容

    Returns:
        (success: bool, message: str)
    """
    if not sendkey:
        return False, "Server酱 SendKey 未配置"

    try:
        url = f"https://sctapi.ftqq.com/{sendkey}.send"
        data = {
            'title': title[:32],  # Server酱标题限制32字符
            'desp': content
        }
        resp = requests.post(url, data=data, timeout=15)
        result = resp.json()

        if result.get('code') == 0:
            return True, "Server酱推送成功"
        else:
            return False, f"Server酱推送失败: {result.get('message', '未知错误')}"
    except Exception as e:
        return False, f"Server酱请求异常: {e}"


def send_wxpusher(app_token, title, content, topic_ids=None, uids=None):
    """
    通过 WxPusher 发送消息到微信

    Args:
        app_token: WxPusher 应用的 appToken
        title: 消息标题（用作 summary）
        content: Markdown 内容
        topic_ids: 主题ID列表（整数列表），用于群发
        uids: 用户UID列表（字符串列表），用于一对一发送

    Returns:
        (success: bool, message: str)
    """
    if not app_token:
        return False, "WxPusher appToken 未配置"

    if not topic_ids and not uids:
        return False, "WxPusher topicIds 和 uids 均为空，至少需要配置一个"

    try:
        url = "https://wxpusher.zjiecode.com/api/send/message"
        payload = {
            "appToken": app_token,
            "content": content,
            "summary": title[:100],  # summary 最长 100 字符
            "contentType": 3,        # 3 = Markdown
            "verifyPayType": 0,
        }
        if topic_ids:
            # 确保是整数列表
            payload["topicIds"] = [int(t) for t in topic_ids]
        if uids:
            payload["uids"] = list(uids)

        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=15)
        result = resp.json()

        if result.get("code") == 1000:
            data_items = result.get("data", [])
            # 逐条检查每个目标的发送状态
            details = []
            all_ok = True
            for item in data_items:
                uid = item.get("uid", "")
                tid = item.get("topicId", "")
                item_code = item.get("code", 0)
                status = item.get("status", "")
                rid = item.get("sendRecordId", "")
                if item_code == 1000:
                    details.append(f"[OK] uid={uid or tid} rid={rid}")
                else:
                    all_ok = False
                    details.append(f"[FAIL] uid={uid or tid} [{item_code}] {status}")
            if not details:
                details.append("无返回详请（uid/topicId 可能无效或未关注应用）")
                all_ok = False
            detail_str = "; ".join(details)
            if all_ok:
                return True, f"WxPusher推送成功 ({detail_str})"
            else:
                return False, f"WxPusher: {detail_str}"
        else:
            return False, f"WxPusher推送失败: [{result.get('code')}] {result.get('msg', '未知错误')}"
    except Exception as e:
        return False, f"WxPusher请求异常: {e}"


def send_notification(config, result, change_messages=None, no_change_msg=None):
    """
    根据配置发送微信通知

    Args:
        config: 完整配置字典
        result: 抓取结果
        change_messages: 变化检测消息列表
        no_change_msg: 无变化描述

    Returns:
        list of (channel, success, message)
    """
    notif_config = config.get('notification', {})
    results = []

    if not notif_config.get('enabled', False):
        print("  [通知] 通知功能未启用，跳过")
        return results

    # on_change_only 检查
    if notif_config.get('on_change_only', False):
        if not change_messages:
            print("  [通知] 设置为仅变化时通知，本次无变化，跳过")
            return results

    # 生成报告
    title, content = generate_report_text(result, change_messages, no_change_msg)
    print(f"  [通知] 报告标题: {title}")

    # Server酱
    sc_config = notif_config.get('serverchan', {})
    if sc_config.get('enabled', False):
        sendkey = sc_config.get('sendkey', '')
        print("  [通知] 正在发送 Server酱...")
        success, msg = send_serverchan(sendkey, title, content)
        results.append(('Server酱', success, msg))
        print(f"  [通知] Server酱: {'[OK]' if success else '[FAIL]'} {msg}")

    # WxPusher
    wx_config = notif_config.get('wxpusher', {})
    if wx_config.get('enabled', False):
        app_token = wx_config.get('app_token', '')
        topic_ids = wx_config.get('topic_ids', [])
        uids = wx_config.get('uids', [])
        print("  [通知] 正在发送 WxPusher...")
        success, msg = send_wxpusher(app_token, title, content, topic_ids, uids)
        results.append(('WxPusher', success, msg))
        print(f"  [通知] WxPusher: {'[OK]' if success else '[FAIL]'} {msg}")

    if not results:
        print("  [通知] 未配置任何通知渠道")

    return results


def test_notification(config_path='config.ini'):
    """
    测试通知功能，发送一条测试消息

    Args:
        config_path: 配置文件路径（支持 .ini 和 .json）
    """
    # 自动查找配置文件
    if not os.path.exists(config_path):
        base = os.path.splitext(config_path)[0]
        for ext in ['.ini', '.json']:
            alt = base + ext
            if os.path.exists(alt):
                config_path = alt
                break

    if config_path.endswith('.json'):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        cp = configparser.ConfigParser()
        cp.read(config_path, encoding='utf-8')
        config = {}
        for section in cp.sections():
            config[section] = {}
            for key, val in cp.items(section):
                # 推断类型
                if val.lower() in ('true', 'false'):
                    config[section][key] = val.lower() == 'true'
                else:
                    config[section][key] = val
        # 合并 serverchan 到 notification
        if 'notification' not in config:
            config['notification'] = {}
        if 'serverchan' in config:
            config['notification']['serverchan'] = config['serverchan']
        if 'wxpusher' in config:
            # 解析 INI 中的逗号分隔字符串为列表
            wx = config['wxpusher']
            if isinstance(wx.get('topic_ids'), str) and wx['topic_ids'].strip():
                wx['topic_ids'] = [x.strip() for x in wx['topic_ids'].split(',') if x.strip()]
            else:
                wx['topic_ids'] = wx.get('topic_ids', []) or []
            if isinstance(wx.get('uids'), str) and wx['uids'].strip():
                wx['uids'] = [x.strip() for x in wx['uids'].split(',') if x.strip()]
            else:
                wx['uids'] = wx.get('uids', []) or []
            config['notification']['wxpusher'] = wx

    notif_config = config.get('notification', {})
    if not notif_config.get('enabled', False):
        print("通知功能未启用，请先在 config.ini 中设置 notification.enabled = true")
        print(f"  配置文件: {os.path.abspath(config_path)}")
        return

    title = "测试通知 - 质量检测资质异常监控"
    content = """## 测试通知

这是一条来自**质量检测资质异常自动监控程序**的测试消息。

如果您收到此消息，说明通知配置成功！

- 推送渠道：Server酱 / WxPusher
- 程序路径：""" + config_path + """
- 测试时间：自动生成

后续定时任务运行后，将自动推送最新的统计报告。
"""

    print(f"标题: {title}")
    print(f"内容长度: {len(content)} 字符")
    print()

    # 测试 Server酱
    sc_config = notif_config.get('serverchan', {})
    if sc_config.get('enabled', False):
        sendkey = sc_config.get('sendkey', '')
        print("正在测试 Server酱...")
        success, msg = send_serverchan(sendkey, title, content)
        print(f"  {'[OK]' if success else '[FAIL]'} {msg}")
    else:
        print("Server酱 未启用")

    # 测试 WxPusher
    wx_config = notif_config.get('wxpusher', {})
    if wx_config.get('enabled', False):
        app_token = wx_config.get('app_token', '')
        topic_ids = wx_config.get('topic_ids', [])
        uids = wx_config.get('uids', [])
        print("正在测试 WxPusher...")
        success, msg = send_wxpusher(app_token, title, content, topic_ids, uids)
        print(f"  {'[OK]' if success else '[FAIL]'} {msg}")
    else:
        print("WxPusher 未启用")


if __name__ == '__main__':
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.ini'
    print(f"使用配置文件: {config_path}")
    print()
    test_notification(config_path)
