#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘搜索爬虫 - 代理IP版本
策略：
1. 付费住宅代理IP轮换（每次请求换IP）
2. Camoufox 反检测浏览器
3. 智能限速 + 退避策略
4. 移动端 + PC端双通道
"""

import asyncio
import hashlib
import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from bs4 import BeautifulSoup
from camoufox.async_api import AsyncCamoufox
from curl_cffi import requests as curl_requests


# ==================== 代理配置 ====================

class ProxyProvider:
    """代理IP提供者 - 支持多种代理服务"""

    def __init__(self, provider_type: str = "kuaidaili", **kwargs):
        """
        provider_type: 代理服务类型
            - "kuaidaili": 快代理（推荐国内）
            - "zhima": 芝麻代理
            - "pinzan": 品赞代理
            - "brightdata": Bright Data（国际）
            - "oxylabs": Oxylabs
            - "custom": 自定义API
            - "list": 本地代理列表
        """
        self.provider_type = provider_type
        self.config = kwargs
        self.session = curl_requests.Session()
        self.proxy_cache = []
        self.failed_proxies = set()

    def get_proxy(self) -> Optional[str]:
        """获取一个代理IP"""
        if self.provider_type == "kuaidaili":
            return self._get_kuaidaili_proxy()
        elif self.provider_type == "zhima":
            return self._get_zhima_proxy()
        elif self.provider_type == "brightdata":
            return self._get_brightdata_proxy()
        elif self.provider_type == "custom":
            return self._get_custom_proxy()
        elif self.provider_type == "list":
            return self._get_list_proxy()
        else:
            return None

    def _get_kuaidaili_proxy(self) -> Optional[str]:
        """快代理 - API获取单个IP"""
        # 快代理私密代理API
        # 注册地址: https://www.kuaidaili.com/
        api_url = self.config.get("api_url", "")
        if not api_url:
            # 使用示例格式（需替换为实际API）
            api_key = self.config.get("api_key", "")
            api_url = f"https://dps.kuaidaili.com/getdps/?serial=你的订单号&num=1&pt=1&format=json&sep=1"

        try:
            resp = self.session.get(api_url, timeout=10)
            data = resp.json()
            # 快代理返回格式
            if data.get("code") == 0:
                ip = data["data"]["proxy_list"][0]
                return f"http://{ip}"
        except Exception as e:
            print(f"  获取快代理失败: {e}")
        return None

    def _get_zhima_proxy(self) -> Optional[str]:
        """芝麻代理 - API获取"""
        # 芝麻代理API
        api_url = self.config.get("api_url", "")
        if not api_url:
            api_key = self.config.get("api_key", "")
            api_url = f"http://webapi.http.zhimacangku.com/getip?ne=1&cd=1&pro=1&cityid=0&dy=1&auth={api_key}&oxy=1&ep=1&ut=1&lb=\\r\\n&sb=\\r\\n&mr=1&gession="

        try:
            resp = self.session.get(api_url, timeout=10)
            # 芝麻代理返回格式: IP:PORT
            ip_port = resp.text.strip()
            if ":" in ip_port:
                return f"http://{ip_port}"
        except Exception as e:
            print(f"  获取芝麻代理失败: {e}")
        return None

    def _get_brightdata_proxy(self) -> Optional[str]:
        """Bright Data - 住宅代理"""
        # Bright Data 住宅代理
        proxy_host = self.config.get("proxy_host", "brd.superproxy.io")
        proxy_port = self.config.get("proxy_port", 33335)
        username = self.config.get("username", "")
        password = self.config.get("password", "")
        session_id = random.randint(1, 100000)  # 每次请求换session

        proxy_url = f"http://{username}-session{session_id}:{password}@{proxy_host}:{proxy_port}"
        return proxy_url

    def _get_custom_proxy(self) -> Optional[str]:
        """自定义代理API"""
        api_url = self.config.get("api_url", "")
        if not api_url:
            return None

        try:
            resp = self.session.get(api_url, timeout=10)
            data = resp.json()
            # 自适应不同返回格式
            if "ip" in data and "port" in data:
                return f"http://{data['ip']}:{data['port']}"
            elif "proxy" in data:
                return data["proxy"]
            elif "data" in data:
                return f"http://{data['data']}"
        except Exception as e:
            print(f"  获取自定义代理失败: {e}")
        return None

    def _get_list_proxy(self) -> Optional[str]:
        """从本地列表获取代理"""
        proxy_list = self.config.get("proxy_list", [])
        if not proxy_list:
            return None

        # 过滤掉已失败的
        available = [p for p in proxy_list if p not in self.failed_proxies]
        if not available:
            self.failed_proxies.clear()  # 重置
            available = proxy_list

        proxy = random.choice(available)
        return proxy

    def report_failure(self, proxy: str):
        """报告代理失败"""
        self.failed_proxies.add(proxy)


# ==================== 限速器 ====================

class AdaptiveRateLimiter:
    """自适应限速器"""

    def __init__(self, base_delay=3.0, max_delay=120.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_delay = base_delay
        self.consecutive_fails = 0

    def on_success(self):
        self.consecutive_fails = 0
        self.current_delay = max(self.base_delay, self.current_delay * 0.8)

    def on_failure(self):
        self.consecutive_fails += 1
        self.current_delay = min(
            self.max_delay,
            self.base_delay * (2 ** self.consecutive_fails)
        )

    def wait(self):
        jitter = random.uniform(0.7, 1.3)
        delay = self.current_delay * jitter
        print(f"  ⏳ 等待 {delay:.1f}秒...")
        time.sleep(delay)


# ==================== 搜索爬虫 ====================

class LiepinSearchScraper:
    """猎聘搜索爬虫 - 代理IP版"""

    # 城市代码
    CITY_CODES = {
        "北京": "010", "上海": "020", "广州": "050020", "深圳": "050090",
        "杭州": "070020", "南京": "060020", "成都": "280020", "武汉": "170020",
        "长沙": "190020", "郑州": "150020", "济南": "080020", "青岛": "080080",
        "西安": "270020", "合肥": "120020", "福州": "110020", "厦门": "110030",
        "沈阳": "230020", "大连": "230030", "哈尔滨": "220020", "长春": "240020",
        "昆明": "250020", "贵阳": "290020", "兰州": "310020", "南宁": "200020",
        "太原": "040020", "南昌": "160020", "海口": "210020",
        "重庆": "040010", "天津": "030010",
    }

    # 搜索关键词
    KEYWORDS = [
        "矿产开采", "采矿", "矿山", "矿业", "地质", "勘探",
        "金属冶炼", "钢铁", "冶金", "炼钢", "炼铁",
        "电力", "热力", "水务", "供电", "发电", "电网",
        "新能源", "光伏", "风电", "太阳能", "储能", "锂电池",
        "石化", "化工", "石油化工", "煤化工",
        "环保", "环境工程", "环境监测", "污染治理",
        "农业", "林业", "牧业", "渔业",
    ]

    # 省份映射
    CITY_TO_PROVINCE = {
        '北京': '北京市', '上海': '上海市', '天津': '天津市', '重庆': '重庆市',
        '广州': '广东省', '深圳': '广东省', '杭州': '浙江省', '南京': '江苏省',
        '成都': '四川省', '武汉': '湖北省', '长沙': '湖南省', '郑州': '河南省',
        '济南': '山东省', '青岛': '山东省', '西安': '陕西省', '合肥': '安徽省',
        '福州': '福建省', '厦门': '福建省', '沈阳': '辽宁省', '大连': '辽宁省',
        '昆明': '云南省', '贵阳': '贵州省', '兰州': '甘肃省', '南宁': '广西壮族自治区',
        '太原': '山西省', '南昌': '江西省', '海口': '海南省',
        '哈尔滨': '黑龙江省', '长春': '吉林省',
    }

    def __init__(self, proxy_provider: ProxyProvider = None, use_mobile: bool = True):
        self.proxy_provider = proxy_provider
        self.use_mobile = use_mobile
        self.rate_limiter = AdaptiveRateLimiter()
        self.all_jobs = []
        self.seen_md5s = set()
        self.output_file = Path("/Users/meteor/爬虫实习项目/猎聘/爬虫代码") / \
            f"猎聘_搜索爬虫_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    def get_province(self, city: str) -> str:
        for key, value in self.CITY_TO_PROVINCE.items():
            if key in city:
                return value
        return ""

    def calculate_md5(self, job: dict) -> str:
        key = f"{job.get('公司名称', '')}_{job.get('岗位名称', '')}_{job.get('薪资范围', '')}"
        return hashlib.md5(key.encode()).hexdigest()

    def extract_job_from_html(self, html: str, category: str = "", keyword: str = "") -> List[dict]:
        """从HTML提取职位信息"""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        cards = soup.find_all('div', class_=lambda x: x and 'job-card-pc-container' in str(x))

        for card in cards:
            try:
                job = {}

                # 职位链接
                link = card.find('a', attrs={'data-jobid': True})
                if link:
                    job['岗位链接'] = link.get('href', '')
                    if job['岗位链接'] and not job['岗位链接'].startswith('http'):
                        job['岗位链接'] = 'https://www.liepin.com' + job['岗位链接']

                # 职位名称
                title = card.find('div', class_='ellipsis-1', title=True)
                if title:
                    job['岗位名称'] = title.get('title', '').strip()

                # 薪资
                salary = card.find('span', class_='job-salary')
                if salary:
                    job['薪资范围'] = salary.string.strip() if salary.string else ''

                # 经验/学历
                labels = card.find_all('span', class_='labels-tag')
                if len(labels) >= 1:
                    job['经验要求'] = labels[0].string.strip() if labels[0].string else ''
                if len(labels) >= 2:
                    job['学历要求'] = labels[1].string.strip() if labels[1].string else ''

                # 公司
                company = card.find('span', class_='company-name')
                if company:
                    job['公司名称'] = company.string.strip() if company.string else ''

                # 公司规模
                tags_box = card.find('div', class_='company-tags-box')
                if tags_box:
                    tags = tags_box.find_all('span')
                    if len(tags) >= 2:
                        job['公司规模'] = tags[1].string.strip() if tags[1].string else ''

                # 地点
                loc_div = card.find('div', class_='job-dq-box')
                if loc_div:
                    loc_text = loc_div.get_text(strip=True)
                    m = re.search(r'【([^】]+)】', loc_text)
                    if m:
                        job['城市'] = m.group(1)
                        job['所在省份'] = self.get_province(job['城市'])

                # 固定字段
                job['招聘平台'] = '猎聘'
                job['岗位类型\n一级'] = category
                job['岗位类型\n企业/公务员/事业单位/军队文职'] = '企业'

                if job.get('岗位名称'):
                    md5 = self.calculate_md5(job)
                    if md5 not in self.seen_md5s:
                        self.seen_md5s.add(md5)
                        jobs.append(job)

            except Exception as e:
                print(f"  ❌ 解析卡片失败: {e}")

        return jobs

    def save_to_excel(self):
        if not self.all_jobs:
            return

        df = pd.DataFrame(self.all_jobs)
        columns = [
            '序号', '招聘平台', '岗位类型\n一级', '岗位类型\n二级', '岗位名称',
            '岗位类型\n企业/公务员/事业单位/军队文职', '公司名称', '公司规模',
            '所在省份', '城市', '详细地址', '学历要求', '经验要求', '薪资范围',
            '福利标签', '工作内容', '任职要求', '岗位链接', '发布时间',
        ]
        for col in columns:
            if col not in df.columns:
                df[col] = ''

        # 添加序号
        df['序号'] = range(1, len(df) + 1)
        df = df[columns]
        df.to_excel(self.output_file, index=False, engine='openpyxl')
        print(f"✅ 已保存 {len(df)} 条记录")

    def search_with_camoufox(self, keyword: str, city_code: str = None,
                              category: str = "", max_pages: int = 3) -> List[dict]:
        """使用Camoufox搜索（带代理）"""
        all_jobs = []

        async def _search():
            proxy_url = self.proxy_provider.get_proxy() if self.proxy_provider else None

            camoufox_config = {
                "headless": True,
            }
            if proxy_url:
                camoufox_config["proxy"] = {"server": proxy_url}

            async with AsyncCamoufox(**camoufox_config) as browser:
                page = await browser.new_page()

                for page_num in range(1, max_pages + 1):
                    # 构建搜索URL
                    if city_code:
                        url = f"https://www.liepin.com/zhaopin/?key={keyword}&dq={city_code}"
                    else:
                        url = f"https://www.liepin.com/zhaopin/?key={keyword}"

                    if page_num > 1:
                        url += f"&pn={page_num - 1}"

                    try:
                        print(f"  🔍 搜索: {keyword} (第{page_num}页)")

                        # 模拟真实用户行为
                        await page.goto(url, timeout=30000)
                        await asyncio.sleep(random.uniform(2, 5))

                        # 隐藏弹窗
                        await page.evaluate("""
                            document.querySelectorAll('.ant-modal-wrap, .modal-mask, .login-modal')
                                .forEach(m => m.style.display = 'none');
                        """)

                        content = await page.content()
                        jobs = self.extract_job_from_html(content, category, keyword)

                        if not jobs:
                            print(f"  ⚠️ 第{page_num}页无结果，可能被限制")
                            self.rate_limiter.on_failure()
                            break

                        all_jobs.extend(jobs)
                        print(f"  ✓ 获取 {len(jobs)} 条")
                        self.rate_limiter.on_success()

                        self.rate_limiter.wait()

                    except Exception as e:
                        print(f"  ❌ 搜索失败: {e}")
                        self.rate_limiter.on_failure()

                        # 如果代理失败，尝试换一个
                        if self.proxy_provider:
                            new_proxy = self.proxy_provider.get_proxy()
                            if new_proxy:
                                print(f"  🔄 切换代理: {new_proxy[:30]}...")

        asyncio.run(_search())
        return all_jobs

    def search_with_curl(self, keyword: str, city_code: str = None,
                          category: str = "", max_pages: int = 3) -> List[dict]:
        """使用curl_cffi搜索（更轻量）"""
        all_jobs = []

        # 获取代理
        proxy_url = self.proxy_provider.get_proxy() if self.proxy_provider else None

        session = curl_requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.liepin.com/",
        })

        if proxy_url:
            session.proxies = {"http": proxy_url, "https": proxy_url}

        # 先访问首页获取cookies
        try:
            session.get("https://www.liepin.com/", impersonate="chrome120")
            time.sleep(1)
        except:
            pass

        for page_num in range(1, max_pages + 1):
            if city_code:
                url = f"https://www.liepin.com/zhaopin/?key={keyword}&dq={city_code}"
            else:
                url = f"https://www.liepin.com/zhaopin/?key={keyword}"

            if page_num > 1:
                url += f"&pn={page_num - 1}"

            try:
                print(f"  🔍 搜索: {keyword} (第{page_num}页)")
                resp = session.get(url, impersonate="chrome120")

                if resp.status_code != 200:
                    print(f"  ⚠️ 状态码: {resp.status_code}")
                    self.rate_limiter.on_failure()
                    continue

                jobs = self.extract_job_from_html(resp.text, category, keyword)

                if not jobs:
                    print(f"  ⚠️ 无结果")
                    self.rate_limiter.on_failure()
                    break

                all_jobs.extend(jobs)
                print(f"  ✓ 获取 {len(jobs)} 条")
                self.rate_limiter.on_success()

                self.rate_limiter.wait()

            except Exception as e:
                print(f"  ❌ 请求失败: {e}")
                self.rate_limiter.on_failure()

        return all_jobs

    def run(self, method: str = "camoufox"):
        """运行搜索爬虫"""
        print("🚀 启动猎聘搜索爬虫（代理IP版）")
        print(f"📁 输出: {self.output_file}")
        print(f"🔧 方法: {method}")
        print(f"🔑 关键词: {len(self.KEYWORDS)} 个")
        print(f"🏙️ 城市: {len(self.CITY_CODES)} 个")
        print("=" * 60)

        # 阶段1: 关键词搜索（不限城市）
        print("\n📌 阶段1: 关键词搜索")
        for keyword in self.KEYWORDS:
            print(f"\n🔍 关键词: {keyword}")
            if method == "camoufox":
                jobs = self.search_with_camoufox(keyword, category="能源/化工/环保", max_pages=3)
            else:
                jobs = self.search_with_curl(keyword, category="能源/化工/环保", max_pages=3)

            self.all_jobs.extend(jobs)
            self.save_to_excel()

            # 关键词间等待
            wait = random.uniform(10, 30)
            print(f"  ⏳ 切换关键词等待 {wait:.0f}秒")
            time.sleep(wait)

        # 阶段2: 城市+关键词交叉搜索
        print("\n📌 阶段2: 城市+关键词交叉搜索")
        # 只选部分城市和关键词做交叉
        top_cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉"]
        top_keywords = ["电力", "新能源", "化工", "环保"]

        for city in top_cities:
            city_code = self.CITY_CODES.get(city)
            if not city_code:
                continue

            for keyword in top_keywords:
                print(f"\n🏙️ {city} + {keyword}")
                if method == "camoufox":
                    jobs = self.search_with_camoufox(keyword, city_code, f"{city}/能源", max_pages=2)
                else:
                    jobs = self.search_with_curl(keyword, city_code, f"{city}/能源", max_pages=2)

                self.all_jobs.extend(jobs)
                self.save_to_excel()

                wait = random.uniform(15, 45)
                print(f"  ⏳ 等待 {wait:.0f}秒")
                time.sleep(wait)

        self.save_to_excel()
        print(f"\n✅ 搜索完成！共 {len(self.all_jobs)} 条记录")


# ==================== 主程序 ====================

def main():
    """主函数 - 配置代理后运行"""

    # ============================================
    # 方式1: 快代理（推荐国内）
    # ============================================
    proxy_provider = ProxyProvider(
        provider_type="kuaidaili",
        api_key="你的API密钥",
        api_url="https://dps.kuaidaili.com/getdps/?serial=你的订单号&num=1&pt=1&format=json&sep=1"
    )

    # ============================================
    # 方式2: Bright Data（国际）
    # ============================================
    # proxy_provider = ProxyProvider(
    #     provider_type="brightdata",
    #     username="你的用户名",
    #     password="你的密码",
    #     proxy_host="brd.superproxy.io",
    #     proxy_port=33335,
    # )

    # ============================================
    # 方式3: 本地代理列表
    # ============================================
    # proxy_provider = ProxyProvider(
    #     provider_type="list",
    #     proxy_list=[
    #         "http://ip1:port1",
    #         "http://ip2:port2",
    #         "http://ip3:port3",
    #     ]
    # )

    # ============================================
    # 方式4: 无代理（仅测试）
    # ============================================
    # proxy_provider = None

    scraper = LiepinSearchScraper(
        proxy_provider=proxy_provider,
        use_mobile=True,
    )
    scraper.run(method="camoufox")


if __name__ == "__main__":
    main()
