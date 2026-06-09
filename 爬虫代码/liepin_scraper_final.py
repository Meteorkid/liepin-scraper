#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘完整爬虫 - 最终版
策略：
1. 列表页获取职位链接和基本信息
2. curl_cffi 详情页获取工作内容、任职要求、福利标签等
3. 智能限速 + 被封冷却恢复
4. 支持断点续爬（跳过已有的岗位链接）
5. 增量保存数据
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

# 已有数据文件（断点续爬用）- 自动查找最新的爬虫输出文件
def find_latest_data_file():
    """查找最新的爬虫输出xlsx文件"""
    import glob
    pattern = str(OUTPUT_DIR / "猎聘_完整爬虫*.xlsx")
    files = glob.glob(pattern)
    if not files:
        return None
    # 按修改时间排序，返回最新的（转为Path对象）
    return Path(max(files, key=os.path.getmtime))

EXISTING_DATA_FILE = find_latest_data_file()

# 省份映射
CITY_TO_PROVINCE = {
    '北京': '北京市', '上海': '上海市', '天津': '天津市', '重庆': '重庆市',
    '石家庄': '河北省', '太原': '山西省', '呼和浩特': '内蒙古自治区',
    '沈阳': '辽宁省', '长春': '吉林省', '哈尔滨': '黑龙江省',
    '南京': '江苏省', '无锡': '江苏省', '徐州': '江苏省', '常州': '江苏省',
    '苏州': '江苏省', '南通': '江苏省', '连云港': '江苏省', '淮安': '江苏省',
    '盐城': '江苏省', '扬州': '江苏省', '镇江': '江苏省', '泰州': '江苏省',
    '宿迁': '江苏省', '昆山': '江苏省', '张家港': '江苏省', '常熟': '江苏省',
    '江阴': '江苏省', '太仓': '江苏省', '宜兴': '江苏省', '溧阳': '江苏省',
    '杭州': '浙江省', '宁波': '浙江省', '温州': '浙江省', '嘉兴': '浙江省',
    '湖州': '浙江省', '绍兴': '浙江省', '金华': '浙江省', '衢州': '浙江省',
    '舟山': '浙江省', '台州': '浙江省', '丽水': '浙江省',
    '合肥': '安徽省', '芜湖': '安徽省', '蚌埠': '安徽省', '淮南': '安徽省',
    '马鞍山': '安徽省', '淮北': '安徽省', '铜陵': '安徽省', '安庆': '安徽省',
    '黄山': '安徽省', '滁州': '安徽省', '阜阳': '安徽省', '宿州': '安徽省',
    '福州': '福建省', '厦门': '福建省', '莆田': '福建省', '三明': '福建省',
    '泉州': '福建省', '漳州': '福建省', '南平': '福建省', '龙岩': '福建省',
    '南昌': '江西省', '景德镇': '江西省', '赣州': '江西省', '九江': '江西省',
    '济南': '山东省', '青岛': '山东省', '淄博': '山东省', '烟台': '山东省',
    '潍坊': '山东省', '济宁': '山东省', '泰安': '山东省', '威海': '山东省',
    '郑州': '河南省', '开封': '河南省', '洛阳': '河南省', '新乡': '河南省',
    '焦作': '河南省', '许昌': '河南省', '南阳': '河南省', '信阳': '河南省',
    '武汉': '湖北省', '宜昌': '湖北省', '襄阳': '湖北省', '荆州': '湖北省',
    '长沙': '湖南省', '株洲': '湖南省', '湘潭': '湖南省', '衡阳': '湖南省',
    '岳阳': '湖南省', '常德': '湖南省', '益阳': '湖南省', '郴州': '湖南省',
    '广州': '广东省', '深圳': '广东省', '珠海': '广东省', '佛山': '广东省',
    '东莞': '广东省', '中山': '广东省', '惠州': '广东省', '汕头': '广东省',
    '南宁': '广西壮族自治区', '柳州': '广西壮族自治区', '桂林': '广西壮族自治区',
    '海口': '海南省', '三亚': '海南省',
    '成都': '四川省', '绵阳': '四川省', '德阳': '四川省', '宜宾': '四川省',
    '贵阳': '贵州省', '遵义': '贵州省',
    '昆明': '云南省', '曲靖': '云南省', '玉溪': '云南省',
    '拉萨': '西藏自治区',
    '西安': '陕西省', '宝鸡': '陕西省', '咸阳': '陕西省', '渭南': '陕西省',
    '兰州': '甘肃省', '天水': '甘肃省',
    '西宁': '青海省',
    '银川': '宁夏回族自治区',
    '乌鲁木齐': '新疆维吾尔自治区', '克拉玛依': '新疆维吾尔自治区',
    '香港': '香港特别行政区', '澳门': '澳门特别行政区', '台湾': '台湾省',
    # 区级匹配（常见区名 → 城市）
    '丰台区': '北京', '朝阳区': '北京', '海淀区': '北京', '西城区': '北京',
    '东城区': '北京', '通州区': '北京', '顺义区': '北京', '大兴区': '北京',
    '昌平区': '北京', '石景山区': '北京',
    '浦东新区': '上海', '闵行区': '上海', '宝山区': '上海', '嘉定区': '上海',
    '松江区': '上海', '青浦区': '上海', '奉贤区': '上海', '崇明区': '上海',
    '黄浦区': '上海', '徐汇区': '上海', '长宁区': '上海', '静安区': '上海',
    '天河区': '广州', '白云区': '广州', '黄埔区': '广州', '番禺区': '广州',
    '南山区': '深圳', '福田区': '深圳', '宝安区': '深圳', '龙华区': '深圳',
    '龙岗区': '深圳', '光明区': '深圳', '罗湖区': '深圳',
    '西湖区': '杭州', '滨江区': '杭州', '余杭区': '杭州', '萧山区': '杭州',
    '上城区': '杭州', '拱墅区': '杭州', '临平区': '杭州', '钱塘区': '杭州',
    '高新区': '成都', '武侯区': '成都', '锦江区': '成都', '青羊区': '成都',
    '金牛区': '成都', '成华区': '成都', '龙泉驿区': '成都', '新都区': '成都',
    '洪山区': '武汉', '武昌区': '武汉', '江岸区': '武汉', '江汉区': '武汉',
    '硚口区': '武汉', '汉阳区': '武汉', '青山区': '武汉', '东西湖区': '武汉',
    '江宁区': '南京', '栖霞区': '南京', '浦口区': '南京', '雨花台区': '南京',
    '建邺区': '南京', '秦淮区': '南京', '玄武区': '南京', '鼓楼区': '南京',
    '姑苏区': '苏州', '虎丘区': '苏州', '吴中区': '苏州', '相城区': '苏州',
    '吴江区': '苏州', '工业园区': '苏州', '高新区': '苏州',
    '历下区': '济南', '市中区': '济南', '槐荫区': '济南', '天桥区': '济南',
    '历城区': '济南',
    '雁塔区': '西安', '碑林区': '西安', '莲湖区': '西安', '新城区': '西安',
    '未央区': '西安', '灞桥区': '西安', '长安区': '西安',
    '渝中区': '重庆', '江北区': '重庆', '南岸区': '重庆', '九龙坡区': '重庆',
    '沙坪坝区': '重庆', '大渡口区': '重庆', '渝北区': '重庆', '巴南区': '重庆',
    '北碚区': '重庆',
    '五华区': '昆明', '盘龙区': '昆明', '官渡区': '昆明', '西山区': '昆明',
    '呈贡区': '昆明',
    '南明区': '贵阳', '云岩区': '贵阳', '花溪区': '贵阳', '观山湖区': '贵阳',
    '小店区': '太原', '迎泽区': '太原', '杏花岭区': '太原',
    '长安区': '石家庄', '桥西区': '石家庄', '新华区': '石家庄', '裕华区': '石家庄',
    '道里区': '哈尔滨', '南岗区': '哈尔滨', '道外区': '哈尔滨', '香坊区': '哈尔滨',
    '南关区': '长春', '宽城区': '长春', '朝阳区': '长春', '二道区': '长春',
    '和平区': '沈阳', '沈河区': '沈阳', '大东区': '沈阳', '皇姑区': '沈阳',
    '铁西区': '沈阳',
    '香洲区': '珠海', '金湾区': '珠海', '斗门区': '珠海',
    '禅城区': '佛山', '南海区': '佛山', '顺德区': '佛山',
    '鼓楼区': '福州', '台江区': '福州', '仓山区': '福州', '马尾区': '福州',
    '思明区': '厦门', '湖里区': '厦门', '集美区': '厦门', '海沧区': '厦门',
    '东湖区': '南昌', '西湖区': '南昌', '青云谱区': '南昌', '红谷滩区': '南昌',
    '金水区': '郑州', '二七区': '郑州', '中原区': '郑州', '管城区': '郑州',
    '岳麓区': '长沙', '芙蓉区': '长沙', '天心区': '长沙', '开福区': '长沙',
    '雨花区': '长沙',
    '龙华区': '海口', '美兰区': '海口', '琼山区': '海口', '秀英区': '海口',
    '城关区': '拉萨',
}


