"""猎聘职位完整爬虫 - 使用 Camoufox 绕过反爬
输出格式严格匹配：师融百工-数据模板.xlsx
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
    # 先尝试直接匹配城市名
    for city, province in CITY_TO_PROVINCE.items():
        if city in city_text:
            return province
    return ""


class LiepinFullScraper:
    """猎聘职位完整爬虫"""

    # 行业分类配置 - 扩展关键词以获取40万条数据
    INDUSTRIES = {
        "能源/化工/环保": {
            "矿产开采": [
                "矿产", "开采", "矿业", "矿山", "采矿", "地质", "勘探",
                "矿物", "矿石", "煤矿", "铁矿", "铜矿", "金矿", "稀土",
                "矿业工程师", "采矿工程师", "矿山安全", "矿产评估"
            ],
            "金属冶炼": [
                "金属", "冶炼", "钢铁", "冶金", "铸造", "锻造", "轧钢",
                "炼钢", "炼铁", "有色金属", "黑色金属", "特种钢", "合金",
                "冶金工程师", "金属材料", "热处理", "表面处理"
            ],
            "电力/热力/水务": [
                "电力", "热力", "水务", "供电", "发电", "电网", "输变电",
                "配电", "变电站", "电力设计", "电力工程", "电气", "继电保护",
                "水务工程师", "供水", "排水", "污水处理", "热力工程师"
            ],
            "新能源": [
                "新能源", "光伏", "风电", "太阳能", "储能", "电池", "锂电",
                "氢能", "燃料电池", "充电桩", "新能源汽车", "动力电池",
                "光伏工程师", "风电工程师", "储能系统", "电池研发", "新能源技术"
            ],
            "石化/化工": [
                "石化", "化工", "化学", "石油", "炼化", "石油化工", "煤化工",
                "精细化工", "高分子", "有机化学", "无机化学", "化学分析",
                "化工工程师", "工艺工程师", "设备工程师", "安全工程师"
            ],
        },
        "政府/非营利/农林牧渔": {
            "政府/公共事业": [
                "政府", "公共事业", "事业单位", "公务员", "市政", "城管",
                "街道办", "社区", "民政", "人社", "卫健", "市场监管",
                "生态环境", "自然资源", "交通运输", "农业农村", "水利"
            ],
            "非营利组织": [
                "非营利", "NGO", "公益", "基金会", "社会团体", "慈善",
                "志愿者", "公益项目", "社会服务", "扶贫", "环保组织",
                "教育公益", "医疗公益", "文化传播", "社区发展"
            ],
            "农林牧渔": [
                "农业", "林业", "牧业", "渔业", "养殖", "种植", "畜牧",
                "水产", "农机", "农技", "种子", "化肥", "农药", "农产品",
                "农业技术", "林业工程师", "畜牧兽医", "水产养殖", "农业机械化"
            ],
        },
    }

    def __init__(self):
        self.jobs = []
        self.seen_keys = set()  # 去重：用职位名+公司名作为唯一键
        self.sequence = 1

    def extract_jobs_from_page(self, html: str, keyword: str, category: str, sub_industry: str, job_type: str) -> list:
        """从HTML页面提取职位信息
        job_type: '企业职位' 或 '猎头职位'
        """
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

                job['search_keyword'] = keyword
                job['industry_category'] = category
                job['sub_industry'] = sub_industry
                job['platform'] = '猎聘'
                job['job_type'] = job_type
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

        # 地点 - 在 _40108__9nJ div 中的【】之间
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

    def scrape_keyword(self, browser, keyword: str, category: str, sub_industry: str, max_pages: int = 3):
        """爬取单个关键词的企业职位和猎头职位"""
        all_jobs = []

        # 爬取两种职位类型
        for job_type in ['企业职位', '猎头职位']:
            print(f"  【{job_type}】搜索 '{keyword}':")

            for page in range(1, max_pages + 1):
                # 猎聘搜索URL：默认是企业职位，猎头职位需要在页面上切换tab
                # 但通过分析，两个tab的搜索URL不同
                if job_type == '猎头职位':
                    url = f'https://www.liepin.com/zhaopin/?key={keyword}&page={page}&headhunter=1'
                else:
                    url = f'https://www.liepin.com/zhaopin/?key={keyword}&page={page}'

                print(f"    第{page}页...", end=' ')

                try:
                    page_obj = browser.new_page()
                    page_obj.goto(url, wait_until='networkidle', timeout=60000)
                    page_obj.wait_for_timeout(3000)

                    html = page_obj.content()
                    jobs = self.extract_jobs_from_page(html, keyword, category, sub_industry, job_type)

                    print(f"找到 {len(jobs)} 个职位")
                    all_jobs.extend(jobs)

                    page_obj.close()

                    if len(jobs) == 0:
                        break  # 没有更多结果

                    time.sleep(2)  # 避免请求过快

                except Exception as e:
                    print(f"失败: {e}")
                    break

        return all_jobs

    def scrape_all(self):
        """爬取所有行业"""
        print("=" * 60)
        print("开始爬取猎聘职位数据")
        print("=" * 60)

        start_time = datetime.now()

        with Camoufox(headless=True) as browser:
            for category, sub_industries in self.INDUSTRIES.items():
                print(f"\n{'='*60}")
                print(f"行业大类: {category}")
                print(f"{'='*60}")

                for sub_industry, keywords in sub_industries.items():
                    print(f"\n--- 细分行业: {sub_industry} ---")

                    for keyword in keywords:
                        jobs = self.scrape_keyword(browser, keyword, category, sub_industry, max_pages=37)
                        self.jobs.extend(jobs)
                        time.sleep(1)

                        # 显示进度
                        elapsed = (datetime.now() - start_time).seconds
                        print(f"    [进度] 已爬取 {len(self.jobs)} 个职位，耗时 {elapsed//60}分{elapsed%60}秒")

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
            filename = f'/Users/meteor/爬虫实习项目/猎聘/猎聘_能源化工环保_政府非营利农林_{timestamp}.xlsx'

        # 按照模板格式整理数据（23列，表头完全匹配）
        data = []
        for job in self.jobs:
            # 解析省份
            location = job.get('location', '')
            province = get_province(location)

            data.append({
                '序号': job.get('sequence', ''),
                '招聘平台': '猎聘',
                '岗位类型\n一级': job.get('industry_category', ''),
                '岗位类型\n二级': job.get('sub_industry', ''),
                '岗位名称': job.get('title', ''),
                '岗位类型\n企业/公务员/事业单位/军队文职': job.get('job_type', '企业职位'),
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
                '备注（技能要求）': f"行业标签: {job.get('industry_tag', '')} | 搜索关键词: {job.get('search_keyword', '')}",
            })

        df = pd.DataFrame(data)

        # 设置列顺序（严格匹配模板）
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
    scraper = LiepinFullScraper()
    scraper.scrape_all()
    scraper.save_to_excel()


if __name__ == '__main__':
    main()
