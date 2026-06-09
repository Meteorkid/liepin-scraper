#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘 Shadowrocket 代理爬虫
使用 Shadowrocket 订阅的代理节点绕过 IP 限制
"""

import asyncio
import base64
import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from camoufox.async_api import AsyncCamoufox

# ==================== 配置 ====================

OUTPUT_DIR = Path("/Users/meteor/爬虫实习项目/猎聘/爬虫代码")
LOG_FILE = OUTPUT_DIR / "scraper_shadowrocket.log"

# 订阅链接
SUBSCRIPTION_URL = "https://tt.vg/freev2"

# 搜索关键词
SEARCH_KEYWORDS = [
    "矿产开采", "采矿", "矿山", "金属冶炼", "钢铁", "冶金",
    "电力", "热力", "水务", "供电", "发电", "电网",
    "新能源", "光伏", "风电", "储能", "锂电池",
    "化工", "石化", "环保", "环境治理",
    "政府", "公务员", "事业单位",
    "农业", "林业", "牧业", "渔业", "农林",
    "非营利", "公益", "社会组织",
]

# 城市代码
CITY_CODES = {
    "北京": "010", "上海": "020", "广州": "050020", "深圳": "050090",
    "成都": "280020", "杭州": "070020", "武汉": "170020", "西安": "270020",
    "重庆": "040020", "南京": "060020", "苏州": "060050", "天津": "030",
    "长沙": "180020", "郑州": "150020", "东莞": "050040", "青岛": "120020",
    "合肥": "140020", "佛山": "050030", "宁波": "070040", "昆明": "250020",
    "沈阳": "100020", "大连": "100040", "福州": "110020", "厦门": "110040",
    "济南": "130020", "长春": "090020", "哈尔滨": "080020", "石家庄": "160020",
}

# 省份映射
PROVINCE_MAP = {
    "北京": "北京", "上海": "上海", "广州": "广东", "深圳": "广东",
    "成都": "四川", "杭州": "浙江", "武汉": "湖北", "西安": "陕西",
    "重庆": "重庆", "南京": "江苏", "苏州": "江苏", "天津": "天津",
    "长沙": "湖南", "郑州": "河南", "东莞": "广东", "青岛": "山东",
    "合肥": "安徽", "佛山": "广东", "宁波": "浙江", "昆明": "云南",
    "沈阳": "辽宁", "大连": "辽宁", "福州": "福建", "厦门": "福建",
    "济南": "山东", "长春": "吉林", "哈尔滨": "黑龙江", "石家庄": "河北",
}


def parse_ss_url(url: str) -> Optional[Dict]:
    """解析 Shadowsocks URL"""
    try:
        if not url.startswith("ss://"):
            return None

        # 移除 #tag
        url_part = url.split("#")[0]

        # 解析
        parsed = urlparse(url_part)
        if parsed.username:
            # 新格式: ss://base64(method:password)@server:port
            user_info = base64.b64decode(parsed.username + "==").decode()
            method, password = user_info.split(":", 1)
            return {
                "type": "ss",
                "server": parsed.hostname,
                "port": parsed.port,
                "method": method,
                "password": password,
            }
        else:
            # 旧格式: ss://base64(method:password:server:port)
            data = base64.b64decode(url_part[5:] + "==").decode()
            parts = data.split(":")
            if len(parts) >= 4:
                method = parts[0]
                password = parts[1]
                server = parts[2]
                port = int(parts[3])
                return {
                    "type": "ss",
                    "server": server,
                    "port": port,
                    "method": method,
                    "password": password,
                }
    except Exception as e:
        pass
    return None


def fetch_subscription(url: str) -> List[Dict]:
    """获取订阅节点"""
    headers = {
        "User-Agent": "Shadowrocket/2209",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        # 解码 base64
        content = base64.b64decode(resp.text.strip() + "==").decode()

        nodes = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # 只处理 Shadowsocks 节点（可直接用作 SOCKS5 代理）
            if line.startswith("ss://"):
                node = parse_ss_url(line)
                if node:
                    nodes.append(node)

        return nodes

    except Exception as e:
        print(f"获取订阅失败: {e}")
        return []


class ShadowrocketScraper:
    """Shadowrocket 代理爬虫"""

    def __init__(self):
        self.all_jobs = []
        self.seen_links = set()
        self.proxy_nodes = []
        self.current_proxy_idx = 0
        self._load_existing_data()

    def _load_existing_data(self):
        """加载已有数据"""
        existing_file = OUTPUT_DIR / "猎聘_整合数据.xlsx"
        if existing_file.exists():
            try:
                df = pd.read_excel(existing_file)
                if '岗位链接' in df.columns:
                    self.seen_links = set(df['岗位链接'].dropna().tolist())
                    print(f"📂 已加载 {len(self.seen_links)} 条已有链接")
            except Exception as e:
                print(f"加载已有数据失败: {e}")

    def _log(self, msg: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _get_next_proxy(self) -> Optional[str]:
        """获取下一个代理节点（SOCKS5 格式）"""
        if not self.proxy_nodes:
            return None

        node = self.proxy_nodes[self.current_proxy_idx]
        self.current_proxy_idx = (self.current_proxy_idx + 1) % len(self.proxy_nodes)

        # 返回 SOCKS5 代理地址
        return f"socks5://{node['server']}:{node['port']}"

    def _extract_jobs_from_html(self, html: str, source: str) -> List[Dict]:
        """从 HTML 提取职位数据"""
        jobs = []
        soup = BeautifulSoup(html, "html.parser")

        # 搜索页面使用 div.job-card
        cards = soup.find_all("div", class_="job-card")

        for card in cards:
            try:
                job = {}

                # 从 data-tlg-ext 提取 job_id
                ext_attr = card.get("data-tlg-ext", "")
                if ext_attr:
                    try:
                        ext_data = json.loads(ext_attr)
                        job_id = ext_data.get("job_id")
                        if job_id:
                            job['岗位链接'] = f"https://m.liepin.com/job/{job_id}.shtml"
                    except json.JSONDecodeError:
                        continue

                # 去重
                if not job.get('岗位链接') or job['岗位链接'] in self.seen_links:
                    continue

                # 职位标题
                h3 = card.find("h3")
                if h3:
                    spans = h3.find_all("span")
                    for span in spans:
                        if "job-title-label" not in (span.get("class") or []):
                            job['岗位名称'] = span.get_text(strip=True)
                            break
                    small = h3.find("small")
                    if small:
                        job['薪资范围'] = small.get_text(strip=True)

                # 公司
                company_div = card.find("div", class_="job-card-company")
                if company_div:
                    job['公司名称'] = company_div.get_text(strip=True)

                # 标签
                labels_div = card.find("div", class_="job-card-labels")
                if labels_div:
                    labels = labels_div.find_all("label")
                    if len(labels) >= 1:
                        job['城市'] = labels[0].get_text(strip=True)
                    if len(labels) >= 2:
                        job['经验要求'] = labels[1].get_text(strip=True)
                    if len(labels) >= 3:
                        job['学历要求'] = labels[2].get_text(strip=True)

                # 发布者
                publisher_div = card.find("div", class_="job-card-publisher")
                if publisher_div:
                    span = publisher_div.find("span")
                    if span:
                        job['发布者'] = span.get_text(strip=True)

                # 基础信息
                job['招聘平台'] = "猎聘"
                job['岗位类型\n一级'] = source
                job['岗位类型\n二级'] = ""
                job['岗位类型\n企业/公务员/事业单位/军队文职'] = "企业"

                # 省份映射
                city = job.get('城市', '').split('-')[0] if job.get('城市') else ''
                job['所在省份'] = PROVINCE_MAP.get(city, city)

                # 生成序号
                job['序号'] = len(self.all_jobs) + len(self.seen_links) + 1

                jobs.append(job)
                self.seen_links.add(job['岗位链接'])

            except Exception as e:
                continue

        return jobs

    async def scrape_keyword(self, page, keyword: str, city_code: str = "") -> List[Dict]:
        """爬取关键词搜索"""
        if city_code:
            url = f"https://m.liepin.com/zhaopin/?key={keyword}&dq={city_code}"
        else:
            url = f"https://m.liepin.com/zhaopin/?key={keyword}"

        self._log(f"  📄 访问: {url}")

        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(random.randint(3000, 5000))

            content = await page.content()
            jobs = self._extract_jobs_from_html(content, keyword)
            self._log(f"  ✓ 提取 {len(jobs)} 条职位")

            return jobs

        except Exception as e:
            self._log(f"  ✗ 访问失败: {e}")
            return []

    async def run(self):
        """运行爬虫"""
        self._log("=" * 60)
        self._log("🚀 启动猎聘 Shadowrocket 代理爬虫")
        self._log("=" * 60)

        # 获取代理节点
        self._log("\n📥 获取代理节点...")
        self.proxy_nodes = fetch_subscription(SUBSCRIPTION_URL)
        self._log(f"   获取到 {len(self.proxy_nodes)} 个 Shadowsocks 节点")

        if not self.proxy_nodes:
            self._log("❌ 未获取到可用的 Shadowsocks 节点")
            self._log("   尝试使用其他类型的节点...")

            # 尝试获取所有节点
            headers = {"User-Agent": "Shadowrocket/2209"}
            try:
                resp = requests.get(SUBSCRIPTION_URL, headers=headers, timeout=30)
                content = base64.b64decode(resp.text.strip() + "==").decode()
                all_lines = [l.strip() for l in content.strip().split("\n") if l.strip()]
                self._log(f"   总共 {len(all_lines)} 个节点")
                for line in all_lines[:5]:
                    self._log(f"   - {line[:50]}...")
            except Exception as e:
                self._log(f"   获取失败: {e}")

            return

        # 打印节点信息
        for i, node in enumerate(self.proxy_nodes):
            self._log(f"   [{i+1}] {node['server']}:{node['port']} ({node['method']})")

        total_new = 0

        # 尝试每个代理节点
        for proxy_idx in range(len(self.proxy_nodes)):
            proxy_url = self._get_next_proxy()
            self._log(f"\n🔗 使用代理: {proxy_url}")

            try:
                async with AsyncCamoufox(headless=True, proxy={"server": proxy_url}, geoip=True) as browser:
                    page = await browser.new_page()
                    await page.set_viewport_size({"width": 375, "height": 812})

                    # 测试代理是否可用
                    self._log("   测试代理连接...")
                    try:
                        await page.goto("https://m.liepin.com/", timeout=15000)
                        self._log("   ✓ 代理连接成功")
                    except Exception as e:
                        self._log(f"   ✗ 代理连接失败: {e}")
                        continue

                    # 阶段1: 关键词搜索
                    self._log("\n📌 阶段1: 关键词搜索")
                    for keyword in SEARCH_KEYWORDS:
                        self._log(f"\n🔍 关键词: {keyword}")

                        for pg in range(1, 4):  # 每个关键词最多3页
                            if pg > 1:
                                url = f"https://m.liepin.com/zhaopin/?key={keyword}&curPage={pg-1}"
                                self._log(f"  📄 第 {pg} 页")
                                try:
                                    await page.goto(url, timeout=30000)
                                    await page.wait_for_timeout(random.randint(3000, 5000))
                                    content = await page.content()
                                    jobs = self._extract_jobs_from_html(content, keyword)
                                    self._log(f"  ✓ 提取 {len(jobs)} 条职位")
                                except Exception as e:
                                    self._log(f"  ✗ 失败: {e}")
                                    break
                            else:
                                jobs = await self.scrape_keyword(page, keyword)

                            if not jobs:
                                self._log(f"  ⚠️ 无数据，停止此关键词")
                                break

                            self.all_jobs.extend(jobs)
                            total_new += len(jobs)

                            if len(self.all_jobs) % 10 == 0:
                                self._save_results()

                            await asyncio.sleep(random.uniform(3, 6))

                    # 阶段2: 城市+关键词搜索
                    self._log("\n📌 阶段2: 城市+关键词搜索")
                    for city, code in list(CITY_CODES.items())[:5]:  # 前5个城市
                        for keyword in SEARCH_KEYWORDS[:3]:  # 前3个关键词
                            self._log(f"\n🏙️ {city} + {keyword}")

                            jobs = await self.scrape_keyword(page, keyword, code)
                            if jobs:
                                self.all_jobs.extend(jobs)
                                total_new += len(jobs)

                            if len(self.all_jobs) % 10 == 0:
                                self._save_results()

                            await asyncio.sleep(random.uniform(3, 6))

            except Exception as e:
                self._log(f"❌ 代理 {proxy_url} 失败: {e}")
                continue

        # 保存最终结果
        self._save_results()

        self._log(f"\n{'=' * 60}")
        self._log(f"✅ 完成！总计新增: {total_new} 条")
        self._log(f"{'=' * 60}")

        return self.all_jobs

    def _save_results(self):
        """保存结果"""
        if not self.all_jobs:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"猎聘_shadowrocket_{timestamp}.xlsx"

        df = pd.DataFrame(self.all_jobs)
        df.to_excel(output_file, index=False, engine='openpyxl')
        self._log(f"✅ 已保存: {output_file} ({len(self.all_jobs)} 条)")


if __name__ == "__main__":
    scraper = ShadowrocketScraper()
    asyncio.run(scraper.run())
