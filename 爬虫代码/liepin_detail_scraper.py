#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘详情页爬虫 - 提取完整职位信息
使用Schema.org结构化数据提取工作内容、任职要求、福利标签等
"""

import re
import json
import time
from typing import Dict, List, Optional
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup


class LiepinDetailScraper:
    """猎聘详情页爬虫"""

    def __init__(self):
        self.session = curl_requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        self.initialized = False

    def init_session(self):
        """初始化会话，访问首页获取必要的Cookie"""
        if self.initialized:
            return

        print("初始化会话...")
        try:
            # 访问首页获取cookie
            resp = self.session.get("https://www.liepin.com/", impersonate="chrome120")
            print(f"  首页状态码: {resp.status_code}")
            print(f"  获取的cookies: {list(self.session.cookies.keys())}")
            self.initialized = True
            time.sleep(1)
        except Exception as e:
            print(f"  初始化失败: {e}")

    def extract_detail(self, url: str) -> Optional[Dict]:
        """
        从详情页URL提取完整职位信息

        Args:
            url: 详情页URL，如 https://www.liepin.com/a/76135965.shtml

        Returns:
            包含职位信息的字典，失败返回None
        """
        self.init_session()

        try:
            # 访问详情页
            resp = self.session.get(url, impersonate="chrome120")

            if resp.status_code != 200:
                print(f"  请求失败，状态码: {resp.status_code}")
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')

            # 提取Schema.org数据（主要来源）
            schema_data = self._extract_schema_data(soup)

            # 提取$CONFIG数据
            config_data = self._extract_config_data(soup)

            # 提取页面元素数据
            page_data = self._extract_page_elements(soup)

            # 合并数据
            result = self._merge_data(schema_data, config_data, page_data, url)

            return result

        except Exception as e:
            print(f"  提取详情失败: {e}")
            return None

    def _extract_schema_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """提取Schema.org JobPosting数据"""
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string and 'JobPosting' in script.string:
                try:
                    # 清理JSON字符串
                    json_str = script.string.strip()
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    json_str = re.sub(r'\s+', ' ', json_str)

                    data = json.loads(json_str)
                    if data.get('@type') == 'JobPosting':
                        return data
                except Exception as e:
                    # 尝试正则提取关键字段
                    return self._extract_schema_by_regex(json_str)
        return None

    def _extract_schema_by_regex(self, json_str: str) -> Optional[Dict]:
        """使用正则表达式从Schema.org数据中提取字段"""
        result = {}

        # 提取标题
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', json_str)
        if title_match:
            result['title'] = title_match.group(1)

        # 提取描述
        desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', json_str)
        if desc_match:
            result['description'] = desc_match.group(1)

        # 提取发布日期
        date_match = re.search(r'"datePosted"\s*:\s*"([^"]+)"', json_str)
        if date_match:
            result['datePosted'] = date_match.group(1)

        # 提取有效期
        valid_match = re.search(r'"validThrough"\s*:\s*"([^"]+)"', json_str)
        if valid_match:
            result['validThrough'] = valid_match.group(1)

        # 提取公司名称
        org_match = re.search(r'"hiringOrganization"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', json_str)
        if org_match:
            result['company'] = org_match.group(1)

        # 提取地址
        street_match = re.search(r'"streetAddress"\s*:\s*"([^"]+)"', json_str)
        if street_match:
            result['address'] = street_match.group(1)

        # 提取经验要求
        exp_match = re.search(r'"experienceRequirements"\s*:\s*"([^"]+)"', json_str)
        if exp_match:
            result['experience'] = exp_match.group(1)

        # 提取学历要求
        edu_match = re.search(r'"educationRequirements"\s*:\s*"([^"]+)"', json_str)
        if edu_match:
            result['education'] = edu_match.group(1)

        return result if result else None

    def _extract_config_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """提取$CONFIG数据"""
        for script in soup.find_all('script'):
            if script.string and '$CONFIG' in script.string:
                try:
                    match = re.search(r'var\s+\$CONFIG\s*=\s*({.*?});', script.string, re.DOTALL)
                    if match:
                        return json.loads(match.group(1))
                except:
                    pass
        return None

    def _extract_page_elements(self, soup: BeautifulSoup) -> Dict:
        """提取页面元素数据"""
        result = {}

        # 提取福利标签
        labels_elem = soup.find('span', class_='labels')
        if labels_elem:
            result['welfare_tags'] = labels_elem.get_text(strip=True)

        # 提取更新时间
        time_elem = soup.find('span', class_='time-factor-wrap')
        if time_elem:
            time_text = time_elem.get_text(strip=True)
            # 提取日期
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', time_text)
            if date_match:
                result['update_time'] = date_match.group(1)

        # 提取职位介绍
        job_intro = soup.find('div', class_='job-intro-container')
        if job_intro:
            result['job_intro'] = job_intro.get_text(strip=True)

        return result

    def _merge_data(self, schema_data: Optional[Dict], config_data: Optional[Dict],
                    page_data: Dict, url: str) -> Dict:
        """合并所有数据源"""
        result = {
            'url': url,
            'title': '',
            'company': '',
            'job_id': '',
            'job_kind': '',
            'description': '',
            'work_content': '',
            'requirements': '',
            'welfare_tags': '',
            'address': '',
            'city': '',
            'province': '',
            'experience': '',
            'education': '',
            'publish_time': '',
            'valid_through': '',
            'industry': '',
        }

        # 从Schema.org数据提取
        if schema_data:
            result['title'] = schema_data.get('title', '')
            result['description'] = schema_data.get('description', '')
            result['publish_time'] = schema_data.get('datePosted', '')
            result['valid_through'] = schema_data.get('validThrough', '')
            result['experience'] = schema_data.get('experienceRequirements', '')
            result['education'] = schema_data.get('educationRequirements', '')
            result['industry'] = schema_data.get('industry', '')

            # 提取公司名称
            org = schema_data.get('hiringOrganization', {})
            if isinstance(org, dict):
                result['company'] = org.get('name', '')

            # 提取地址
            location = schema_data.get('jobLocation', {})
            if isinstance(location, dict):
                address = location.get('address', {})
                if isinstance(address, dict):
                    result['address'] = address.get('streetAddress', '')
                    result['city'] = address.get('addressLocality', '')
                    result['province'] = address.get('addressRegion', '')

            # 提取job_id
            identifier = schema_data.get('identifier', {})
            if isinstance(identifier, dict):
                result['job_id'] = str(identifier.get('value', ''))

        # 从$CONFIG数据补充
        if config_data:
            if not result['job_id']:
                result['job_id'] = str(config_data.get('jobId', ''))
            result['job_kind'] = config_data.get('jobKind', '')
            if not result['company']:
                result['company'] = config_data.get('compName', '')

        # 从页面元素补充
        if page_data.get('welfare_tags'):
            result['welfare_tags'] = page_data['welfare_tags']

        if page_data.get('update_time'):
            result['publish_time'] = page_data['update_time']

        # 分离工作内容和任职要求
        if result['description']:
            result['work_content'], result['requirements'] = self._split_description(
                result['description']
            )

        return result

    def _split_description(self, description: str) -> tuple:
        """分离工作内容和任职要求"""
        work_content = ''
        requirements = ''

        # 尝试按常见分隔符分割
        separators = ['任职要求', '任职资格', '岗位要求', '职位要求', '岗位职责', '工作职责']
        for sep in separators:
            if sep in description:
                parts = description.split(sep, 1)
                work_content = parts[0].strip()
                if len(parts) > 1:
                    requirements = sep + parts[1].strip()
                break

        # 如果没有找到分隔符，尝试按行分割
        if not work_content and not requirements:
            lines = description.split('\n')
            mid = len(lines) // 2
            work_content = '\n'.join(lines[:mid])
            requirements = '\n'.join(lines[mid:])

        return work_content, requirements

    def extract_batch(self, urls: List[str], delay: float = 2.0) -> List[Dict]:
        """
        批量提取多个详情页

        Args:
            urls: URL列表
            delay: 请求间隔（秒）

        Returns:
            职位信息列表
        """
        results = []

        for i, url in enumerate(urls):
            print(f"提取第 {i+1}/{len(urls)} 个: {url}")

            result = self.extract_detail(url)
            if result:
                results.append(result)
                print(f"  [成功] {result['title'][:30]}...")
            else:
                print(f"  [失败]")

            # 限速
            if i < len(urls) - 1:
                time.sleep(delay)

        return results


def test_single_url():
    """测试单个URL"""
    print("=" * 60)
    print("测试单个URL提取")
    print("=" * 60)

    scraper = LiepinDetailScraper()
    url = "https://www.liepin.com/a/76135965.shtml"

    result = scraper.extract_detail(url)

    if result:
        print("\n提取成功！")
        print(f"职位名称: {result['title']}")
        print(f"公司名称: {result['company']}")
        print(f"工作内容: {result['work_content'][:200]}...")
        print(f"任职要求: {result['requirements'][:200]}...")
        print(f"福利标签: {result['welfare_tags']}")
        print(f"详细地址: {result['address']}")
        print(f"城市: {result['city']}")
        print(f"省份: {result['province']}")
        print(f"经验要求: {result['experience']}")
        print(f"学历要求: {result['education']}")
        print(f"发布时间: {result['publish_time']}")
        print(f"有效期: {result['valid_through']}")
        print(f"行业: {result['industry']}")
        print(f"职位ID: {result['job_id']}")
        print(f"职位类型: {result['job_kind']}")
    else:
        print("\n提取失败")


def test_batch_urls():
    """测试批量URL"""
    print("=" * 60)
    print("测试批量URL提取")
    print("=" * 60)

    # 测试URL列表
    test_urls = [
        "https://www.liepin.com/a/76135965.shtml",
        # 可以添加更多URL进行测试
    ]

    scraper = LiepinDetailScraper()
    results = scraper.extract_batch(test_urls, delay=3.0)

    print(f"\n成功提取 {len(results)} 个职位")

    # 保存结果
    output_file = '/Users/meteor/爬虫实习项目/猎聘/爬虫代码/liepin_detail_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"结果已保存到: {output_file}")


if __name__ == "__main__":
    test_single_url()
    print("\n")
    test_batch_urls()
