#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘移动端爬虫 - 绕过 IP 限制
使用 m.liepin.com 行业分类页面获取数据
"""

import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup

# ==================== 配置 ====================

OUTPUT_DIR = Path("/Users/meteor/爬虫实习项目/猎聘/爬虫代码")
LOG_FILE = OUTPUT_DIR / "scraper_mobile.log"

# 移动端 User-Agent
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"

# 行业分类 URL
INDUSTRY_URLS = {
    "能源/化工/环保/矿产开采": "https://m.liepin.com/career/nengyuankuangchanhuanbao/",
    "能源/化工/环保/金属冶炼": "https://m.liepin.com/career/nengyuankuangchanhuanbao/",
    "能源/化工/环保/电力/热力/水务": "https://m.liepin.com/career/nengyuankuangchanhuanbao/",
    "能源/化工/环保/新能源": "https://m.liepin.com/career/nengyuankuangchanhuanbao/",
    "能源/化工/环保/石化/化工": "https://m.liepin.com/career/nengyuankuangchanhuanbao/",
    "政府/非营利/农林牧渔/政府/公共事业": "https://m.liepin.com/career/gongwuyuannonglinmuyuqt/",
    "政府/非营利/农林牧渔/非营利组织": "https://m.liepin.com/career/gongwuyuannonglinmuyuqt/",
    "政府/非营利/农林牧渔/农林牧渔": "https://m.liepin.com/career/gongwuyuannonglinmuyuqt/",
}

class MobileScraper:
    """移动端爬虫"""

    def __init__(self):
        self.session = curl_requests.Session()
        self.all_jobs = []
        self.seen_links = set()
        self.headers = {
            "User-Agent": MOBILE_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://m.liepin.com/",
        }
        self._load_existing_data()

    def _load_existing_data(self):
        """加载已有数据"""
        existing_file = OUTPUT_DIR / "猎聘_整合数据.xlsx"
        if existing_file.exists():
            try:
                df = pd.read_excel(existing_file)
                if '岗位链接' in df.columns:
                    self.seen_links = set(df['岗位链接'].dropna().tolist())
                    print(f"📂 加载已有数据: {len(self.seen_links)} 条链接")
            except Exception as e:
                print(f"加载已有数据失败: {e}")

    def _log(self, msg: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _random_delay(self, min_sec: float = 2.0, max_sec: float = 5.0):
        """随机延迟"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def _extract_jobs_from_html(self, html: str, category: str) -> List[Dict]:
        """从移动端 HTML 提取职位数据"""
        jobs = []
        soup = BeautifulSoup(html, "html.parser")

        # 查找职位容器
        job_wrap = soup.find("section", class_="so-job-job-wrap")
        if not job_wrap:
            return jobs

        # 查找职位信息容器
        info_container = job_wrap.find("div", class_="recruitment-info-container")
        if not info_container:
            return jobs

        # 查找所有职位链接
        job_links = info_container.find_all("a", href=True)

        for link in job_links:
            try:
                job = {}
                href = link.get("href", "")

                # 过滤非职位链接
                if "/job/" not in href and "/a/" not in href:
                    continue

                # 构造完整链接
                if not href.startswith("http"):
                    href = "https://m.liepin.com" + href
                job['岗位链接'] = href

                # 去重
                if job['岗位链接'] in self.seen_links:
                    continue

                # 从链接文本提取信息
                link_text = link.get_text(strip=True)

                # 解析职位标题（通常是第一行）
                title_div = link.find("div", class_="job-title")
                if title_div:
                    span = title_div.find("span", class_="ellipsis")
                    if span:
                        job['岗位名称'] = span.get_text(strip=True)

                # 解析薪资
                salary_elem = link.find("small")
                if salary_elem:
                    job['薪资范围'] = salary_elem.get_text(strip=True)

                # 解析公司
                company_div = link.find("div", class_="job-card-company")
                if company_div:
                    company_text = company_div.get_text(strip=True)
                    company_text = re.sub(r'(战略融资|天使轮|A轮|B轮|C轮|D轮|已上市|不需要融资).*', '', company_text)
                    job['公司名称'] = company_text.strip()

                # 解析标签（城市、经验、学历）
                labels_div = link.find("div", class_="job-card-labels")
                if labels_div:
                    labels_text = labels_div.get_text(strip=True)
                    # 尝试解析：城市+经验+学历
                    # 例如：衢江区4年以上本科
                    parts = re.findall(r'[一-龥]+|\d+年', labels_text)
                    if len(parts) >= 3:
                        job['城市'] = parts[0]
                        job['经验要求'] = parts[1]
                        job['学历要求'] = parts[2]
                    elif len(parts) == 2:
                        job['城市'] = parts[0]
                        job['经验要求'] = parts[1]
                    elif len(parts) == 1:
                        job['城市'] = parts[0]

                # 基础信息
                job['招聘平台'] = "猎聘"
                job['岗位类型\n一级'] = category.split("/")[0] if "/" in category else category
                job['岗位类型\n二级'] = category.split("/")[-1] if "/" in category else ""
                job['岗位类型\n企业/公务员/事业单位/军队文职'] = "企业"

                # 省份映射
                province_map = {
                    "北京": "北京", "上海": "上海", "广州": "广东", "深圳": "广东",
                    "成都": "四川", "杭州": "浙江", "武汉": "湖北", "西安": "陕西",
                    "重庆": "重庆", "南京": "江苏", "苏州": "江苏", "天津": "天津",
                    "长沙": "湖南", "郑州": "河南", "东莞": "广东", "青岛": "山东",
                    "合肥": "安徽", "佛山": "广东", "宁波": "浙江", "昆明": "云南",
                    "沈阳": "辽宁", "大连": "辽宁", "福州": "福建", "厦门": "福建",
                    "济南": "山东", "长春": "吉林", "哈尔滨": "黑龙江", "石家庄": "河北",
                }
                city = job.get('城市', '')
                job['所在省份'] = province_map.get(city, city)

                # 生成序号
                job['序号'] = len(self.all_jobs) + len(self.seen_links) + 1

                # 添加到结果
                jobs.append(job)
                self.seen_links.add(job['岗位链接'])

            except Exception as e:
                continue

        return jobs

    def scrape_industry_page(self, url: str, category: str, max_pages: int = 10) -> List[Dict]:
        """爬取行业页面"""
        all_jobs = []

        for page in range(1, max_pages + 1):
            page_url = f"{url}pn{page}/" if page > 1 else url
            self._log(f"📄 访问: {page_url}")

            try:
                resp = self.session.get(page_url, headers=self.headers, impersonate="safari17_0", timeout=15)

                if resp.status_code != 200:
                    self._log(f"  ✗ 状态码: {resp.status_code}")
                    break

                # 提取职位
                jobs = self._extract_jobs_from_html(resp.text, category)
                self._log(f"  ✓ 提取 {len(jobs)} 条职位")

                if not jobs:
                    self._log(f"  ⚠️ 第 {page} 页无数据，停止")
                    break

                all_jobs.extend(jobs)
                self._random_delay(3, 6)

            except Exception as e:
                self._log(f"  ✗ 请求失败: {e}")
                break

        return all_jobs

    def run(self):
        """运行爬虫"""
        self._log("=" * 60)
        self._log("🚀 启动猎聘移动端爬虫")
        self._log("=" * 60)

        total_new = 0

        for category, url in INDUSTRY_URLS.items():
            self._log(f"\n🏭 开始: {category}")

            jobs = self.scrape_industry_page(url, category, max_pages=50)
            self.all_jobs.extend(jobs)
            total_new += len(jobs)

            self._log(f"  ✓ 本行业新增: {len(jobs)} 条")
            self._log(f"  ✓ 总计: {len(self.all_jobs)} 条新增")

            # 保存中间结果
            if self.all_jobs:
                self._save_results()

            # 行业间冷却
            self._log(f"⏸️ 行业切换，冷却 30 秒...")
            time.sleep(30)

        self._log(f"\n{'=' * 60}")
        self._log(f"✅ 完成！总计新增: {total_new} 条")
        self._log(f"{'=' * 60}")

        return self.all_jobs

    def _save_results(self):
        """保存结果"""
        if not self.all_jobs:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"猎聘_移动端_{timestamp}.xlsx"

        # 转换为 DataFrame
        df = pd.DataFrame(self.all_jobs)

        # 保存
        df.to_excel(output_file, index=False, engine='openpyxl')
        self._log(f"✅ 已保存: {output_file}")

if __name__ == "__main__":
    scraper = MobileScraper()
    scraper.run()
