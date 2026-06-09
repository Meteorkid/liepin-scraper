#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘详情页方案验证测试
测试不同场景下的详情页提取效果
"""

import json
import time
from typing import Dict, List
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup
import re


def test_different_jobs():
    """测试1: 不同职位ID的详情页"""
    print("=" * 60)
    print("测试1: 不同职位ID的详情页")
    print("=" * 60)

    # 不同职位ID（需要替换为实际有效的ID）
    test_urls = [
        "https://www.liepin.com/a/76135965.shtml",
        # 可以添加更多测试URL
    ]

    session = curl_requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    # 初始化
    session.get("https://www.liepin.com/", impersonate="chrome120")
    time.sleep(1)

    results = []
    for url in test_urls:
        print(f"\n--- 测试: {url} ---")
        try:
            resp = session.get(url, impersonate="chrome120")
            print(f"  状态码: {resp.status_code}")

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')

                # 提取Schema.org数据
                for script in soup.find_all('script', type='application/ld+json'):
                    if script.string and 'JobPosting' in script.string:
                        try:
                            json_str = script.string.strip()
                            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                            data = json.loads(json_str)

                            if data.get('@type') == 'JobPosting':
                                result = {
                                    'url': url,
                                    'title': data.get('title', ''),
                                    'company': data.get('hiringOrganization', {}).get('name', ''),
                                    'address': data.get('jobLocation', {}).get('address', {}).get('streetAddress', ''),
                                    'experience': data.get('experienceRequirements', ''),
                                    'education': data.get('educationRequirements', ''),
                                    'publish_time': data.get('datePosted', ''),
                                    'has_description': bool(data.get('description')),
                                }
                                results.append(result)
                                print(f"  [成功] {result['title'][:30]}...")
                                break
                        except Exception as e:
                            print(f"  [错误] JSON解析失败: {e}")
                            break

            time.sleep(2)  # 限速

        except Exception as e:
            print(f"  [错误] {e}")

    print(f"\n成功提取 {len(results)} 个职位详情")
    return results


def test_concurrent_requests():
    """测试2: 并发请求测试"""
    print("\n" + "=" * 60)
    print("测试2: 并发请求测试")
    print("=" * 60)

    test_url = "https://www.liepin.com/a/76135965.shtml"

    session = curl_requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    # 初始化
    session.get("https://www.liepin.com/", impersonate="chrome120")
    time.sleep(1)

    # 测试不同间隔
    intervals = [0.5, 1, 2, 3]
    results = []

    for interval in intervals:
        print(f"\n--- 间隔: {interval}秒 ---")
        success_count = 0
        total_requests = 5

        for i in range(total_requests):
            try:
                resp = session.get(test_url, impersonate="chrome120")
                if resp.status_code == 200 and len(resp.text) > 10000:
                    success_count += 1
                time.sleep(interval)
            except:
                pass

        success_rate = success_count / total_requests * 100
        results.append({
            'interval': interval,
            'success_count': success_count,
            'success_rate': success_rate
        })
        print(f"  成功: {success_count}/{total_requests} ({success_rate:.1f}%)")

    print("\n结果汇总:")
    for r in results:
        print(f"  间隔 {r['interval']}秒: 成功率 {r['success_rate']:.1f}%")

    return results


def test_with_proxy():
    """测试3: 代理测试（可选）"""
    print("\n" + "=" * 60)
    print("测试3: 代理测试（需要配置代理）")
    print("=" * 60)

    # 如果有代理，可以在这里配置
    # proxies = {
    #     "http": "http://proxy:port",
    #     "https": "http://proxy:port",
    # }

    print("  [跳过] 未配置代理")
    print("  如需使用代理，请修改此函数中的proxies配置")


def test_error_handling():
    """测试4: 错误处理测试"""
    print("\n" + "=" * 60)
    print("测试4: 错误处理测试")
    print("=" * 60)

    session = curl_requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })

    # 初始化
    session.get("https://www.liepin.com/", impersonate="chrome120")
    time.sleep(1)

    # 测试无效URL
    invalid_urls = [
        "https://www.liepin.com/a/99999999.shtml",  # 不存在的职位
        "https://www.liepin.com/a/invalid.shtml",    # 无效格式
    ]

    for url in invalid_urls:
        print(f"\n--- 测试无效URL: {url} ---")
        try:
            resp = session.get(url, impersonate="chrome120")
            print(f"  状态码: {resp.status_code}")
            print(f"  页面大小: {len(resp.text)} bytes")

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # 检查是否是404页面
                title = soup.title.string if soup.title else ''
                print(f"  页面标题: {title[:50] if title else 'None'}")

                # 检查是否有职位数据
                has_job_data = bool(soup.find('script', type='application/ld+json'))
                print(f"  包含职位数据: {has_job_data}")

        except Exception as e:
            print(f"  [错误] {e}")


def test_field_extraction_accuracy():
    """测试5: 字段提取准确性测试"""
    print("\n" + "=" * 60)
    print("测试5: 字段提取准确性测试")
    print("=" * 60)

    test_url = "https://www.liepin.com/a/76135965.shtml"

    session = curl_requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    # 初始化
    session.get("https://www.liepin.com/", impersonate="chrome120")
    time.sleep(1)

    print(f"测试URL: {test_url}")
    resp = session.get(test_url, impersonate="chrome120")

    if resp.status_code != 200:
        print(f"请求失败，状态码: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, 'html.parser')

    # 提取所有字段
    fields = {
        'title': False,
        'company': False,
        'description': False,
        'work_content': False,
        'requirements': False,
        'welfare_tags': False,
        'address': False,
        'city': False,
        'province': False,
        'experience': False,
        'education': False,
        'publish_time': False,
        'valid_through': False,
        'industry': False,
        'job_id': False,
    }

    # 提取Schema.org数据
    for script in soup.find_all('script', type='application/ld+json'):
        if script.string and 'JobPosting' in script.string:
            try:
                json_str = script.string.strip()
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                data = json.loads(json_str)

                if data.get('@type') == 'JobPosting':
                    fields['title'] = bool(data.get('title'))
                    fields['company'] = bool(data.get('hiringOrganization', {}).get('name'))
                    fields['description'] = bool(data.get('description'))
                    fields['address'] = bool(data.get('jobLocation', {}).get('address', {}).get('streetAddress'))
                    fields['city'] = bool(data.get('jobLocation', {}).get('address', {}).get('addressLocality'))
                    fields['province'] = bool(data.get('jobLocation', {}).get('address', {}).get('addressRegion'))
                    fields['experience'] = bool(data.get('experienceRequirements'))
                    fields['education'] = bool(data.get('educationRequirements'))
                    fields['publish_time'] = bool(data.get('datePosted'))
                    fields['valid_through'] = bool(data.get('validThrough'))
                    fields['industry'] = bool(data.get('industry'))

                    # 分离工作内容和任职要求
                    if data.get('description'):
                        desc = data['description']
                        separators = ['任职要求', '任职资格', '岗位要求']
                        for sep in separators:
                            if sep in desc:
                                fields['work_content'] = True
                                fields['requirements'] = True
                                break
                        if not fields['work_content']:
                            fields['work_content'] = True

                    # 提取job_id
                    identifier = data.get('identifier', {})
                    if isinstance(identifier, dict):
                        fields['job_id'] = bool(identifier.get('value'))

                    break
            except:
                pass

    # 提取福利标签
    labels_elem = soup.find('span', class_='labels')
    fields['welfare_tags'] = labels_elem is not None

    # 输出结果
    print("\n字段提取结果:")
    print("-" * 40)
    extracted_count = 0
    total_count = len(fields)

    for field, extracted in fields.items():
        status = "✅" if extracted else "❌"
        print(f"  {status} {field}")
        if extracted:
            extracted_count += 1

    print("-" * 40)
    print(f"提取率: {extracted_count}/{total_count} ({extracted_count/total_count*100:.1f}%)")


if __name__ == "__main__":
    print("猎聘详情页方案验证测试")
    print("=" * 60)

    # 运行所有测试
    test_different_jobs()
    test_concurrent_requests()
    test_error_handling()
    test_field_extraction_accuracy()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
