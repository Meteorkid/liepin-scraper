#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘移动端爬虫 v2
尝试不同的 URL 格式和 API 端点
"""

import json
import time
from curl_cffi import requests as curl_requests

# 移动端 User-Agent
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"

def test_different_formats():
    """测试不同的 URL 格式"""
    session = curl_requests.Session()

    headers = {
        "User-Agent": MOBILE_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 测试不同的 URL 格式
    test_urls = [
        # 格式1: 关键词搜索
        "https://m.liepin.com/zhaopin/?key=%E7%9F%BF%E4%BA%A7%E5%BC%80%E9%87%87",
        # 格式2: 行业页面
        "https://m.liepin.com/career/nengyuankuangchanhuanbao/",
        # 格式3: 城市+行业
        "https://m.liepin.com/city-bj/zhaopin/?key=%E7%9F%BF%E4%BA%A7%E5%BC%80%E9%87%87",
        # 格式4: 直接职位列表
        "https://m.liepin.com/zhaopin/list/?key=%E7%9F%BF%E4%BA%A7%E5%BC%80%E9%87%87",
        # 格式5: API 端点
        "https://m.liepin.com/api/com.liepin.searchfront4c.pc-search-job?key=%E7%9F%BF%E4%BA%A7%E5%BC%80%E9%87%87&dq=010&curPage=0&pageSize=40",
    ]

    for url in test_urls:
        print(f"\n测试: {url}")
        try:
            resp = session.get(url, headers=headers, impersonate="safari17_0", timeout=10)
            print(f"  状态码: {resp.status_code}, 长度: {len(resp.text)}")

            # 检查是否有职位数据
            if "job-card" in resp.text:
                count = resp.text.count("job-card")
                print(f"  ✓ 找到 {count} 个职位卡片！")
            elif "暂无" in resp.text or "没有" in resp.text:
                print(f"  ✗ 无结果")
            else:
                print(f"  ? 未知响应")

        except Exception as e:
            print(f"  失败: {e}")

def test_pc_api_with_mobile_ua():
    """用移动端 UA 访问 PC 端 API"""
    session = curl_requests.Session()

    headers = {
        "User-Agent": MOBILE_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://m.liepin.com/",
        "Origin": "https://m.liepin.com",
    }

    # PC 端搜索 API
    api_url = "https://www.liepin.com/api/com.liepin.searchfront4c.pc-search-job"
    params = {
        "key": "矿产开采",
        "dq": "010",
        "curPage": "0",
        "pageSize": "40",
    }

    print(f"\n测试 PC API (移动端UA): {api_url}")
    try:
        resp = session.get(api_url, params=params, headers=headers, impersonate="safari17_0", timeout=10)
        print(f"  状态码: {resp.status_code}, 长度: {len(resp.text)}")

        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"  JSON: {str(data)[:300]}...")
            except:
                print(f"  非JSON: {resp.text[:200]}...")

    except Exception as e:
        print(f"  失败: {e}")

def test_career_page():
    """测试行业分类页面"""
    session = curl_requests.Session()

    headers = {
        "User-Agent": MOBILE_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 行业分类页面
    urls = [
        "https://m.liepin.com/career/nengyuankuangchanhuanbao/",
        "https://m.liepin.com/career/gongwuyuannonglinmuyuqt/",
    ]

    for url in urls:
        print(f"\n测试行业页面: {url}")
        try:
            resp = session.get(url, headers=headers, impersonate="safari17_0", timeout=10)
            print(f"  状态码: {resp.status_code}, 长度: {len(resp.text)}")

            if "job-card" in resp.text:
                count = resp.text.count("job-card")
                print(f"  ✓ 找到 {count} 个职位卡片！")
            else:
                print(f"  ✗ 无职位数据")

        except Exception as e:
            print(f"  失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("猎聘移动端爬虫 v2 测试")
    print("=" * 60)

    test_different_formats()
    test_pc_api_with_mobile_ua()
    test_career_page()
