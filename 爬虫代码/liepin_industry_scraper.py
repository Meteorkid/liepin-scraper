"""猎聘行业分类爬虫 - 从行业分类页面直接爬取职位数据
目标：爬取能源/化工/环保 + 政府/非营利/农林牧渔的所有职位
"""

from camoufox.sync_api import Camoufox
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re
import hashlib


# 省份映射：城市名 -> 省份
CITY_TO_PROVINCE = {
    "北京": "北京市", "上海": "上海市", "天津": "天津市", "重庆": "重庆市",
    "广州": "广东省", "深圳": "广东省", "东莞": "广东省", "佛山": "广东省",
    "珠海": "广东省", "惠州": "广东省", "中山": "广东省", "汕头": "广东省",
    "杭州": "浙江省", "宁波": "浙江省", "温州": "浙江省", "嘉兴": "浙江省",
    "湖州": "浙江省", "绍兴": "浙江省", "金华": "浙江省", "台州": "浙江省",
    "南京": "江苏省", "苏州": "江苏省", "无锡": "江苏省", "常州": "江苏省",
    "徐州": "江苏省", "南通": "江苏省", "扬州": "江苏省", "镇江": "江苏省",
    "成都": "四川省", "绵阳": "四川省", "德阳": "四川省",
    "武汉": "湖北省", "宜昌": "湖北省", "襄阳": "湖北省",
    "长沙": "湖南省", "株洲": "湖南省", "湘潭": "湖南省",
    "郑州": "河南省", "洛阳": "河南省", "开封": "河南省",
    "济南": "山东省", "青岛": "山东省", "烟台": "山东省", "潍坊": "山东省",
    "西安": "陕西省", "咸阳": "陕西省",
    "合肥": "安徽省", "芜湖": "安徽省", "蚌埠": "安徽省",
    "福州": "福建省", "厦门": "福建省", "泉州": "福建省",
    "南昌": "江西省", "赣州": "江西省",
    "太原": "山西省", "大同": "山西省",
    "沈阳": "辽宁省", "大连": "辽宁省", "鞍山": "辽宁省",
    "长春": "吉林省",
    "哈尔滨": "黑龙江省",
    "昆明": "云南省", "大理": "云南省",
    "贵阳": "贵州省", "遵义": "贵州省",
    "兰州": "甘肃省",
    "西宁": "青海省",
    "海口": "海南省",
    "南宁": "广西壮族自治区", "柳州": "广西壮族自治区",
    "呼和浩特": "内蒙古自治区", "包头": "内蒙古自治区",
    "拉萨": "西藏自治区",
    "乌鲁木齐": "新疆维吾尔自治区", "银川": "宁夏回族自治区",
}


def get_province(city_text: str) -> str:
    """从城市文本中提取省份"""
    if not city_text:
        return ""
    for city, province in CITY_TO_PROVINCE.items():
        if city in city_text:
            return province
    return ""


