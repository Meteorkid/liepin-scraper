#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘移动端爬虫测试
验证 m.liepin.com 是否可以绕过 IP 限制
"""

import re
import time
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup

# 移动端 User-Agent
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"

def test_mobile_search(keyword: str, city_code: str = ""):
    """测试移动端搜索"""
    session = curl_requests.Session()

    # 构造移动端搜索 URL
    if city_code:
        url = f"https://m.liepin.com/zhaopin/?key={keyword}&dq={city_code}"
    else:
        url = f"https://m.liepin.com/zhaopin/?key={keyword}"

    print(f"测试URL: {url}")

    headers = {
        "User-Agent": MOBILE_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://m.liepin.com/",
    }

    try:
        resp = session.get(url, headers=headers, impersonate="safari17_0", timeout=15)
        print(f"状态码: {resp.status_code}")
        print(f"响应长度: {len(resp.text)} 字符")

        # 检查是否有数据
        if "job-card" in resp.text or "job-card-pc-container" in resp.text:
            print("✓ 找到职位卡片！")
            # 提取职位数量
            job_count = resp.text.count("job-card")
            print(f"  职位卡片数量: {job_count}")
        elif "暂无搜索结果" in resp.text or "没有找到" in resp.text:
            print("✗ 无搜索结果")
        else:
            print("? 未知响应，保存到文件分析")
            with open("/Users/meteor/爬虫实习项目/猎聘/爬虫代码/mobile_response.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            print("  已保存到 mobile_response.html")

        return resp.text

    except Exception as e:
        print(f"请求失败: {e}")
        return None

def test_mobile_api(keyword: str, city_code: str = ""):
    """测试移动端 API"""
    session = curl_requests.Session()

    # 尝试常见的 API 端点
    api_urls = [
        f"https://m.liepin.com/api/com.liepin.searchfront4c.pc-search-job?key={keyword}&dq={city_code}",
        f"https://m.liepin.com/api/search/job?key={keyword}&city={city_code}",
        f"https://api-m.liepin.com/search/job?key={keyword}",
    ]

    headers = {
        "User-Agent": MOBILE_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://m.liepin.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    for api_url in api_urls:
        print(f"\n测试API: {api_url}")
        try:
            resp = session.get(api_url, headers=headers, impersonate="safari17_0", timeout=10)
            print(f"  状态码: {resp.status_code}")
            print(f"  响应长度: {len(resp.text)} 字符")

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"  JSON响应: {str(data)[:200]}...")
                except:
                    print(f"  非JSON响应: {resp.text[:200]}...")

        except Exception as e:
            print(f"  请求失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("猎聘移动端爬虫测试")
    print("=" * 60)

    # 测试1: 移动端搜索页面
    print("\n【测试1】移动端搜索页面")
    test_mobile_search("矿产开采")

    # 测试2: 移动端搜索页面（带城市）
    print("\n【测试2】移动端搜索页面（北京）")
    test_mobile_search("矿产开采", "010")

    # 测试3: 移动端 API
    print("\n【测试3】移动端 API")
    test_mobile_api("矿产开采")
