"""猎聘职位爬虫 - 使用 OmniCrawl 绕过反爬"""

import asyncio
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import json
import sys
import os

# 添加 OmniCrawl 路径
sys.path.insert(0, '/Users/meteor/github/omnicrawl')
from omnicrawl import OmniClient, FetchMode


class LiepinScraper:
    """猎聘职位爬虫"""

    # 行业分类配置
    INDUSTRIES = {
        "能源/化工/环保": {
            "矿产开采": ["矿产", "开采", "矿业", "矿山", "采矿"],
            "金属冶炼": ["金属", "冶炼", "钢铁", "冶金", "铸造"],
            "电力/热力/水务": ["电力", "热力", "水务", "供电", "发电", "电网"],
            "新能源": ["新能源", "光伏", "风电", "太阳能", "储能", "电池"],
            "石化/化工": ["石化", "化工", "化学", "石油", "炼化"],
        },
        "政府/非营利/农林牧渔": {
            "政府/公共事业": ["政府", "公共事业", "事业单位", "公务员", "市政"],
            "非营利组织": ["非营利", "NGO", "公益", "基金会", "社会团体"],
            "农林牧渔": ["农业", "林业", "牧业", "渔业", "养殖", "种植"],
        },
    }

    def __init__(self):
        self.client = None
        self.results = []
        self.sequence = 1

    async def __aenter__(self):
        self.client = OmniClient(
            mode=FetchMode.AUTO,
            max_retries=3,
            min_delay=2.0,
        )
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.close()

    async def search_jobs(self, keyword: str, page: int = 1) -> List[Dict]:
        """搜索职位"""
        url = f'https://www.liepin.com/zhaopin/?key={keyword}&page={page}'
        jobs = []

        try:
            result = await self.client.get(url)
            if result.status_code == 200 and result.html:
                jobs = self._parse_job_list(result.html)
                print(f"  搜索 '{keyword}' 第{page}页: 找到 {len(jobs)} 个职位")
            else:
                print(f"  搜索 '{keyword}' 失败: 状态码 {result.status_code}")
        except Exception as e:
            print(f"  搜索 '{keyword}' 异常: {e}")

        return jobs

    def _parse_job_list(self, html: str) -> List[Dict]:
        """解析职位列表"""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        # 猎聘职位卡片选择器
        job_cards = soup.find_all(['div', 'li'], class_=lambda x: x and (
            'job-card' in str(x).lower() or
            'job-item' in str(x).lower() or
            'joblist' in str(x).lower()
        ))

        for card in job_cards:
            job = self._parse_job_card(card)
            if job:
                jobs.append(job)

        return jobs

    def _parse_job_card(self, card) -> Optional[Dict]:
        """解析单个职位卡片"""
        try:
            # 职位名称
            title_elem = card.find(['a', 'h3', 'div'], class_=lambda x: x and 'title' in str(x).lower())
            title = title_elem.get_text(strip=True) if title_elem else ""

            # 公司名称
            company_elem = card.find(['a', 'div'], class_=lambda x: x and 'company' in str(x).lower())
            company = company_elem.get_text(strip=True) if company_elem else ""

            # 薪资
            salary_elem = card.find(['span', 'div'], class_=lambda x: x and 'salary' in str(x).lower())
            salary = salary_elem.get_text(strip=True) if salary_elem else ""

            # 地点
            location_elem = card.find(['span', 'div'], class_=lambda x: x and ('location' in str(x).lower() or 'city' in str(x).lower()))
            location = location_elem.get_text(strip=True) if location_elem else ""

            # 职位链接
            link_elem = card.find('a', href=True)
            link = link_elem.get('href', '') if link_elem else ""
            if link and not link.startswith('http'):
                link = f'https://www.liepin.com{link}'

            # 经验要求
            exp_elem = card.find(['span', 'div'], string=lambda text: text and ('经验' in text or '年' in text))
            experience = exp_elem.get_text(strip=True) if exp_elem else ""

            # 学历要求
            edu_elem = card.find(['span', 'div'], string=lambda text: text and ('学历' in text or '本科' in text or '硕士' in text))
            education = edu_elem.get_text(strip=True) if edu_elem else ""

            if title and company:
                return {
                    'title': title,
                    'company': company,
                    'salary': salary,
                    'location': location,
                    'link': link,
                    'experience': experience,
                    'education': education,
                }
        except Exception as e:
            print(f"  解析职位卡片失败: {e}")

        return None

    async def scrape_industry(self, category: str, sub_industry: str, keywords: List[str]) -> List[Dict]:
        """爬取某个细分行业的职位"""
        print(f"\n=== 爬取: {category} > {sub_industry} ===")

        all_jobs = []
        for keyword in keywords:
            # 搜索多个页面
            for page in range(1, 4):  # 每个关键词搜索3页
                jobs = await self.search_jobs(keyword, page)
                if not jobs:
                    break  # 没有更多结果

                for job in jobs:
                    job['industry_category'] = category
                    job['sub_industry'] = sub_industry
                    job['search_keyword'] = keyword
                    job['platform'] = '猎聘'
                    job['sequence'] = self.sequence
                    self.sequence += 1

                all_jobs.extend(jobs)
                await asyncio.sleep(2)  # 避免请求过快

        print(f"  共爬取 {len(all_jobs)} 个职位")
        return all_jobs

    async def scrape_all(self):
        """爬取所有行业"""
        print("开始爬取猎聘职位数据...\n")

        for category, sub_industries in self.INDUSTRIES.items():
            for sub_industry, keywords in sub_industries.items():
                jobs = await self.scrape_industry(category, sub_industry, keywords)
                self.results.extend(jobs)

        print(f"\n=== 爬取完成 ===")
        print(f"总计: {len(self.results)} 个职位")

    def save_to_excel(self, filename: str):
        """保存到 Excel"""
        if not self.results:
            print("没有数据可保存")
            return

        # 按照模板格式整理数据
        data = []
        for job in self.results:
            data.append({
                '序号': job.get('sequence', ''),
                '招聘平台': '猎聘',
                '岗位类型一级': job.get('industry_category', ''),
                '岗位类型二级': job.get('sub_industry', ''),
                '岗位名称': job.get('title', ''),
                '岗位类型': '企业职位',  # 默认企业职位
                '公司名称': job.get('company', ''),
                '公司规模': '',
                '所在省份': '',
                '城市': job.get('location', ''),
                '详细地址': '',
                '学历要求': job.get('education', ''),
                '经验要求': job.get('experience', ''),
                '薪资范围': job.get('salary', ''),
                '福利标签': '',
                '工作内容': '',
                '任职要求': '',
                '岗位链接': job.get('link', ''),
                '发布时间': '',
                '投递起始时间': '',
                '投递截止时间': '',
                '证书要求': '',
                '备注（技能要求）': f"搜索关键词: {job.get('search_keyword', '')}",
            })

        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"\n数据已保存到: {filename}")
        print(f"共 {len(df)} 条记录")


async def main():
    """主函数"""
    async with LiepinScraper() as scraper:
        await scraper.scrape_all()

        # 保存结果
        output_dir = '/Users/meteor/爬虫实习项目/猎聘'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{output_dir}/猎聘_能源化工环保_政府非营利农林_{timestamp}.xlsx'
        scraper.save_to_excel(filename)


if __name__ == '__main__':
    asyncio.run(main())
