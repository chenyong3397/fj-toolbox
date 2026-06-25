# -*- coding: utf-8 -*-
"""
资质异常监控 Blueprint
挂载路径: /api/qualify  (同时兼容根路径 /)
"""

import os
import json
import time
import subprocess
import threading
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, send_file

bp = Blueprint('qualify_abnormal', __name__, url_prefix='/api/qualify')


def get_info():
    """模块信息（供 /modules 接口使用）"""
    return {
        'name': '异常预警',
        'desc': '福建省质量检测资质异常企业查询',
        'icon': '🔍',
        'page': '/pages/qualify/qualify',
        'url_prefix': '/api/qualify',
        'bg': '#185FA5'
    }


# ========== 全局状态（每个 blueprint 独立管理自己的状态）==========
task_status = {
    'running': False,
    'last_run_time': None,
    'last_success_time': None,
    'last_error': None,
    'last_result': None,
    'run_count': 0
}
status_lock = threading.Lock()

# ========== 工具函数 ==========

def get_config():
    """读取 config.ini 中的配置"""
    import configparser
    cp = configparser.ConfigParser()
    cfg_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.ini')
    cfg_file = os.path.normpath(cfg_file)
    cp.read(cfg_file, encoding='utf-8')
    return cp


def check_token(req, cfg=None):
    """验证请求中的 Token"""
    if cfg is None:
        cfg = get_config()
    try:
        api_token = cfg.get('api', 'token', fallback='fj-qualify-2026')
    except Exception:
        api_token = 'fj-qualify-2026'

    # URL 参数 ?token=xxx
    t = req.args.get('token', '')
    if not t:
        auth = req.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            t = auth[7:]
    return t == api_token


def get_script_path():
    """获取主程序路径"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scrape_qualify_abnormal.py')


def get_output_dir():
    """获取输出目录"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output')