def get_province(city: str) -> str:
    """从城市名获取省份"""
    if not city:
        return ''
    # 直接匹配
    if city in CITY_TO_PROVINCE:
        return CITY_TO_PROVINCE[city]
    # 去掉区名后匹配
    for suffix in ['·', '市', '地区', '州', '区']:
        if suffix in city:
            city_part = city.split(suffix)[0]
            if city_part in CITY_TO_PROVINCE:
                return CITY_TO_PROVINCE[city_part]
    # 模糊匹配
    for key, value in CITY_TO_PROVINCE.items():
        if key in city or city in key:
            return value
    return ''


class SmartRateLimiter:
    """智能限速器"""
    def __init__(self, min_delay=5.0, max_delay=180.0, backoff_factor=2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.current_delay = min_delay
        self.block_count = 0
        self.success_count = 0

    def report_blocked(self):
        self.block_count += 1
        self.success_count = 0
        self.current_delay = min(
            self.min_delay * (self.backoff_factor ** self.block_count),
            self.max_delay
        )
        print(f"⚠️  被限制！当前延时: {self.current_delay:.1f}秒, 连续被封: {self.block_count}次")

    def report_success(self):
        self.success_count += 1
        if self.success_count >= 3:
            self.block_count = max(0, self.block_count - 1)
            self.current_delay = max(
                self.min_delay,
                self.current_delay / self.backoff_factor
            )

    def wait(self):
        jitter = random.uniform(0.8, 1.2)
        delay = self.current_delay * jitter
        print(f"⏳ 等待 {delay:.1f}秒...")
        time.sleep(delay)

    def cooldown(self, seconds=None):
        """长时间冷却"""
        if seconds is None:
            seconds = self.current_delay * 3
        print(f"🧊 冷却 {seconds:.0f}秒...")
        time.sleep(seconds)


class DetailExtractor:
    """详情页数据提取器（curl_cffi）"""

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
        if self.initialized:
            return
        try:
            self.session.get("https://www.liepin.com/", impersonate="chrome120")
            self.initialized = True
            time.sleep(1)
        except Exception as e:
            print(f"  详情页会话初始化失败: {e}")

    def extract(self, url: str) -> Optional[Dict]:
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
                            result['industry'] = data.get('industry', '')

                            location = data.get('jobLocation', {})
                            if isinstance(location, dict):
                                address = location.get('address', {})
                                if isinstance(address, dict):
                                    result['address'] = address.get('streetAddress', '')
                                    result['city'] = address.get('addressLocality', '')
                                    result['province'] = address.get('addressRegion', '')
                            break
                    except:
                        pass

            # 提取福利标签（div.labels 包含 span 标签）
            labels_elem = soup.find('div', class_='labels')
            if labels_elem:
                # 提取所有 span 标签的文本，用逗号分隔
                spans = labels_elem.find_all('span')
                if spans:
                    result['welfare_tags'] = ', '.join([s.get_text(strip=True) for s in spans])
                else:
                    result['welfare_tags'] = labels_elem.get_text(strip=True)

            # 分离工作内容和任职要求
            if result.get('description'):
                desc = result['description']
                separators = ['任职要求', '任职资格', '岗位要求', '职位要求', '岗位职责']
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
            print(f"  详情提取失败: {e}")
            return None


class LiepinFinalScraper:
    """猎聘最终爬虫"""

    def __init__(self):
        self.all_jobs = []
        self.seen_links = set()  # 用岗位链接去重
        self.rate_limiter = SmartRateLimiter()
        self.detail_extractor = DetailExtractor()
        self.output_file = OUTPUT_DIR / f"猎聘_完整爬虫_最终版_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # 加载已有数据（断点续爬）
        self._load_existing_data()

        # 行业分类URL
        self.industry_urls = [
            # 能源/化工/环保
            ("https://www.liepin.com/career/nengyuankuangchanhuanbao/", "能源/化工/环保", "矿产开采"),
            ("https://www.liepin.com/career/nengyuankuangchanhuanbao/", "能源/化工/环保", "金属冶炼"),
            ("https://www.liepin.com/career/nengyuankuangchanhuanbao/", "能源/化工/环保", "电力/热力/水务"),
            ("https://www.liepin.com/career/nengyuankuangchanhuanbao/", "能源/化工/环保", "新能源"),
            ("https://www.liepin.com/career/nengyuankuangchanhuanbao/", "能源/化工/环保", "石化/化工"),
            ("https://www.liepin.com/career/nengyuankuangchanhuanbao/", "能源/化工/环保", "环保"),
            # 政府/非营利/农林牧渔
            ("https://www.liepin.com/career/gongwuyuannonglinmuyuqt/", "政府/非营利/农林牧渔", "政府/公共事业"),
            ("https://www.liepin.com/career/gongwuyuannonglinmuyuqt/", "政府/非营利/农林牧渔", "非营利组织"),
            ("https://www.liepin.com/career/gongwuyuannonglinmuyuqt/", "政府/非营利/农林牧渔", "农林牧渔"),
        ]

        # 关键词列表（每个行业6个关键词）
        self.industry_keywords = {
            "能源/化工/环保": [
                "矿产开采", "采矿", "矿山", "金属冶炼", "钢铁", "冶金",
                "电力", "热力", "水务", "供电", "发电", "电网",
                "新能源", "光伏", "风电", "太阳能", "储能", "锂电池",
                "石化", "化工", "石油化工", "煤化工", "精细化工",
                "环保", "环境工程", "环境监测", "污染治理", "固废处理",
            ],
            "政府/非营利/农林牧渔": [
                "政府", "公务员", "事业单位", "公共事业", "公共服务",
                "非营利", "公益", "NGO", "基金会",
                "农业", "林业", "牧业", "渔业", "农艺", "畜牧", "兽医",
            ],
        }

        # 城市代码（dq参数）用于城市+行业交叉搜索
        self.city_codes = {
            "北京": "010", "上海": "020", "广州": "050020", "深圳": "050090",
            "成都": "280020", "杭州": "070020", "武汉": "170020", "南京": "060020",
            "重庆": "040020", "西安": "270020", "苏州": "060080", "天津": "030",
            "长沙": "180020", "郑州": "150020", "东莞": "050030", "青岛": "120020",
            "合肥": "140020", "佛山": "050050", "宁波": "070030", "昆明": "250020",
            "福州": "110020", "厦门": "110030", "大连": "080020", "沈阳": "080030",
            "济南": "120030", "无锡": "060030", "常州": "060050", "珠海": "050060",
        }

        # 用于交叉搜索的精简关键词
        self.search_keywords = [
            "采矿", "金属冶炼", "电力", "新能源", "化工", "环保",
            "政府", "农业", "林业", "牧业",
        ]

    def _load_existing_data(self):
        """加载已有数据（断点续爬）"""
        if EXISTING_DATA_FILE.exists():
            try:
                df = pd.read_excel(EXISTING_DATA_FILE)
                for _, row in df.iterrows():
                    link = str(row.get('岗位链接', ''))
                    if link and link not in self.seen_links:
                        self.seen_links.add(link)
                        job = {}
                        for col in df.columns:
                            val = row[col]
                            job[col] = '' if pd.isna(val) else str(val)
                        self.all_jobs.append(job)
                print(f"📂 加载已有数据: {len(self.all_jobs)} 条（去重链接: {len(self.seen_links)}）")
            except Exception as e:
                print(f"⚠️  加载已有数据失败: {e}")

    def calculate_md5(self, job_data: dict) -> str:
        key_str = f"{job_data.get('公司名称', '')}_{job_data.get('岗位名称', '')}_{job_data.get('薪资范围', '')}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def save_to_excel(self, jobs: List[dict]):
        if not jobs:
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
        # 添加序号
        df['序号'] = range(1, len(df) + 1)
        df.to_excel(self.output_file, index=False, engine='openpyxl')
        print(f"✅ 已保存 {self.output_file.name}，共 {len(df)} 条记录")

    def extract_job_from_card(self, card, category: str, sub_industry: str) -> Optional[dict]:
        try:
            job = {}

            # 职位链接
            link_elem = card.find('a', attrs={'data-jobid': True})
            if link_elem:
                job['岗位链接'] = link_elem.get('href', '')
                if job['岗位链接'] and not job['岗位链接'].startswith('http'):
                    job['岗位链接'] = 'https://www.liepin.com' + job['岗位链接']

            # 职位名称
            title_elem = card.find('div', class_='ellipsis-1', title=True)
            if title_elem:
                job['岗位名称'] = title_elem.get('title', '').strip()

            # 薪资
            salary_elem = card.find('span', class_='job-salary')
            if salary_elem:
                job['薪资范围'] = salary_elem.string.strip() if salary_elem.string else ''

            # 经验和学历
            labels = card.find_all('span', class_='labels-tag')
            if len(labels) >= 1:
                job['经验要求'] = labels[0].string.strip() if labels[0].string else ''
            if len(labels) >= 2:
                job['学历要求'] = labels[1].string.strip() if labels[1].string else ''

            # 公司名称
            company_elem = card.find('span', class_='company-name')
            if company_elem:
                job['公司名称'] = company_elem.string.strip() if company_elem.string else ''

            # 公司标签（行业、融资、规模）
            tags_box = card.find('div', class_='company-tags-box')
            if tags_box:
                tags = tags_box.find_all('span')
                if len(tags) >= 3:
                    job['行业标签'] = tags[0].string.strip() if tags[0].string else ''
                    job['公司规模'] = tags[2].string.strip() if tags[2].string else ''
                elif len(tags) >= 2:
                    job['公司规模'] = tags[1].string.strip() if tags[1].string else ''
                elif len(tags) >= 1:
                    job['公司规模'] = tags[0].string.strip() if tags[0].string else ''

            # 地点
            location_div = card.find('div', class_='job-dq-box')
            if location_div:
                location_text = location_div.get_text(strip=True)
                loc_match = re.search(r'【([^】]+)】', location_text)
                if loc_match:
                    raw_city = loc_match.group(1)
                    job['城市'] = raw_city
                    job['所在省份'] = get_province(raw_city)

            # 固定字段
            job['招聘平台'] = '猎聘'
            job['岗位类型\n一级'] = category.split('/')[0] if '/' in category else category
            job['岗位类型\n二级'] = sub_industry if sub_industry else ''
            job['岗位类型\n企业/公务员/事业单位/军队文职'] = '企业'

            return job

        except Exception as e:
            print(f"❌ 提取职位信息失败: {e}")
            return None

    def enrich_with_detail(self, job: dict) -> dict:
        """用详情页数据补全字段"""
        url = job.get('岗位链接', '')
        if not url:
            return job

        # 如果所有字段都已完整，跳过
        if job.get('工作内容') and job.get('任职要求') and job.get('福利标签'):
            return job

        detail = self.detail_extractor.extract(url)
        if not detail:
            return job

        # 补全字段（不覆盖列表页已有的数据）
        field_map = {
            '工作内容': 'work_content',
            '任职要求': 'requirements',
            '福利标签': 'welfare_tags',
            '详细地址': 'address',
            '发布时间': 'publish_time',
        }

        for cn_key, en_key in field_map.items():
            if not job.get(cn_key) and detail.get(en_key):
                job[cn_key] = detail[en_key]

        # 详情页城市/省份更精确
        if detail.get('city') and (not job.get('城市') or '区' in detail.get('city', '')):
            job['城市'] = detail['city']
        if detail.get('province'):
            job['所在省份'] = detail['province']
        if detail.get('experience') and not job.get('经验要求'):
            job['经验要求'] = detail['experience']
        if detail.get('education') and not job.get('学历要求'):
            job['学历要求'] = detail['education']

        # 备注
        notes = []
        if detail.get('industry'):
            notes.append(f"行业: {detail['industry']}")
        if detail.get('valid_through'):
            notes.append(f"有效期至: {detail['valid_through']}")
        if notes:
            job['备注（技能要求）'] = '; '.join(notes)

        return job

    async def scrape_list_page(self, page, url: str, category: str, sub_industry: str, is_search: bool = False) -> List[dict]:
        """爬取列表页"""
        jobs = []

        try:
            print(f"📄 访问: {url}")
            await page.goto(url, timeout=30000)

            # 搜索页面需要更长等待时间（JS渲染）
            if is_search:
                try:
                    await page.wait_for_selector('.job-card-pc-container', timeout=15000)
                except:
                    await asyncio.sleep(6)
            else:
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
                self.rate_limiter.report_blocked()
                return jobs

            for card in cards:
                job = self.extract_job_from_card(card, category, sub_industry)
                if job and job.get('岗位名称') and job.get('岗位链接'):
                    # 用链接去重
                    if job['岗位链接'] not in self.seen_links:
                        self.seen_links.add(job['岗位链接'])
                        jobs.append(job)

            self.rate_limiter.report_success()
            print(f"✓ 提取 {len(jobs)} 条职位（总去重: {len(self.seen_links)}）")

        except Exception as e:
            print(f"❌ 爬取页面失败: {e}")
            self.rate_limiter.report_blocked()

        return jobs

    async def scrape_industry(self, browser, base_url: str, category: str, sub_industry: str, max_pages: int = 50):
        """爬取一个行业的所有页面"""
        page = await browser.new_page()
        industry_jobs = []
        consecutive_blocked = 0

        try:
            for page_num in range(1, max_pages + 1):
                if page_num == 1:
                    page_url = base_url
                else:
                    page_url = f"{base_url.rstrip('/')}/pn{page_num - 1}/"

                print(f"\n{'='*60}")
                print(f"📊 {category}/{sub_industry} - 第 {page_num}/{max_pages} 页")
                print(f"{'='*60}")

                jobs = await self.scrape_list_page(page, page_url, category, sub_industry)

                if not jobs:
                    consecutive_blocked += 1
                    if consecutive_blocked >= 3:
                        print(f"⚠️  连续 {consecutive_blocked} 页无数据，停止此行业")
                        break
                else:
                    consecutive_blocked = 0

                # 获取详情页数据
                for job in jobs:
                    job = self.enrich_with_detail(job)
                    time.sleep(random.uniform(0.5, 1.5))  # 详情页限速
                    industry_jobs.append(job)
                    self.all_jobs.append(job)

                # 每50条保存
                if len(self.all_jobs) % 50 < 40:
                    self.save_to_excel(self.all_jobs)

                # 限速
                self.rate_limiter.wait()

                # 每10页额外等待
                if page_num % 10 == 0:
                    extra = random.uniform(30, 60)
                    print(f"⏸️  每10页额外等待 {extra:.0f}秒...")
                    await asyncio.sleep(extra)

        finally:
            await page.close()

        return industry_jobs

    async def scrape_keywords(self, browser, category: str, sub_industry: str, keywords: List[str], max_pages: int = 5):
        """爬取关键词搜索结果"""
        page = await browser.new_page()
        keyword_jobs = []

        try:
            for keyword in keywords:
                for page_num in range(1, max_pages + 1):
                    if page_num == 1:
                        search_url = f"https://www.liepin.com/zhaopin/?key={keyword}"
                    else:
                        search_url = f"https://www.liepin.com/zhaopin/?key={keyword}&pn={page_num - 1}"

                    print(f"\n{'='*60}")
                    print(f"🔍 关键词: {keyword}, 第 {page_num}/{max_pages} 页")
                    print(f"{'='*60}")

                    jobs = await self.scrape_list_page(page, search_url, category, sub_industry, is_search=True)

                    if not jobs:
                        print(f"⚠️  第 {page_num} 页无数据，停止此关键词")
                        break

                    # 获取详情页数据
                    for job in jobs:
                        job = self.enrich_with_detail(job)
                        time.sleep(random.uniform(0.5, 1.5))
                        keyword_jobs.append(job)
                        self.all_jobs.append(job)

                    # 每50条保存
                    if len(self.all_jobs) % 50 < 40:
                        self.save_to_excel(self.all_jobs)

                    self.rate_limiter.wait()

                # 关键词间等待
                await asyncio.sleep(random.uniform(5, 15))

        finally:
            await page.close()

        return keyword_jobs

    async def enrich_existing_detail(self):
        """补全已有数据的详情页字段"""
        jobs_needing = [j for j in self.all_jobs if j.get('岗位链接') and (
            not j.get('福利标签') or not j.get('工作内容') or not j.get('详细地址')
        )]
        if not jobs_needing:
            print("✅ 所有数据已完整")
            return

        print(f"\n📝 需要补全详情: {len(jobs_needing)} 条")
        enriched = 0
        for i, job in enumerate(jobs_needing):
            if enriched >= 500:  # 限制补全数量
                break

            url = job.get('岗位链接', '')
            if not url:
                continue

            try:
                detail = self.detail_extractor.extract(url)
                if detail:
                    # 补全所有缺失字段
                    if detail.get('welfare_tags') and not job.get('福利标签'):
                        job['福利标签'] = detail['welfare_tags']
                    if detail.get('work_content') and not job.get('工作内容'):
                        job['工作内容'] = detail['work_content']
                    if detail.get('requirements') and not job.get('任职要求'):
                        job['任职要求'] = detail['requirements']
                    if detail.get('address') and not job.get('详细地址'):
                        job['详细地址'] = detail['address']
                    if detail.get('city'):
                        job['城市'] = detail['city']
                    if detail.get('province'):
                        job['所在省份'] = detail['province']
                    enriched += 1
                    if enriched % 10 == 0:
                        print(f"  已补全 {enriched} 条详情")
                time.sleep(1)  # 限速
            except Exception as e:
                pass

        print(f"✅ 福利标签补全完成: {enriched} 条")
        if enriched > 0:
            self.save_to_excel(self.all_jobs)

    async def scrape_city_keyword(self, browser, city_name: str, city_code: str, keyword: str, category: str, sub_industry: str, max_pages: int = 3):
        """爬取城市+关键词组合的搜索结果"""
        page = await browser.new_page()
        jobs = []

        try:
            for page_num in range(1, max_pages + 1):
                if page_num == 1:
                    search_url = f"https://www.liepin.com/zhaopin/?key={keyword}&dq={city_code}"
                else:
                    search_url = f"https://www.liepin.com/zhaopin/?key={keyword}&dq={city_code}&pn={page_num - 1}"

                print(f"\n{'='*60}")
                print(f"🏙️  {city_name} + {keyword} - 第 {page_num}/{max_pages} 页")
                print(f"{'='*60}")

                page_jobs = await self.scrape_list_page(page, search_url, category, sub_industry, is_search=True)

                if not page_jobs:
                    print(f"⚠️  第 {page_num} 页无数据，停止此组合")
                    break

                jobs.extend(page_jobs)
                for job in page_jobs:
                    self.all_jobs.append(job)

                # 每50条保存
                if len(self.all_jobs) % 50 < 40:
                    self.save_to_excel(self.all_jobs)

                self.rate_limiter.wait()

                # 搜索间短等待
                await asyncio.sleep(random.uniform(3, 8))

        finally:
            await page.close()

        return jobs

    async def scrape_jobkind(self, browser, keyword: str, jobkind: int, jobkind_name: str, category: str, sub_industry: str, max_pages: int = 3):
        """爬取猎头/企业职位分类搜索结果"""
        page = await browser.new_page()
        jobs = []

        try:
            for page_num in range(1, max_pages + 1):
                if page_num == 1:
                    search_url = f"https://www.liepin.com/zhaopin/?key={keyword}&jobKind={jobkind}"
                else:
                    search_url = f"https://www.liepin.com/zhaopin/?key={keyword}&jobKind={jobkind}&pn={page_num - 1}"

                print(f"\n{'='*60}")
                print(f"👔 {jobkind_name} + {keyword} - 第 {page_num}/{max_pages} 页")
                print(f"{'='*60}")

                page_jobs = await self.scrape_list_page(page, search_url, category, sub_industry, is_search=True)

                if not page_jobs:
                    print(f"⚠️  第 {page_num} 页无数据，停止此组合")
                    break

                jobs.extend(page_jobs)
                for job in page_jobs:
                    self.all_jobs.append(job)

                # 每50条保存
                if len(self.all_jobs) % 50 < 40:
                    self.save_to_excel(self.all_jobs)

                self.rate_limiter.wait()

                # 搜索间短等待
                await asyncio.sleep(random.uniform(3, 8))

        finally:
            await page.close()

        return jobs

    async def run(self):
        print("🚀 启动猎聘完整爬虫（最终版）")
        print(f"📁 输出: {self.output_file}")
        print(f"📊 已有数据: {len(self.all_jobs)} 条")
        print(f"🔗 已有链接: {len(self.seen_links)} 个")
        print(f"🏭 目标行业: {len(self.industry_urls)} 个")
        print("="*60)

        async with AsyncCamoufox(headless=True) as browser:

            # 阶段0: 补全已有数据的详情字段
            if self.all_jobs:
                print("\n" + "="*60)
                print("📌 阶段0: 补全已有数据的详情字段")
                print("="*60)
                await self.enrich_existing_detail()

            # 阶段1: 行业分类页面
            print("\n" + "="*60)
            print("📌 阶段1: 爬取行业分类页面")
            print("="*60)

            for base_url, category, sub_industry in self.industry_urls:
                print(f"\n🏭 开始: {category}/{sub_industry}")

                await self.scrape_industry(browser, base_url, category, sub_industry, max_pages=50)

                # 行业间冷却
                cooldown_time = random.uniform(60, 120)
                print(f"\n⏸️  行业切换，冷却 {cooldown_time:.0f}秒...")
                await asyncio.sleep(cooldown_time)

                # 保存
                self.save_to_excel(self.all_jobs)

            # 阶段2: 关键词搜索
            print("\n" + "="*60)
            print("📌 阶段2: 爬取关键词搜索结果")
            print("="*60)

            for category, keywords in self.industry_keywords.items():
                sub_industry = keywords[0]
                print(f"\n🏷️  关键词组: {category}")
                await self.scrape_keywords(browser, category, sub_industry, keywords, max_pages=5)

                # 组间冷却
                await asyncio.sleep(random.uniform(60, 120))

            # 阶段3: 城市+关键词交叉搜索
            print("\n" + "="*60)
            print("📌 阶段3: 城市+关键词交叉搜索")
            print("="*60)

            search_count = 0
            for city_name, city_code in self.city_codes.items():
                for keyword in self.search_keywords:
                    # 确定行业分类
                    if keyword in ["采矿", "金属冶炼", "电力", "新能源", "化工", "环保"]:
                        category = "能源/化工/环保"
                        sub_industry = keyword
                    else:
                        category = "政府/非营利/农林牧渔"
                        sub_industry = keyword

                    await self.scrape_city_keyword(browser, city_name, city_code, keyword, category, sub_industry, max_pages=3)

                    search_count += 1
                    # 搜索间冷却
                    await asyncio.sleep(random.uniform(10, 25))

                    # 每10次搜索长冷却
                    if search_count % 10 == 0:
                        long_cool = random.uniform(60, 120)
                        print(f"\n⏸️  每10次搜索，冷却 {long_cool:.0f}秒...")
                        await asyncio.sleep(long_cool)
                        self.save_to_excel(self.all_jobs)

            # 阶段4: 猎头/企业职位拆分搜索
            print("\n" + "="*60)
            print("📌 阶段4: 猎头/企业职位拆分搜索")
            print("="*60)

            for keyword in self.search_keywords:
                if keyword in ["采矿", "金属冶炼", "电力", "新能源", "化工", "环保"]:
                    category = "能源/化工/环保"
                    sub_industry = keyword
                else:
                    category = "政府/非营利/农林牧渔"
                    sub_industry = keyword

                # 猎头职位
                await self.scrape_jobkind(browser, keyword, 1, "猎头职位", category, sub_industry, max_pages=3)
                await asyncio.sleep(random.uniform(10, 20))

                # 企业职位
                await self.scrape_jobkind(browser, keyword, 2, "企业职位", category, sub_industry, max_pages=3)
                await asyncio.sleep(random.uniform(10, 20))

                # 每组保存
                self.save_to_excel(self.all_jobs)

            # 最终保存
            self.save_to_excel(self.all_jobs)

            # 统计
            print("\n" + "="*60)
            print(f"✅ 爬取完成！")
            print(f"📊 总数据量: {len(self.all_jobs)} 条")
            print(f"📁 保存到: {self.output_file}")

            # 字段填充率统计
            df = pd.DataFrame(self.all_jobs)
            for col in ['公司名称', '公司规模', '所在省份', '城市', '学历要求', '经验要求', '薪资范围', '福利标签', '工作内容', '任职要求', '详细地址']:
                filled = df[col].apply(lambda x: pd.notna(x) and str(x).strip() != '').sum()
                print(f"  {col}: {filled}/{len(df)} ({filled/len(df)*100:.1f}%)")
            print("="*60)


async def main():
    scraper = LiepinFinalScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
