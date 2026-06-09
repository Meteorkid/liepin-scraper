#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控爬虫状态并定期保存数据
"""

import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# 配置
SCRAPER_LOG = Path("/Users/meteor/爬虫实习项目/猎聘/爬虫代码/scraper_v2.log")
OUTPUT_DIR = Path("/Users/meteor/爬虫实习项目/猎聘/爬虫代码")
CHECK_INTERVAL = 60  # 每60秒检查一次

def get_scraper_pid():
    """获取爬虫进程PID"""
    try:
        result = os.popen("ps aux | grep 'liepin_full_scraper_v2.py' | grep -v grep").read()
        if result.strip():
            parts = result.strip().split()
            return int(parts[1])
    except:
        pass
    return None

def extract_jobs_from_log():
    """从日志中提取职位数据"""
    jobs = []

    try:
        with open(SCRAPER_LOG, 'r', encoding='utf-8') as f:
            content = f.read()

        # 这里需要解析日志来提取职位数据
        # 由于日志中没有完整的职位数据，我们需要从其他来源获取
        # 暂时返回空列表
        pass
    except Exception as e:
        print(f"读取日志失败: {e}")

    return jobs

def save_checkpoint(data, checkpoint_file):
    """保存检查点"""
    try:
        if data:
            df = pd.DataFrame(data)
            df.to_excel(checkpoint_file, index=False, engine='openpyxl')
            print(f"✅ 检查点已保存: {checkpoint_file}, 共 {len(df)} 条记录")
    except Exception as e:
        print(f"❌ 保存检查点失败: {e}")

def main():
    print("🔍 启动爬虫监控...")
    print(f"📁 日志文件: {SCRAPER_LOG}")
    print(f"⏱️  检查间隔: {CHECK_INTERVAL}秒")
    print("="*60)

    last_pid = None
    checkpoint_count = 0

    while True:
        try:
            # 检查爬虫进程
            current_pid = get_scraper_pid()

            if current_pid:
                if last_pid is None:
                    print(f"✅ 检测到爬虫进程 PID: {current_pid}")
                last_pid = current_pid

                # 检查日志更新
                if SCRAPER_LOG.exists():
                    mtime = datetime.fromtimestamp(SCRAPER_LOG.stat().st_mtime)
                    age = (datetime.now() - mtime).total_seconds()

                    if age > 300:  # 5分钟没有更新
                        print(f"⚠️  日志已 {age:.0f} 秒未更新，爬虫可能卡住")
            else:
                if last_pid:
                    print(f"❌ 爬虫进程已停止 (之前PID: {last_pid})")
                    last_pid = None

                    # 尝试从日志中提取数据并保存
                    jobs = extract_jobs_from_log()
                    if jobs:
                        checkpoint_file = OUTPUT_DIR / f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        save_checkpoint(jobs, checkpoint_file)

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n🛑 监控已停止")
            break
        except Exception as e:
            print(f"❌ 监控异常: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
