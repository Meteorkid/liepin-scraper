"""猎聘行业分类爬虫 - 使用OmniCrawl智能限速
自动降级 + 智能限速 + 代理轮换
目标：爬取所有行业分类页面的所有数据
"""

import sys
import os
sys.path.insert(0, '/Users/meteor/github/omnicrawl')

from camoufox.sync_api import Camoufox
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re
import hashlib


# 省份映射
CITY_TO_PROVINCE = {
    "北京": "北京市", "上海": "上海市", "天津": "天津市", "重庆": "重庆市",
    "广州": "广东省", "深圳": "广东省", "东莞": "广东省", "佛山": "广东省",
    "杭州": "浙江省", "宁波": "浙江省", "温州": "浙江省", "嘉兴": "浙江省",
    "南京": "江苏省", "苏州": "江苏省", "无锡": "江苏省", "常州": "江苏省",
    "成都": "四川省", "武汉": "湖北省", "长沙": "湖南省", "郑州": "河南省",
    "济南": "山东省", "青岛": "山东省", "西安": "陕西省", "合肥": "安徽省",
    "福州": "福建省", "厦门": "福建省", "南昌": "江西省", "太原": "山西省",
    "沈阳": "辽宁省", "大连": "辽宁省", "长春": "吉林省", "哈尔滨": "黑龙江省",
    "昆明": "云南省", "贵阳": "贵州省", "兰州": "甘肃省", "海口": "海南省",
    "南宁": "广西壮族自治区", "呼和浩特": "内蒙古自治区",
    "乌鲁木齐": "新疆维吾尔自治区", "银川": "宁夏回族自治区",
}


def get_province(city_text: str) -> str:
    if not city_text:
        return ""
    for city, province in CITY_TO_PROVINCE.items():
        if city in city_text:
            return province
    return ""