class LiepinIndustryScraper:
    """猎聘行业分类爬虫"""

    # 行业分类页面URL
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
        self.seen_keys = set()  # 去重
        self.sequence = 1

    def extract_jobs_from_page(self, html: str, category: str, sub_industry: str) -> list:
        """从HTML页面提取职位信息"""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        # 查找工作卡片
        job_cards = soup.find_all('div', class_=lambda x: x and 'job-card-pc-container' in str(x))

        for card in job_cards:
            job = self._parse_job_card(card)
            if job:
                # 去重：职位名+公司名
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

        # 职位名称
        title_elem = card.find('div', class_='ellipsis-1', title=True)
        if title_elem:
            job['title'] = title_elem.get('title', '').strip()

        # 职位链接
        link_elem = card.find('a', href=True, target='_blank')
        if link_elem:
            job['link'] = link_elem.get('href', '')
            if job['link'] and not job['link'].startswith('http'):
                job['link'] = f'https://www.liepin.com{job["link"]}'

        # 薪资
        salary_elem = card.find('span', class_='_40108E8PWS')
        if salary_elem:
            job['salary'] = salary_elem.get_text(strip=True)

        # 经验和学历
        exp_edu_spans = card.find_all('span', class_='_40108hJbMl')
        if len(exp_edu_spans) >= 2:
            job['experience'] = exp_edu_spans[0].get_text(strip=True)
            job['education'] = exp_edu_spans[1].get_text(strip=True)

        # 公司名称
        company_elem = card.find('span', class_='_40108K6Y1c')
        if company_elem:
            job['company'] = company_elem.get_text(strip=True)

        # 地点
        location_div = card.find('div', class_='_40108__9nJ')
        if location_div:
            text = location_div.get_text()
            loc_match = re.search(r'【([^】]+)】', text)
            if loc_match:
                job['location'] = loc_match.group(1)

        # 行业标签
        industry_elem = card.find('div', class_='_40108hFeAm')
        if industry_elem:
            job['industry_tag'] = industry_elem.get_text(strip=True)

        # 公司规模
        scale_elem = card.find('div', class_='_40108cpKKS')
        if scale_elem:
            job['company_scale'] = scale_elem.get_text(strip=True)

        return job if job.get('title') else None

    @staticmethod
    def _close_modal(page_obj):
        """关闭猎聘弹窗"""
        try:
            # 关闭ant-modal弹窗
            page_obj.evaluate("""() => {
                // 关闭所有ant-modal弹窗
                document.querySelectorAll('.ant-modal-wrap').forEach(modal => {
                    modal.style.display = 'none';
                });
                // 点击关闭按钮
                document.querySelectorAll('.ant-modal-close').forEach(btn => btn.click());
                // 移除遮罩层
                document.querySelectorAll('.ant-modal-mask').forEach(mask => {
                    mask.style.display = 'none';
                });
            }""")
        except:
            pass

    def scrape_industry_page(self, browser, url: str, category: str, sub_industry: str, max_pages: int = 50):
        """爬取行业分类页面的所有职位"""
        all_jobs = []

        # 先访问第一页获取总页数
        print(f"  访问行业页面: {url}")
        try:
            page_obj = browser.new_page()
            page_obj.goto(url, wait_until='networkidle', timeout=60000)
            page_obj.wait_for_timeout(5000)

            # 关闭弹窗
            self._close_modal(page_obj)
            page_obj.wait_for_timeout(1000)

            html = page_obj.content()
            soup = BeautifulSoup(html, 'html.parser')

            # 猎聘行业分类页面实际有10页数据（pn0到pn9）
            # 分页链接只显示前5页，但实际可以访问更多
            total_pages = 10  # 直接设置为10页
            total_pages = min(total_pages, max_pages)

            print(f"  总页数: {total_pages}")

            # 爬取第一页
            jobs = self.extract_jobs_from_page(html, category, sub_industry)
            print(f"  第1页: 找到 {len(jobs)} 个职位")
            all_jobs.extend(jobs)

            page_obj.close()

            # 爬取剩余页
            # 分页URL格式：pn1=第2页, pn2=第3页, pn3=第4页...
            for page_num in range(2, total_pages + 1):
                page_url = f"{url.rstrip('/')}/pn{page_num - 1}/"

                print(f"  第{page_num}页...", end=' ')

                try:
                    page_obj = browser.new_page()
                    page_obj.goto(page_url, wait_until='networkidle', timeout=60000)
                    page_obj.wait_for_timeout(5000)

                    # 关闭弹窗
                    self._close_modal(page_obj)
                    page_obj.wait_for_timeout(1000)

                    html = page_obj.content()
                    jobs = self.extract_jobs_from_page(html, category, sub_industry)

                    print(f"找到 {len(jobs)} 个职位")
                    all_jobs.extend(jobs)

                    page_obj.close()

                    if len(jobs) == 0:
                        break

                    time.sleep(15)  # 增加请求间隔到15秒

                except Exception as e:
                    print(f"失败: {e}")
                    break

        except Exception as e:
            print(f"  访问失败: {e}")

        return all_jobs

    def scrape_all(self):
        """爬取所有行业"""
        print("=" * 60)
        print("开始爬取猎聘行业分类职位数据")
        print("=" * 60)

        start_time = datetime.now()

        with Camoufox(headless=True) as browser:
            for category, sub_industries in self.INDUSTRY_URLS.items():
                print(f"\n{'='*60}")
                print(f"行业大类: {category}")
                print(f"{'='*60}")

                for sub_industry, url in sub_industries.items():
                    print(f"\n--- 细分行业: {sub_industry} ---")
                    jobs = self.scrape_industry_page(browser, url, category, sub_industry, max_pages=100)
                    self.jobs.extend(jobs)

                    # 显示进度
                    elapsed = (datetime.now() - start_time).seconds
                    print(f"  [进度] 已爬取 {len(self.jobs)} 个职位，耗时 {elapsed//60}分{elapsed%60}秒")

                    time.sleep(2)

        print(f"\n{'='*60}")
        print(f"爬取完成!")
        print(f"  总职位数: {len(self.jobs)}")
        print(f"  去重后: {len(self.seen_keys)}")
        print(f"  总耗时: {(datetime.now() - start_time).seconds // 60} 分钟")
        print(f"{'='*60}")

    def save_to_excel(self, filename: str = None):
        """保存到Excel - 严格匹配师融百工-数据模板格式"""
        if not self.jobs:
            print("没有数据可保存")
            return

        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'/Users/meteor/爬虫实习项目/猎聘/猎聘_行业分类_{timestamp}.xlsx'

        # 按照模板格式整理数据
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

        # 设置列顺序
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
    scraper = LiepinIndustryScraper()
    scraper.scrape_all()
    scraper.save_to_excel()


if __name__ == '__main__':
    main()
