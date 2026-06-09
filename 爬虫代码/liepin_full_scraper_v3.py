#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘完整爬虫 V3 - 列表页 + 详情页
策略：
1. 从列表页获取职位链接和基本信息
2. 从详情页获取工作内容、任职要求、福利标签等
3. 智能限速避免被封
4. 增量保存数据
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


# ==================== 配置 ====================

OUTPUT_DIR = Path("/Users/meteor/爬虫实习项目/猎聘/爬虫代码")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 省份映射（从v2复制）
CITY_TO_PROVINCE = {
    '北京': '北京市', '上海': '上海市', '天津': '天津市', '重庆': '重庆市',
    '广州': '广东省', '深圳': '广东省', '杭州': '浙江省', '南京': '江苏省',
    '成都': '四川省', '武汉': '湖北省', '长沙': '湖南省', '郑州': '河南省',
    '济南': '山东省', '青岛': '山东省', '西安': '陕西省', '合肥': '安徽省',
    '福州': '福建省', '厦门': '福建省', '南昌': '江西省', '太原': '山西省',
    '沈阳': '辽宁省', '大连': '辽宁省', '长春': '吉林省', '哈尔滨': '黑龙江省',
    '昆明': '云南省', '贵阳': '贵州省', '兰州': '甘肃省', '海口': '海南省',
    '南宁': '广西壮族自治区', '呼和浩特': '内蒙古自治区',
    '乌鲁木齐': '新疆维吾尔自治区', '银川': '宁夏回族自治区',
}


def get_province(city: str) -> str:
    """从城市名获取省份"""
    if not city:
        return ''
    for key, value in CITY_TO_PROVINCE.items():
        if key in city or city in key:
            return value
    return ''


