#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘详情页反爬研究
目标：分析详情页反爬机制，找到获取工作内容、任职要求、福利标签等字段的方法
"""

import json
import time
import re
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup

# 测试URL
TEST_URL = "https://www.liepin.com/a/76135965.shtml"
TEST_URL_2 = "https://www.liepin.com/job/76135965.shtml"

# 不同的User-Agent组合
USER_AGENTS = {
    "chrome_windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "chrome_mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "firefox_windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "safari_mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
}


def test_basic_request():
    """测试1: 基本请求 - 不同UA组合"""
    print("=" * 60)
    print("测试1: 基本请求测试")
    print("=" * 60)

    for ua_name, ua in USER_AGENTS.items():
        print(f"\n--- UA: {ua_name} ---")
        try:
            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }

            resp = curl_requests.get(TEST_URL, headers=headers, impersonate="chrome120")
            print(f"  状态码: {resp.status_code}")
            print(f"  页面大小: {len(resp.text)} bytes")
            print(f"  标题: {resp.text[:200]}...")

            if resp.status_code == 200 and len(resp.text) > 1000:
                print(f"  [成功] 可能获取到页面")
            else:
                print(f"  [失败] 可能被拦截")

        except Exception as e:
            print(f"  [错误] {e}")


def test_with_referer():
    """测试2: 带Referer的请求"""
    print("\n" + "=" * 60)
    print("测试2: 带Referer的请求")
    print("=" * 60)

    referers = [
        "https://www.liepin.com/",
        "https://www.liepin.com/zhaopin/",
        "https://www.liepin.com/career/",
        None,
    ]

    for referer in referers:
        print(f"\n--- Referer: {referer or 'None'} ---")
        try:
            headers = {
                "User-Agent": USER_AGENTS["chrome_windows"],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": referer,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            }

            resp = curl_requests.get(TEST_URL, headers=headers, impersonate="chrome120")
            print(f"  状态码: {resp.status_code}")
            print(f"  页面大小: {len(resp.text)} bytes")

            # 检查是否包含详情内容
            if "job-content" in resp.text or "job-detail" in resp.text:
                print(f"  [成功] 可能包含职位详情")
            else:
                print(f"  [未知] 需要进一步分析")

        except Exception as e:
            print(f"  [错误] {e}")


def test_with_cookies():
    """测试3: 带Cookie的请求"""
    print("\n" + "=" * 60)
    print("测试3: 带Cookie的请求")
    print("=" * 60)

    # 先访问首页获取cookie
    print("先访问首页获取cookie...")
    try:
        session = curl_requests.Session()
        session.headers.update({
            "User-Agent": USER_AGENTS["chrome_windows"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

        # 访问首页
        home_resp = session.get("https://www.liepin.com/", impersonate="chrome120")
        print(f"  首页状态码: {home_resp.status_code}")
        print(f"  获取的cookies: {dict(session.cookies)}")

        time.sleep(2)

        # 带cookie访问详情页
        detail_resp = session.get(TEST_URL, impersonate="chrome120")
        print(f"\n  详情页状态码: {detail_resp.status_code}")
        print(f"  页面大小: {len(detail_resp.text)} bytes")

        # 分析页面内容
        soup = BeautifulSoup(detail_resp.text, 'html.parser')

        # 检查是否有职位标题
        title_tag = soup.find('title')
        if title_tag:
            print(f"  页面标题: {title_tag.string}")

        # 检查是否有职位内容
        job_content = soup.find('div', class_='job-content')
        if job_content:
            print(f"  [成功] 找到job-content元素")
            print(f"  内容长度: {len(job_content.get_text())} chars")
        else:
            print(f"  [未找到] job-content元素")

        # 检查是否有职位要求
        job_require = soup.find('div', class_='job-require')
        if job_require:
            print(f"  [成功] 找到job-require元素")
            print(f"  内容长度: {len(job_require.get_text())} chars")

        # 检查是否有标签
        tags = soup.find_all('span', class_='tags-tag')
        if tags:
            print(f"  [成功] 找到 {len(tags)} 个标签")

        # 保存页面内容用于分析
        with open('/Users/meteor/爬虫实习项目/猎聘/爬虫代码/liepin_detail_debug.html', 'w', encoding='utf-8') as f:
            f.write(detail_resp.text)
        print(f"  页面已保存到liepin_detail_debug.html")

    except Exception as e:
        print(f"  [错误] {e}")


def test_job_url_format():
    """测试4: 不同URL格式"""
    print("\n" + "=" * 60)
    print("测试4: 不同URL格式")
    print("=" * 60)

    url_formats = [
        "https://www.liepin.com/a/76135965.shtml",
        "https://www.liepin.com/job/76135965.shtml",
        "https://www.liepin.com/jobdetail/76135965",
        "https://www.liepin.com/zhaopin/detail/76135965",
    ]

    session = curl_requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENTS["chrome_windows"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    # 先访问首页
    session.get("https://www.liepin.com/", impersonate="chrome120")
    time.sleep(1)

    for url in url_formats:
        print(f"\n--- URL: {url} ---")
        try:
            resp = session.get(url, impersonate="chrome120")
            print(f"  状态码: {resp.status_code}")
            print(f"  页面大小: {len(resp.text)} bytes")

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    print(f"  页面标题: {title_tag.string[:50]}...")
        except Exception as e:
            print(f"  [错误] {e}")


def test_api_endpoints():
    """测试5: 探索API接口"""
    print("\n" + "=" * 60)
    print("测试5: 探索API接口")
    print("=" * 60)

    job_id = "76135965"

    # 可能的API端点
    api_endpoints = [
        f"https://www.liepin.com/api/com.liepin.homepage.get-job-detail?jobId={job_id}",
        f"https://www.liepin.com/api/job/detail?jobId={job_id}",
        f"https://api.liepin.com/job/detail?jobId={job_id}",
        f"https://www.liepin.com/job/api/detail?jobId={job_id}",
        f"https://www.liepin.com/a/api/detail?jobId={job_id}",
    ]

    session = curl_requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENTS["chrome_windows"],
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://www.liepin.com/a/{job_id}.shtml",
    })

    # 先访问首页
    session.get("https://www.liepin.com/", impersonate="chrome120")
    time.sleep(1)

    for api_url in api_endpoints:
        print(f"\n--- API: {api_url} ---")
        try:
            resp = session.get(api_url, impersonate="chrome120")
            print(f"  状态码: {resp.status_code}")
            print(f"  响应大小: {len(resp.text)} bytes")
            print(f"  Content-Type: {resp.headers.get('content-type', 'unknown')}")
            print(f"  响应前200字符: {resp.text[:200]}")
        except Exception as e:
            print(f"  [错误] {e}")


def test_mobile_api():
    """测试6: 移动端API"""
    print("\n" + "=" * 60)
    print("测试6: 移动端API")
    print("=" * 60)

    job_id = "76135965"

    mobile_apis = [
        f"https://m.liepin.com/job/{job_id}",
        f"https://m.liepin.com/a/{job_id}.shtml",
    ]

    mobile_headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    session = curl_requests.Session()
    session.headers.update(mobile_headers)

    for url in mobile_apis:
        print(f"\n--- Mobile URL: {url} ---")
        try:
            resp = session.get(url, impersonate="safari17_2_ios")
            print(f"  状态码: {resp.status_code}")
            print(f"  页面大小: {len(resp.text)} bytes")

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    print(f"  页面标题: {title_tag.string[:50] if title_tag.string else 'None'}")
        except Exception as e:
            print(f"  [错误] {e}")


def test_list_page_hidden_data():
    """测试7: 列表页是否有隐藏数据"""
    print("\n" + "=" * 60)
    print("测试7: 列表页隐藏数据分析")
    print("=" * 60)

    # 访问搜索页面
    search_url = "https://www.liepin.com/zhaopin/?key=Python"

    session = curl_requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENTS["chrome_windows"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })

    # 先访问首页
    session.get("https://www.liepin.com/", impersonate="chrome120")
    time.sleep(2)

    # 访问搜索页
    resp = session.get(search_url, impersonate="chrome120")
    print(f"搜索页状态码: {resp.status_code}")
    print(f"页面大小: {len(resp.text)} bytes")

    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 查找工作卡片
        cards = soup.find_all('div', class_=lambda x: x and 'job-card-pc-container' in str(x))
        print(f"找到 {len(cards)} 个工作卡片")

        if cards:
            # 分析第一个卡片的所有属性
            card = cards[0]
            print(f"\n第一个卡片HTML:")
            print(str(card)[:2000])

            # 查找所有data-*属性
            print("\n所有data-*属性:")
            for elem in card.find_all(True):
                for attr_name, attr_value in elem.attrs.items():
                    if attr_name.startswith('data-'):
                        print(f"  {attr_name}: {str(attr_value)[:100]}")

            # 查找script标签中的JSON数据
            scripts = card.find_all('script')
            if scripts:
                print(f"\n找到 {len(scripts)} 个script标签")

            # 查找隐藏的input
            hidden_inputs = card.find_all('input', type='hidden')
            if hidden_inputs:
                print(f"\n找到 {len(hidden_inputs)} 个隐藏input")
                for inp in hidden_inputs:
                    print(f"  {inp.get('name', 'unnamed')}: {inp.get('value', '')[:50]}")


def analyze_debug_html():
    """分析已保存的debug HTML"""
    print("\n" + "=" * 60)
    print("分析已保存的debug HTML")
    print("=" * 60)

    try:
        with open('/Users/meteor/爬虫实习项目/猎聘/爬虫代码/liepin_detail_debug.html', 'r', encoding='utf-8') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')

        # 查找所有可能的职位相关内容
        print("\n查找包含 'job' 的class:")
        for elem in soup.find_all(class_=lambda x: x and 'job' in str(x).lower()):
            class_name = elem.get('class')
            text = elem.get_text(strip=True)[:100] if elem.get_text(strip=True) else ''
            print(f"  Class: {class_name}, Text: {text}")

        # 查找所有script标签中的数据
        print("\n查找script中的数据:")
        for script in soup.find_all('script'):
            if script.string and ('job' in script.string.lower() or 'detail' in script.string.lower()):
                print(f"  Script内容前500字符: {script.string[:500]}")

        # 查找__NEXT_DATA__或类似的数据
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            print(f"\n找到__NEXT_DATA__:")
            print(next_data.string[:500] if next_data.string else "Empty")

        # 检查是否有404标识
        if '404' in content or 'not found' in content.lower():
            print("\n[警告] 页面包含404或not found内容")

    except FileNotFoundError:
        print("debug HTML文件不存在，请先运行test_with_cookies()")


def test_xhr_api():
    """测试8: XHR API接口（需要从浏览器网络请求中分析）"""
    print("\n" + "=" * 60)
    print("测试8: XHR API接口测试")
    print("=" * 60)

    # 常见的猎聘API端点（需要验证）
    job_id = "76135965"

    api_tests = [
        {
            "url": f"https://www.liepin.com/api/com.liepin.homepage.get-job-detail?jobId={job_id}",
            "desc": "获取职位详情API"
        },
        {
            "url": f"https://www.liepin.com/api/job/get-job-info?jobId={job_id}",
            "desc": "职位信息API"
        },
        {
            "url": f"https://www.liepin.com/api/v1/job/detail?jobId={job_id}",
            "desc": "v1版本API"
        },
        {
            "url": f"https://api-c.liepin.com/api/job/detail?jobId={job_id}",
            "desc": "API-C版本"
        },
    ]

    session = curl_requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENTS["chrome_windows"],
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": f"https://www.liepin.com/a/{job_id}.shtml",
        "Origin": "https://www.liepin.com",
    })

    # 先访问首页和详情页建立会话
    print("建立会话...")
    session.get("https://www.liepin.com/", impersonate="chrome120")
    time.sleep(1)
    session.get(f"https://www.liepin.com/a/{job_id}.shtml", impersonate="chrome120")
    time.sleep(1)

    for api_test in api_tests:
        print(f"\n--- {api_test['desc']} ---")
        print(f"URL: {api_test['url']}")
        try:
            resp = session.get(api_test["url"], impersonate="chrome120")
            print(f"状态码: {resp.status_code}")
            print(f"Content-Type: {resp.headers.get('content-type', 'unknown')}")
            print(f"响应大小: {len(resp.text)} bytes")

            if resp.status_code == 200:
                try:
                    data = json.loads(resp.text)
                    print(f"JSON数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
                except:
                    print(f"响应内容: {resp.text[:500]}")
        except Exception as e:
            print(f"[错误] {e}")


if __name__ == "__main__":
    print("猎聘详情页反爬研究")
    print("=" * 60)

    # 按顺序运行测试
    test_basic_request()
    test_with_referer()
    test_with_cookies()
    test_job_url_format()
    test_api_endpoints()
    test_mobile_api()
    test_xhr_api()

    print("\n" + "=" * 60)
    print("研究完成！")
    print("请检查生成的 liepin_detail_debug.html 文件")
    print("=" * 60)