class SmartRateLimiter:
    """智能限速器 - 基于被封次数自适应调整延时"""

    def __init__(self, min_delay=3.0, max_delay=60.0, backoff_factor=2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.current_delay = min_delay
        self.block_count = 0
        self.success_count = 0

    def report_blocked(self):
        """报告被封，增加延时"""
        self.block_count += 1
        self.success_count = 0
        self.current_delay = min(
            self.min_delay * (self.backoff_factor ** self.block_count),
            self.max_delay
        )
        print(f"    ⚠️ 被限制 (第{self.block_count}次)，延时增加到 {self.current_delay:.1f}秒")

    def report_success(self):
        """报告成功，逐步恢复延时"""
        self.success_count += 1
        if self.success_count >= 3:  # 连续成功3次后开始恢复
            self.block_count = max(0, self.block_count - 1)
            self.current_delay = max(
                self.min_delay,
                self.current_delay / self.backoff_factor
            )

    def wait(self):
        """等待当前延时"""
        time.sleep(self.current_delay)


class LiepinOmniScraper:
    """猎聘行业分类爬虫 - 使用智能限速"""

    INDUSTRY_URLS = {
        "能源/化工/环保": {
            "矿产开采": "https://www.liepin.com/career/nengyuankuangchanhuanbao/",
            "金属冶炼": "https://www.liepin.com/career/nengyuankuangchanhuanbao/",
            "电力/热力/水务": "https://www.liepin.com/career/nengyuankuangchanhuanbao/",
            "新能源": "https://www.liepin.com/career/nengyuankuangchanhuanbao/",
            "石化/化工": "https://www.liepin.com/career/nengyuankuangchanhuanbao/",
        },
        "政府/非营利/农林牧渔": {
            "政府/公共事业": "https://www.liepin.com/career/gongwuyuannonglinmuyuqt/",
            "非营利组织": "https://www.liepin.com/career/gongwuyuannonglinmuyuqt/",
            "农林牧渔": "https://www.liepin.com/career/nengyuankuangchanhuanbao/",
        },
    }

    def __init__(self):
        self.jobs = []
        self.seen_keys = set()
        self.sequence = 1
        self.rate_limiter = SmartRateLimiter(
            min_delay=5.0,
            max_delay=120.0,
            backoff_factor=2.0
        )

    def extract_jobs_from_html(self, html: str, category: str, sub_industry: str) -> list:
        """从HTML页面提取职位信息"""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        job_cards = soup.find_all('div', class_=lambda x: x and 'job-card-pc-container' in str(x))

        for card in job_cards:
            job = self._parse_job_card(card)
            if job:
                dedup_key = hashlib.md5(f"{job.get('title', '')}_{job.get('company', '')}".encode()).hexdigest()
                if dedup_key in self.seen_keys:
                    continue
                self.seen_keys.add(dedup_key)

                job['industry_category'] = category
                job['sub_industry'] = sub_industry
                job['platform'] = '猎聘'
                job['sequence'] = self.sequence
                self.sequence += 1
                jobs.append(job)

        return jobs

    def _parse_job_card(self, card) -> dict:
        """解析单个工作卡片"""
        job = {}

        title_elem = card.find('div', class_='ellipsis-1', title=True)
        if title_elem:
            job['title'] = title_elem.get('title', '').strip()

        link_elem = card.find('a', href=True, target='_blank')
        if link_elem:
            job['link'] = link_elem.get('href', '')
            if job['link'] and not job['link'].startswith('http'):
                job['link'] = f'https://www.liepin.com{job["link"]}'

        salary_elem = card.find('span', class_='_40108E8PWS')
        if salary_elem:
            job['salary'] = salary_elem.get_text(strip=True)

        exp_edu_spans = card.find_all('span', class_='_40108hJbMl')
        if len(exp_edu_spans) >= 2:
            job['experience'] = exp_edu_spans[0].get_text(strip=True)
            job['education'] = exp_edu_spans[1].get_text(strip=True)

        company_elem = card.find('span', class_='_40108K6Y1c')
        if company_elem:
            job['company'] = company_elem.get_text(strip=True)

        location_div = card.find('div', class_='_40108__9nJ')
        if location_div:
            text = location_div.get_text()
            loc_match = re.search(r'【([^】]+)】', text)
            if loc_match:
                job['location'] = loc_match.group(1)

        industry_elem = card.find('div', class_='_40108hFeAm')
        if industry_elem:
            job['industry_tag'] = industry_elem.get_text(strip=True)

        scale_elem = card.find('div', class_='_40108cpKKS')
        if scale_elem:
            job['company_scale'] = scale_elem.get_text(strip=True)

        return job if job.get('title') else None

    def scrape_all(self):
        """爬取所有行业 - 复用浏览器实例"""
        print("=" * 60)
        print("开始爬取猎聘行业分类职位数据（使用智能限速 + 复用浏览器）")
        print("=" * 60)

        start_time = datetime.now()
        total_pages_scraped = 0

        # 复用同一个Camoufox浏览器实例
        with Camoufox(headless=True) as browser:
            for category, sub_industries in self.INDUSTRY_URLS.items():
                print(f"\n{'='*60}")
                print(f"行业大类: {category}")
                print(f"{'='*60}")

                for sub_industry, base_url in sub_industries.items():
                    print(f"\n--- 细分行业: {sub_industry} ---")

                    # 爬取10页
                    consecutive_blocks = 0
                    for page_num in range(0, 10):
                        if page_num == 0:
                            page_url = base_url
                        else:
                            page_url = f"{base_url.rstrip('/')}/pn{page_num}/"

                        print(f"  第{page_num + 1}页...", end=' ')

                        # 使用智能限速器等待
                        self.rate_limiter.wait()

                        try:
                            page_obj = browser.new_page()
                            page_obj.goto(page_url, wait_until='networkidle', timeout=60000)
                            page_obj.wait_for_timeout(5000)

                            # 关闭弹窗
                            page_obj.evaluate("""() => {
                                document.querySelectorAll('.ant-modal-wrap').forEach(m => m.style.display = 'none');
                                document.querySelectorAll('.ant-modal-mask').forEach(m => m.style.display = 'none');
                            }""")
                            page_obj.wait_for_timeout(1000)

                            html = page_obj.content()
                            page_obj.close()

                            # 提取职位
                            jobs = self.extract_jobs_from_html(html, category, sub_industry)

                            if len(jobs) > 0:
                                self.rate_limiter.report_success()
                                consecutive_blocks = 0
                                print(f"找到 {len(jobs)} 个职位")
                            else:
                                self.rate_limiter.report_blocked()
                                consecutive_blocks += 1
                                print(f"找到 0 个职位")

                            self.jobs.extend(jobs)
                            total_pages_scraped += 1

                        except Exception as e:
                            self.rate_limiter.report_blocked()
                            consecutive_blocks += 1
                            print(f"失败: {e}")

                        # 显示进度
                        elapsed = (datetime.now() - start_time).seconds
                        print(f"    [进度] 总计 {len(self.jobs)} 个职位 | 耗时 {elapsed//60}分{elapsed%60}秒 | 延时 {self.rate_limiter.current_delay:.1f}秒")

                        # 如果连续被限制，增加等待时间
                        if consecutive_blocks >= 3:
                            wait_time = 180  # 等待3分钟
                            print(f"    连续被限制{consecutive_blocks}次，等待{wait_time}秒...")
                            time.sleep(wait_time)
                            consecutive_blocks = 0
                            self.rate_limiter.block_count = 0
                            self.rate_limiter.current_delay = self.rate_limiter.min_delay

                    # 行业间等待（增加到60秒）
                    print(f"\n  行业爬取完成，等待60秒...")
                    time.sleep(60)

        print(f"\n{'='*60}")
        print(f"爬取完成!")
        print(f"  总职位数: {len(self.jobs)}")
        print(f"  去重后: {len(self.seen_keys)}")
        print(f"  总页数: {total_pages_scraped}")
        print(f"  总耗时: {(datetime.now() - start_time).seconds // 60} 分钟")
        print(f"{'='*60}")

    def save_to_excel(self, filename: str = None):
        """保存到Excel"""
        if not self.jobs:
            print("没有数据可保存")
            return

        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'/Users/meteor/爬虫实习项目/猎聘/猎聘_行业分类_智能限速_{timestamp}.xlsx'

        data = []
        for job in self.jobs:
            location = job.get('location', '')
            province = get_province(location)

            data.append({
                '序号': job.get('sequence', ''),
                '招聘平台': '猎聘',
                '岗位类型\n一级': job.get('industry_category', ''),
                '岗位类型\n二级': job.get('sub_industry', ''),
                '岗位名称': job.get('title', ''),
                '岗位类型\n企业/公务员/事业单位/军队文职': '企业职位',
                '公司名称': job.get('company', ''),
                '公司规模': job.get('company_scale', ''),
                '所在省份': province,
                '城市': location,
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
                '备注（技能要求）': f"行业标签: {job.get('industry_tag', '')}",
            })

        df = pd.DataFrame(data)

        columns = [
            '序号', '招聘平台', '岗位类型\n一级', '岗位类型\n二级', '岗位名称',
            '岗位类型\n企业/公务员/事业单位/军队文职', '公司名称', '公司规模',
            '所在省份', '城市', '详细地址', '学历要求', '经验要求', '薪资范围',
            '福利标签', '工作内容', '任职要求', '岗位链接', '发布时间',
            '投递起始时间', '投递截止时间', '证书要求', '备注（技能要求）'
        ]
        df = df[columns]

        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"\n数据已保存到: {filename}")
        print(f"共 {len(df)} 条记录（去重后）")

        return filename


def main():
    """主函数"""
    scraper = LiepinOmniScraper()
    scraper.scrape_all()
    scraper.save_to_excel()


if __name__ == '__main__':
    main()