class SmartRateLimiter:
    """智能限速器"""

    def __init__(self, min_delay=5.0, max_delay=120.0, backoff_factor=2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.current_delay = min_delay
        self.block_count = 0
        self.success_count = 0

    def report_blocked(self):
        """报告被封锁"""
        self.block_count += 1
        self.success_count = 0
        self.current_delay = min(
            self.min_delay * (self.backoff_factor ** self.block_count),
            self.max_delay
        )
        print(f"⚠️  被限制！当前延时: {self.current_delay:.1f}秒")

    def report_success(self):
        """报告成功"""
        self.success_count += 1
        if self.success_count >= 3:
            self.block_count = max(0, self.block_count - 1)
            self.current_delay = max(
                self.min_delay,
                self.current_delay / self.backoff_factor
            )

    def wait(self):
        """等待"""
        jitter = random.uniform(0.8, 1.2)
        delay = self.current_delay * jitter
        print(f"⏳ 等待 {delay:.1f}秒...")
        time.sleep(delay)


class LiepinDetailExtractor:
    """详情页数据提取器（使用curl_cffi）"""

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
        """初始化会话"""
        if self.initialized:
            return
        try:
            self.session.get("https://www.liepin.com/", impersonate="chrome120")
            self.initialized = True
            time.sleep(1)
        except Exception as e:
            print(f"  初始化详情页会话失败: {e}")

    def extract(self, url: str) -> Optional[Dict]:
        """从详情页提取数据"""
        self.init_session()

        try:
            resp = self.session.get(url, impersonate="chrome120")
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')
            result = {}

            # 提取Schema.org数据
            for script in soup.find_all('script', type='application/ld+json'):
                if script.string and 'JobPosting' in script.string:
                    try:
                        json_str = script.string.strip()
                        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                        json_str = re.sub(r'\s+', ' ', json_str)
                        data = json.loads(json_str)

                        if data.get('@type') == 'JobPosting':
                            result['description'] = data.get('description', '')
                            result['publish_time'] = data.get('datePosted', '')
                            result['valid_through'] = data.get('validThrough', '')
                            result['experience'] = data.get('experienceRequirements', '')
                            result['education'] = data.get('educationRequirements', '')

                            # 提取地址
                            location = data.get('jobLocation', {})
                            if isinstance(location, dict):
                                address = location.get('address', {})
                                if isinstance(address, dict):
                                    result['address'] = address.get('streetAddress', '')
                                    result['city'] = address.get('addressLocality', '')
                                    result['province'] = address.get('addressRegion', '')

                            # 提取职位类型
                            result['employment_type'] = data.get('employmentType', '')
                            result['industry'] = data.get('industry', '')
                            break
                    except:
                        pass

            # 提取福利标签
            labels_elem = soup.find('span', class_='labels')
            if labels_elem:
                result['welfare_tags'] = labels_elem.get_text(strip=True)

            # 分离工作内容和任职要求
            if result.get('description'):
                desc = result['description']
                separators = ['任职要求', '任职资格', '岗位要求', '职位要求']
                for sep in separators:
                    if sep in desc:
                        parts = desc.split(sep, 1)
                        result['work_content'] = parts[0].strip()
                        if len(parts) > 1:
                            result['requirements'] = sep + parts[1].strip()
                        break

                if not result.get('work_content'):
                    result['work_content'] = desc

            return result

        except Exception as e:
            print(f"  提取详情失败: {e}")
            return None


class LiepinFullScraperV3:
    """猎聘完整爬虫V3 - 列表页 + 详情页"""

    def __init__(self, fetch_detail: bool = True):
        self.all_jobs = []
        self.seen_md5s = set()
        self.rate_limiter = SmartRateLimiter()
        self.detail_extractor = LiepinDetailExtractor() if fetch_detail else None
        self.fetch_detail = fetch_detail
        self.output_file = OUTPUT_DIR / f"猎聘_完整爬虫_V3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # 关键词列表
        self.keywords = [
            # 能源/矿产开采
            "矿产开采", "采矿", "矿山", "矿业", "地质", "勘探",
            # 金属冶炼
            "金属冶炼", "钢铁", "冶金", "炼钢", "炼铁",
            # 电力/热力/水务
            "电力", "热力", "水务", "供电", "发电", "电网",
            # 新能源
            "新能源", "光伏", "风电", "太阳能", "储能", "锂电池",
            # 石化/化工
            "石化", "化工", "石油化工", "煤化工",
            # 环保
            "环保", "环境工程", "环境监测", "污染治理",
            # 政府/公共事业
            "政府", "公务员", "事业单位", "公共事业",
            # 农林牧渔
            "农业", "林业", "牧业", "渔业",
        ]

    def calculate_md5(self, job_data: dict) -> str:
        """计算MD5用于去重"""
        key_str = f"{job_data.get('公司名称', '')}_{job_data.get('岗位名称', '')}_{job_data.get('薪资范围', '')}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def save_to_excel(self, jobs: List[dict]):
        """保存到Excel"""
        if not jobs:
            print("⚠️  没有数据可保存")
            return

        df = pd.DataFrame(jobs)

        template_columns = [
            '序号', '招聘平台', '岗位类型\n一级', '岗位类型\n二级', '岗位名称',
            '岗位类型\n企业/公务员/事业单位/军队文职', '公司名称', '公司规模',
            '所在省份', '城市', '详细地址', '学历要求', '经验要求', '薪资范围',
            '福利标签', '工作内容', '任职要求', '岗位链接', '发布时间',
            '投递起始时间', '投递截止时间', '证书要求', '备注（技能要求）'
        ]

        for col in template_columns:
            if col not in df.columns:
                df[col] = ''

        df = df[template_columns]
        df.to_excel(self.output_file, index=False, engine='openpyxl')
        print(f"✅ 已保存到 {self.output_file}，共 {len(df)} 条记录")

    def extract_job_from_card(self, card, category: str, sub_industry: str) -> Optional[dict]:
        """从卡片中提取职位信息"""
        try:
            job = {}

            # 职位链接和ID
            link_elem = card.find('a', attrs={'data-jobid': True})
            if link_elem:
                job['岗位链接'] = link_elem.get('href', '')
                job['job_id'] = link_elem.get('data-jobid', '')

            # 职位名称
            title_elem = card.find('div', class_='ellipsis-1', title=True)
            if title_elem:
                job['岗位名称'] = title_elem.get('title', '').strip()

            # 薪资
            salary_elem = card.find('span', class_='job-salary')
            if salary_elem:
                job['薪资范围'] = salary_elem.string.strip() if salary_elem.string else ''

            # 经验和学历要求
            labels = card.find_all('span', class_='labels-tag')
            if len(labels) >= 1:
                job['经验要求'] = labels[0].string.strip() if labels[0].string else ''
            if len(labels) >= 2:
                job['学历要求'] = labels[1].string.strip() if labels[1].string else ''

            # 公司名称
            company_elem = card.find('span', class_='company-name')
            if company_elem:
                job['公司名称'] = company_elem.string.strip() if company_elem.string else ''

            # 公司标签
            tags_box = card.find('div', class_='company-tags-box')
            if tags_box:
                tags = tags_box.find_all('span')
                if len(tags) >= 2:
                    job['公司规模'] = tags[1].string.strip() if len(tags) > 1 and tags[1].string else ''

            # 地点
            location_div = card.find('div', class_='job-dq-box')
            if location_div:
                location_text = location_div.get_text(strip=True)
                loc_match = re.search(r'【([^】]+)】', location_text)
                if loc_match:
                    job['城市'] = loc_match.group(1)
                    job['所在省份'] = get_province(job['城市'])

            # 固定字段
            job['招聘平台'] = '猎聘'
            job['岗位类型\n一级'] = category.split('/')[0] if '/' in category else category
            job['岗位类型\n二级'] = sub_industry if sub_industry else ''
            job['岗位类型\n企业/公务员/事业单位/军队文职'] = '企业'

            return job

        except Exception as e:
            print(f"❌ 提取职位信息失败: {e}")
            return None

    def fetch_job_detail(self, job: dict) -> dict:
        """获取职位详情"""
        if not self.fetch_detail or not self.detail_extractor:
            return job

        url = job.get('岗位链接', '')
        if not url:
            return job

        print(f"  📋 获取详情: {url}")
        detail = self.detail_extractor.extract(url)

        if detail:
            # 更新职位信息
            if detail.get('work_content'):
                job['工作内容'] = detail['work_content']
            if detail.get('requirements'):
                job['任职要求'] = detail['requirements']
            if detail.get('welfare_tags'):
                job['福利标签'] = detail['welfare_tags']
            if detail.get('address'):
                job['详细地址'] = detail['address']
            if detail.get('city') and not job.get('城市'):
                job['城市'] = detail['city']
            if detail.get('province') and not job.get('所在省份'):
                job['所在省份'] = detail['province']
            if detail.get('experience') and not job.get('经验要求'):
                job['经验要求'] = detail['experience']
            if detail.get('education') and not job.get('学历要求'):
                job['学历要求'] = detail['education']
            if detail.get('publish_time'):
                job['发布时间'] = detail['publish_time']

            # 添加备注
            notes = []
            if detail.get('industry'):
                notes.append(f"行业: {detail['industry']}")
            if detail.get('valid_through'):
                notes.append(f"有效期至: {detail['valid_through']}")
            if notes:
                job['备注（技能要求）'] = '; '.join(notes)

            print(f"    ✅ 成功提取详情")
        else:
            print(f"    ❌ 提取详情失败")

        return job

    async def scrape_page(self, page, url: str, category: str, sub_industry: str) -> List[dict]:
        """爬取单个页面"""
        jobs = []

        try:
            print(f"📄 访问: {url}")
            await page.goto(url, timeout=30000)
            await asyncio.sleep(3)

            # 隐藏弹窗
            await page.evaluate("""
                document.querySelectorAll('.ant-modal-wrap').forEach(m => m.style.display = 'none');
                document.querySelectorAll('.modal-mask').forEach(m => m.style.display = 'none');
            """)

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            cards = soup.find_all('div', class_=lambda x: x and 'job-card-pc-container' in str(x))

            if not cards:
                print(f"⚠️  未找到工作卡片，可能被限制")
                self.rate_limiter.report_blocked()
                return jobs

            for card in cards:
                job = self.extract_job_from_card(card, category, sub_industry)
                if job and job.get('岗位名称'):
                    md5 = self.calculate_md5(job)
                    if md5 not in self.seen_md5s:
                        self.seen_md5s.add(md5)

                        # 获取详情页数据
                        if self.fetch_detail:
                            job = self.fetch_job_detail(job)
                            time.sleep(1)  # 详情页限速

                        jobs.append(job)

            self.rate_limiter.report_success()
            print(f"✓ 提取 {len(jobs)} 条职位")

        except Exception as e:
            print(f"❌ 爬取页面失败: {e}")
            self.rate_limiter.report_blocked()

        return jobs

    async def scrape_keyword(self, browser, keyword: str, category: str, sub_industry: str, max_pages: int = 10):
        """爬取关键词搜索结果"""
        page = await browser.new_page()
        all_jobs = []

        try:
            for page_num in range(1, max_pages + 1):
                if page_num == 1:
                    search_url = f"https://www.liepin.com/zhaopin/?key={keyword}"
                else:
                    search_url = f"https://www.liepin.com/zhaopin/?key={keyword}&pn={page_num - 1}"

                print(f"\n{'='*60}")
                print(f"🔍 关键词: {keyword}, 第 {page_num}/{max_pages} 页")
                print(f"{'='*60}")

                jobs = await self.scrape_page(page, search_url, category, sub_industry)

                if not jobs:
                    print(f"⚠️  第 {page_num} 页无数据，停止爬取此关键词")
                    break

                all_jobs.extend(jobs)
                self.all_jobs.extend(jobs)

                # 定期保存
                if len(self.all_jobs) % 50 < 40:
                    self.save_to_excel(self.all_jobs)

                self.rate_limiter.wait()

        finally:
            await page.close()

        return all_jobs

    async def run(self):
        """运行爬虫"""
        print("🚀 启动猎聘完整爬虫V3（列表页 + 详情页）")
        print(f"📁 输出文件: {self.output_file}")
        print(f"📊 关键词数量: {len(self.keywords)}")
        print(f"🔍 是否获取详情: {self.fetch_detail}")
        print("="*60)

        async with AsyncCamoufox(headless=True) as browser:
            # 每个行业选择部分关键词
            industry_keyword_map = {
                "能源/矿产开采": ["矿产开采", "采矿", "矿山", "矿业", "地质", "勘探"],
                "能源/金属冶炼": ["金属冶炼", "钢铁", "冶金", "炼钢", "炼铁"],
                "能源/电力": ["电力", "热力", "水务", "供电", "发电", "电网"],
                "能源/新能源": ["新能源", "光伏", "风电", "太阳能", "储能"],
                "能源/化工": ["石化", "化工", "石油化工", "煤化工"],
                "环保": ["环保", "环境工程", "环境监测", "污染治理"],
                "政府/公共事业": ["政府", "公务员", "事业单位", "公共事业"],
                "农林牧渔": ["农业", "林业", "牧业", "渔业"],
            }

            for industry, keywords in industry_keyword_map.items():
                for keyword in keywords:
                    print(f"\n🔍 爬取关键词: {keyword} (行业: {industry})")
                    await self.scrape_keyword(browser, keyword, industry, keyword, max_pages=5)

                    # 关键词间等待
                    wait_time = random.uniform(10, 30)
                    await asyncio.sleep(wait_time)

            # 最终保存
            self.save_to_excel(self.all_jobs)

            print("\n" + "="*60)
            print(f"✅ 爬取完成！")
            print(f"📊 总数据量: {len(self.all_jobs)} 条")
            print(f"📁 保存到: {self.output_file}")
            print("="*60)


async def main():
    # 可以通过参数控制是否获取详情页
    # fetch_detail=True 会获取详情页，但速度较慢
    # fetch_detail=False 只获取列表页，速度快但字段不全
    scraper = LiepinFullScraperV3(fetch_detail=True)
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