def run_scrape_task():
    """后台运行抓取任务（直接调用 scraper，避免子进程问题）"""
    global task_status
    with status_lock:
        task_status['running'] = True
        task_status['last_run_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task_status['last_error'] = None

    import sys
    import io
    project_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    sys.path.insert(0, project_root)

    try:
        from scrape_qualify_abnormal import (
            run_scrape, generate_excel, check_whats_changed,
            load_historical_baseline, save_change_history, load_config
        )

        # 使用 scraper 自带的 load_config（处理类型转换）
        cfg_file = os.path.join(project_root, 'config.ini')
        config = load_config(cfg_file)

        # 准备日志文件（捕获 scraper 的 print 输出）
        log_file = os.path.join(
            get_output_dir(),
            f"api_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # 重定向 stdout 以捕获输出
        old_stdout = sys.stdout
        log_buffer = io.StringIO()
        sys.stdout = log_buffer

        try:
            print(f"[INFO] 开始抓取 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # 1. 运行抓取
            result = run_scrape(config)

            if not result:
                print("[ERROR] 抓取失败：无返回结果")
                with status_lock:
                    task_status['running'] = False
                    task_status['last_error'] = '抓取失败：无返回结果'
                return

            # 2. 生成 Excel
            output_dir = config["output"]["output_dir"]
            prefix = config["output"]["filename_prefix"]
            output_file, latest_file = generate_excel(result, config)
            print(f"[INFO] Excel 已生成: {output_file}")

            # 3. 加载历史基准数据（7天前）
            old_result = load_historical_baseline(output_dir, prefix, days_ago=7)

            # 4. 变化检测
            change_result = check_whats_changed(old_result, result)
            print(f"[INFO] 变化检测: has_change={change_result['has_change']}, messages={len(change_result['messages'])}")

            # 5. 保存变化历史
            save_change_history(config, change_result)
            print(f"[INFO] 变化历史已保存")

            # 6. 读取最终结果
            result_file = os.path.join(get_output_dir(), "质量检测_资质异常_最新.json")
            final_result = None
            if os.path.exists(result_file):
                with open(result_file, 'r', encoding='utf-8') as f:
                    final_result = json.load(f)
                print(f"[INFO] 最终结果: {final_result['abnormal_count']} 家异常")

            with status_lock:
                task_status['running'] = False
                task_status['last_success_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                task_status['last_result'] = final_result
                task_status['run_count'] += 1

            print(f"[OK] 抓取任务完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        finally:
            sys.stdout = old_stdout
            # 写入日志文件
            log_content = log_buffer.getvalue()
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            log_buffer.close()

    except Exception as e:
        import traceback
        with status_lock:
            task_status['running'] = False
            task_status['last_error'] = str(e)
        print(f"[ERROR] 抓取任务失败: {e}")
        traceback.print_exc()

        # 确保日志被保存
        try:
            log_content = log_buffer.getvalue()
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            log_buffer.close()
        except Exception:
            pass


# ========== 路由 ==========

@bp.route('/run', methods=['POST', 'GET'])
def trigger_run():
    """触发抓取任务"""
    cfg = get_config()
    if not check_token(request, cfg):
        return jsonify({'code': 401, 'msg': 'Token验证失败'}), 401

    with status_lock:
        if task_status['running']:
            return jsonify({'code': 409, 'msg': '已有任务正在运行，请稍后再试'})

    t = threading.Thread(target=run_scrape_task, daemon=True)
    t.start()

    return jsonify({'code': 0, 'msg': '任务已启动，请稍后查询状态', 'data': {'running': True}})


@bp.route('/status', methods=['GET'])
def get_status():
    """查询运行状态"""
    cfg = get_config()
    if not check_token(request, cfg):
        return jsonify({'code': 401, 'msg': 'Token验证失败'}), 401

    with status_lock:
        return jsonify({
            'code': 0,
            'data': {
                'running': task_status['running'],
                'last_run_time': task_status['last_run_time'],
                'last_success_time': task_status['last_success_time'],
                'last_error': task_status['last_error'],
                'run_count': task_status['run_count'],
                'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })


@bp.route('/report', methods=['GET'])
def get_report():
    """获取最新报告数据"""
    cfg = get_config()
    if not check_token(request, cfg):
        return jsonify({'code': 401, 'msg': 'Token验证失败'}), 401

    result_file = os.path.join(get_output_dir(), "质量检测_资质异常_最新.json")
    if not os.path.exists(result_file):
        return jsonify({'code': 404, 'msg': '暂无报告数据，请先运行抓取'}), 404

    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return jsonify({'code': 0, 'data': result})
    except Exception as e:
        return jsonify({'code': 500, 'msg': f'读取报告失败: {e}'}), 500


@bp.route('/report/latest-file', methods=['GET'])
def download_report():
    """下载最新Excel报告"""
    cfg = get_config()
    if not check_token(request, cfg):
        return jsonify({'code': 401, 'msg': 'Token验证失败'}), 401

    excel_file = os.path.join(get_output_dir(), "质量检测_资质异常_最新.xlsx")
    if not os.path.exists(excel_file):
        return jsonify({'code': 404, 'msg': '暂无Excel报告文件'}), 404

    return send_file(excel_file, as_attachment=True, download_name='质量检测_资质异常_最新.xlsx')


@bp.route('/report-summary', methods=['GET'])
def get_report_summary():
    """获取格式化报告摘要（与微信推送格式一致）"""
    # /report-summary 无需Token（小程序首页加载时使用）
    result_file = os.path.join(get_output_dir(), "质量检测_资质异常_最新.json")
    if not os.path.exists(result_file):
        return jsonify({'code': 404, 'msg': '暂无报告数据，请先运行抓取'}), 404

    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
    except Exception as e:
        return jsonify({'code': 500, 'msg': f'读取报告失败: {e}'}), 500

    # 构建与微信推送一致的格式化数据
    scrape_time = result.get('scrape_time', '')
    total = result.get('total_companies', 0)
    abnormal_count = result.get('abnormal_count', 0)
    normal_count = result.get('normal_count', 0)
    error_count = result.get('error_count', 0)
    abnormal_companies = result.get('abnormal_companies', [])
    total_items = sum(len(c.get('abnormalItems', [])) for c in abnormal_companies)
    pct = abnormal_count / max(total, 1) * 100

    # 统计数据
    stats = {
        'scrape_time': scrape_time,
        'total_companies': total,
        'abnormal_count': abnormal_count,
        'abnormal_items': total_items,
        'normal_count': normal_count,
        'error_count': error_count,
        'abnormal_pct': f"{pct:.1f}%"
    }

    # 尝试读取变化历史（保留最近7天）
    output_dir = get_output_dir()
    changes = {'has_change': False, 'messages': [], 'history': [], 'changed_companies': []}

    history_file = os.path.join(output_dir, "change_history.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            all_changes = history_data.get("changes", [])

            # 收集7天内所有变化消息 + 按企业聚合
            cutoff = datetime.now() - timedelta(days=7)
            companies_map = {}  # {name: {"name": ..., "events": [{"type": "新增/恢复/变更", "time": "..."}], "days": set()}}

            for entry in all_changes:
                try:
                    entry_time = datetime.strptime(entry.get("time", ""), '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
                if entry_time < cutoff:
                    continue

                has = entry.get("has_change", False)
                msg_list = entry.get("messages", [])
                nc_msg = entry.get("no_change_msg", "")
                st = entry.get("stats", {})
                companies_data = entry.get("companies", {})

                entry_data = {
                    "time": entry.get("time", ""),
                    "has_change": has,
                    "messages": msg_list if has else [],
                    "no_change_msg": nc_msg if not has else "",
                    "stats": st
                }
                changes["history"].append(entry_data)

                if has:
                    changes["has_change"] = True
                    for msg in msg_list:
                        if msg not in changes["messages"]:
                            changes["messages"].append(msg)

                    # 按企业聚合变化
                    time_str = entry.get("time", "")
                    date_str = time_str[:10] if len(time_str) >= 10 else time_str
                    for name in companies_data.get("added", []):
                        if name not in companies_map:
                            companies_map[name] = {"name": name, "events": [], "days": set()}
                        companies_map[name]["events"].append({"type": "新增异常", "time": time_str})
                        companies_map[name]["days"].add(date_str)
                    for name in companies_data.get("removed", []):
                        if name not in companies_map:
                            companies_map[name] = {"name": name, "events": [], "days": set()}
                        companies_map[name]["events"].append({"type": "恢复正常", "time": time_str})
                        companies_map[name]["days"].add(date_str)
                    for name in companies_data.get("changed", []):
                        if name not in companies_map:
                            companies_map[name] = {"name": name, "events": [], "days": set()}
                        companies_map[name]["events"].append({"type": "异常项变更", "time": time_str})
                        companies_map[name]["days"].add(date_str)

            # 按时间倒序排列（最新的在前）
            changes["history"].reverse()

            # 近7天有变化的企业（按出现天数降序、名称升序）
            changed_companies = []
            for name, info in companies_map.items():
                info["day_count"] = len(info["days"])
                info["days"] = sorted(list(info["days"]))  # set → list（可JSON序列化）
                info["events"].sort(key=lambda e: e["time"], reverse=True)
                changed_companies.append(info)
            changed_companies.sort(key=lambda c: (-c["day_count"], c["name"]))
            changes["changed_companies"] = changed_companies

        except Exception:
            pass

    # 如果变化历史为空，回退到 7 天前对比逻辑（兼容首次使用）
    if not changes["history"]:
        old_files = []
        for fname in os.listdir(output_dir):
            if fname.startswith('质量检测_资质异常_') and fname.endswith('.json') and '_最新' not in fname:
                old_files.append(fname)

        if old_files:
            # 找到最接近 7 天前的历史文件
            target_time = datetime.now() - timedelta(days=7)
            candidates = []
            for fname in old_files:
                base = fname[len('质量检测_资质异常_') : -5]
                try:
                    file_time = datetime.strptime(base, '%Y%m%d_%H%M%S')
                except ValueError:
                    continue
                diff = abs((file_time - target_time).total_seconds())
                if diff <= 14 * 86400:
                    candidates.append((diff, fname))

            if not candidates:
                # 没有 7 天附近的数据，用最早的
                all_with_time = []
                for fname in old_files:
                    base = fname[len('质量检测_资质异常_') : -5]
                    try:
                        file_time = datetime.strptime(base, '%Y%m%d_%H%M%S')
                        all_with_time.append((file_time, fname))
                    except ValueError:
                        continue
                if all_with_time:
                    all_with_time.sort()
                    candidates = [(0, all_with_time[0][1])]
                else:
                    candidates = []

            if candidates:
                candidates.sort()
                old_fname = candidates[0][1]
                old_file = os.path.join(output_dir, old_fname)
                try:
                    with open(old_file, 'r', encoding='utf-8') as f:
                        old_result = json.load(f)
                    old_companies = {c['companyName']: c for c in old_result.get('abnormal_companies', [])}
                    new_companies = {c['companyName']: c for c in abnormal_companies}
                    old_names = set(old_companies.keys())
                    new_names = set(new_companies.keys())

                    added = new_names - old_names
                    removed = old_names - new_names

                    if added:
                        changes['has_change'] = True
                        for name in added:
                            items = new_companies[name]['abnormalItems']
                            reasons = '；'.join(item.get('qualifyName', '') for item in items)
                            changes['messages'].append(f'新增异常企业：{name}（{len(items)} 项：{reasons}）')
                    if removed:
                        changes['has_change'] = True
                        for name in removed:
                            changes['messages'].append(f'恢复正常：{name}')

                    # 检查仍在列表中的企业异常项是否变化
                    common = old_names & new_names
                    for name in common:
                        old_items = {item.get('qualifyName', '') for item in old_companies[name]['abnormalItems']}
                        new_items = {item.get('qualifyName', '') for item in new_companies[name]['abnormalItems']}
                        if old_items != new_items:
                            changes['has_change'] = True
                            changes['messages'].append(f'异常项发生变化：{name}')
                except Exception:
                    pass

    # 格式化企业列表（与微信推送分组逻辑一致）
    companies = []
    for comp in abnormal_companies:
        items = comp.get('abnormalItems', [])
        groups_map = {}
        group_order = []

        for item in items:
            detail = item.get('detail') or {}
            qualify_name = item.get('qualifyName', '').replace('专项资质', '')
            check_batch = detail.get('name', '')
            check_officer = detail.get('checkOfficerName', '')
            check_end = detail.get('checkEndTime', '')
            key = (check_batch, check_officer, check_end)
            if key not in groups_map:
                groups_map[key] = []
                group_order.append(key)
            groups_map[key].append(qualify_name)

        groups = []
        for key in group_order:
            check_batch, check_officer, check_end = key
            groups.append({
                'qualify_names': groups_map[key],
                'qualify_count': len(groups_map[key]),
                'check_batch': check_batch,
                'check_officer': check_officer,
                'check_end': check_end
            })

        companies.append({
            'name': comp['companyName'],
            'total_items': len(items),
            'group_count': len(groups),
            'groups': groups
        })

    return jsonify({
        'code': 0,
        'data': {
            'report_time': scrape_time,
            'stats': stats,
            'changes': changes,
            'companies': companies
        }
    })


# ========== 根路径兼容（无 /api/qualify 前缀，直接 /run 等）==========
# 这些路由注册到 bp 但不带前缀，供主 app.py 选择性注册

def register_root_routes(app_ref):
    """
    将部分路由注册到根路径（向后兼容）
    在主 app.py 中调用：qualify_abnormal.register_root_routes(app)
    """
    # 用不同类型的函数名避免冲突
    @app_ref.route('/run', methods=['POST', 'GET'])
    def _root_run():
        return trigger_run()

    @app_ref.route('/status', methods=['GET'])
    def _root_status():
        return get_status()

    @app_ref.route('/report', methods=['GET'])
    def _root_report():
        return get_report()

    @app_ref.route('/report-summary', methods=['GET'])
    def _root_summary():
        return get_report_summary()

    @app_ref.route('/report/latest-file', methods=['GET'])
    def _root_download():
        return download_report()
