#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猎聘详情页反爬研究总结
"""

研究总结 = """
============================================================
猎聘详情页反爬研究总结
============================================================

一、问题分析
----------------
1. 现象：详情页（如 /a/76135965.shtml）返回404或错误页面
2. 原因分析：
   - 详情页使用JavaScript动态渲染
   - 页面内容通过Schema.org结构化数据提供
   - 直接访问HTML页面无法获取完整数据

二、解决方案
----------------
✅ 最佳方案：使用curl_cffi提取Schema.org结构化数据

核心发现：
1. 页面包含 <script type="application/ld+json"> 标签
2. 标签内有完整的职位数据（JSON格式）
3. 数据字段包括：
   - title: 职位名称
   - description: 职位描述（包含工作内容和任职要求）
   - datePosted: 发布时间
   - validThrough: 有效期
   - experienceRequirements: 经验要求
   - educationRequirements: 学历要求
   - jobLocation: 工作地点
   - hiringOrganization: 公司信息
   - industry: 行业

三、测试结果
----------------
1. 字段提取率：93.3%（14/15字段成功提取）
2. 成功率：100%（不同间隔测试）
3. 详细字段提取情况：
   ✅ 职位名称 (title)
   ✅ 公司名称 (company)
   ✅ 职位描述 (description)
   ✅ 工作内容 (work_content)
   ✅ 任职要求 (requirements)
   ❌ 福利标签 (welfare_tags) - 部分职位可能没有
   ✅ 详细地址 (address)
   ✅ 城市 (city)
   ✅ 省份 (province)
   ✅ 经验要求 (experience)
   ✅ 学历要求 (education)
   ✅ 发布时间 (publish_time)
   ✅ 有效期 (valid_through)
   ✅ 行业 (industry)
   ✅ 职位ID (job_id)

四、代码实现
----------------
核心代码示例：

from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup
import re
import json

def extract_job_detail(url):
    session = curl_requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    # 初始化会话
    session.get("https://www.liepin.com/", impersonate="chrome120")

    # 访问详情页
    resp = session.get(url, impersonate="chrome120")
    soup = BeautifulSoup(resp.text, 'html.parser')

    # 提取Schema.org数据
    for script in soup.find_all('script', type='application/ld+json'):
        if script.string and 'JobPosting' in script.string:
            json_str = script.string.strip()
            json_str = re.sub(r'[\\x00-\\x1f\\x7f-\\x9f]', ' ', json_str)
            data = json.loads(json_str)

            if data.get('@type') == 'JobPosting':
                return {
                    'title': data.get('title', ''),
                    'description': data.get('description', ''),
                    'address': data.get('jobLocation', {}).get('address', {}).get('streetAddress', ''),
                    'experience': data.get('experienceRequirements', ''),
                    'education': data.get('educationRequirements', ''),
                    'publish_time': data.get('datePosted', ''),
                }
    return None

五、最佳实践
----------------
1. 会话管理：
   - 先访问首页获取必要的Cookie
   - 保持会话状态以提高成功率

2. 限速策略：
   - 最小间隔：0.5秒（测试显示成功率100%）
   - 推荐间隔：1-2秒（平衡速度和稳定性）
   - 批量爬取时添加随机延迟

3. 错误处理：
   - 检查HTTP状态码
   - 验证页面是否包含职位数据
   - 处理无效URL和404页面

4. 数据清洗：
   - 分离工作内容和任职要求
   - 统一日期格式
   - 处理特殊字符

六、文件说明
----------------
1. liepin_detail_research.py - 反爬机制研究脚本
2. liepin_detail_scraper.py - 详情页提取器
3. liepin_detail_test.py - 方案验证测试
4. liepin_full_scraper_v3.py - 完整爬虫（列表页+详情页）
5. liepin_detail_debug.html - 调试用HTML文件
6. liepin_detail_results.json - 测试结果

七、注意事项
----------------
1. 福利标签可能在某些职位中不存在
2. 某些字段可能为空（如详细地址）
3. 建议在爬取前先测试单个URL
4. 大规模爬取时注意限速和异常处理
5. 定期保存数据以防丢失

============================================================
"""

print(研究总结)

if __name__ == "__main__":
    print("研究总结已输出")
