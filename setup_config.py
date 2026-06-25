#!/usr/bin/env python3
"""
交互式配置向导
直接在命令行回答问题，自动生成 config.ini 配置文件
无需手动编辑任何文件！

用法：
  python setup_config.py
"""

import os
import configparser

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')


def ask(prompt, default=None, choices=None):
    """友好的命令行问答"""
    if default:
        prompt = f"{prompt} [默认: {default}]"

    while True:
        val = input(prompt + "\n> ").strip()

        if not val and default:
            val = str(default)

        if not val:
            print("  不能为空，请重新输入\n")
            continue

        if choices:
            val_lower = val.lower()
            for c in choices:
                if isinstance(c, str) and val_lower == c.lower():
                    return c
            print(f"  请输入以下选项之一: {', '.join(choices)}\n")
            continue

        return val


def ask_bool(prompt, default=True):
    """询问是/否"""
    d = "Y" if default else "N"
    val = ask(f"{prompt} (Y/N)", default=d, choices=['Y', 'N', 'y', 'n'])
    return val.upper() == 'Y'


def main():
    print("=" * 60)
    print("  质量检测企业资质异常 - 交互式配置向导")
    print("=" * 60)
    print()
    print("这个向导会帮您一步步设置所有参数，")
    print("无需手动打开任何文件编辑。")
    print()

    # 检查是否已有配置
    if os.path.exists(CONFIG_PATH):
        existing = configparser.ConfigParser()
        existing.read(CONFIG_PATH, encoding='utf-8')
        if not ask_bool("检测到已有 config.ini，是否覆盖？"):
            print("已取消，现有配置文件保持不变。")
            return

    config = configparser.ConfigParser()

    # ---- 通知设置 ----
    print()
    print("─" * 50)
    print("  【第一步】微信通知设置")
    print("─" * 50)
    print()

    enable_notify = ask_bool("是否启用微信通知？", default=True)
    config.add_section('notification')
    config.set('notification', 'enabled', str(enable_notify).lower())
    config.set('notification', 'on_change_only', 'false')

    if enable_notify:
        use_sc = ask_bool("  使用 Server酱 推送？（https://sct.ftqq.com/）", default=True)
        config.add_section('serverchan')
        config.set('serverchan', 'enabled', str(use_sc).lower())
        if use_sc:
            sc_key = ask("  请输入 Server酱 SendKey")
            config.set('serverchan', 'sendkey', sc_key)
            print(f"  已设置 Server酱 SendKey: {sc_key[:8]}...")
        else:
            config.set('serverchan', 'sendkey', '')

        use_wx = ask_bool("  使用 WxPusher 推送？（https://wxpusher.zjiecode.com/）", default=True)
        config.add_section('wxpusher')
        config.set('wxpusher', 'enabled', str(use_wx).lower())
        if use_wx:
            wx_app_token = ask("  请输入 WxPusher appToken")
            config.set('wxpusher', 'app_token', wx_app_token)
            print(f"  已设置 WxPusher appToken: {wx_app_token[:12]}...")
            wx_topic = ask("  请输入 WxPusher topicIds（主题ID，多个用英文逗号分隔，不需要可留空）", default="")
            config.set('wxpusher', 'topic_ids', wx_topic)
            wx_uids = ask("  请输入 WxPusher uids（用户UID，多个用英文逗号分隔，不需要可留空）", default="")
            config.set('wxpusher', 'uids', wx_uids)
        else:
            config.set('wxpusher', 'app_token', '')
            config.set('wxpusher', 'topic_ids', '')
            config.set('wxpusher', 'uids', '')
    else:
        config.add_section('serverchan')
        config.set('serverchan', 'enabled', 'false')
        config.set('serverchan', 'sendkey', '')
        config.add_section('wxpusher')
        config.set('wxpusher', 'enabled', 'false')
        config.set('wxpusher', 'app_token', '')
        config.set('wxpusher', 'topic_ids', '')
        config.set('wxpusher', 'uids', '')

    # ---- 定时设置 ----
    print()
    print("─" * 50)
    print("  【第二步】定时运行设置")
    print("─" * 50)
    print()

    enable_schedule = ask_bool("是否启用定时运行？（每天自动抓取一次）", default=True)
    config.add_section('schedule')
    config.set('schedule', 'enabled', str(enable_schedule).lower())

    if enable_schedule:
        run_time = ask("  每天几点运行？（HH:MM 格式，例如 08:00）", default="08:00")
        config.set('schedule', 'time', run_time)
        weekdays_only = ask_bool("  仅工作日运行？", default=False)
        config.set('schedule', 'weekdays_only', str(weekdays_only).lower())
    else:
        config.set('schedule', 'time', '08:00')
        config.set('schedule', 'weekdays_only', 'false')

    # ---- 其他设置 ----
    print()
    print("─" * 50)
    print("  【第三步】其他设置")
    print("─" * 50)
    print()

    # 平台地址（一般不需要改）
    print("平台地址（一般无需修改，直接回车即可）：")
    base_url = ask("  base_url", default="https://220.160.52.164:8813/credit")
    index_url = ask("  index_url", default="https://220.160.52.164:8813/gaia/infoPublic/index.html")

    config.add_section('platform')
    config.set('platform', 'base_url', base_url)
    config.set('platform', 'index_url', index_url)

    config.add_section('query')
    config.set('query', 'industry_id', '2')
    config.set('query', 'page_size', '30')
    config.set('query', 'request_delay_min', '0.3')
    config.set('query', 'request_delay_max', '0.8')
    config.set('query', 'refresh_token_every', '25')

    # 输出设置
    output_dir = ask("输出目录", default="output")
    config.add_section('output')
    config.set('output', 'output_dir', output_dir)
    config.set('output', 'filename_prefix', '质量检测_资质异常')
    config.set('output', 'keep_history', '30')

    # ---- 保存 ----
    print()
    print("─" * 50)
    print("  正在保存配置...")
    print("─" * 50)

    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        config.write(f)

    print()
    print("=" * 60)
    print("  配置完成！")
    print("=" * 60)
    print()
    print(f"  配置文件: {CONFIG_PATH}")
    print(f"  可以用记事本打开编辑: notepad {CONFIG_PATH}")
    print()
    print("下一步：")
    print("  1. 测试通知: 双击 test_notify.bat")
    print("  2. 手动运行: 双击 run_now.bat")
    print("  3. 安装定时: 双击 install_schedule.bat")
    print()


if __name__ == '__main__':
    main()
