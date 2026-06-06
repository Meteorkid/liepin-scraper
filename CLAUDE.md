# 猎聘数据爬取项目

## 项目概述
- **目标**：从猎聘网爬取能源/化工/环保 + 政府/非营利/农林牧渔行业的招聘数据
- **输出格式**：严格按照 `师融百工-数据模板.xlsx` 的23列格式
- **目标数据量**：40万条（实际受限于猎聘平台数据量）

## 技术栈
- **Python 3.12**（虚拟环境：`/Users/meteor/github/omnicrawl/.venv312`）
- **Camoufox**：反检测浏览器，用于访问列表页
- **curl_cffi**：模拟浏览器请求，用于提取详情页数据
- **BeautifulSoup**：HTML解析
- **pandas + openpyxl**：Excel数据处理

## 项目结构
```
猎聘/
├── CLAUDE.md                    # 本文件
├── 师融百工-数据模板.xlsx         # 输出模板（23列格式）
├── 爬虫代码/
│   ├── liepin_scraper_final.py  # 最终版爬虫（当前使用）
│   ├── liepin_detail_scraper.py # 详情页提取器
│   ├── liepin_full_scraper_v2.py # 完整爬虫V2
│   ├── liepin_full_scraper_v3.py # 完整爬虫V3
│   ├── scraper_final.log        # 爬虫运行日志
│   └── *.xlsx                   # 输出数据文件
```

## 核心爬虫架构

### 1. 列表页爬取（Camoufox）
- 访问猎聘行业分类页面或搜索结果页
- 使用 Playwright 自动化浏览器
- 智能限速：被封时指数退避（5s → 180s）
- 每页提取：职位名称、薪资、经验、学历、公司名称、公司规模、城市、岗位链接

### 2. 详情页提取（curl_cffi）
- 使用 Schema.org 结构化数据（`<script type="application/ld+json">`）
- 提取：工作内容、任职要求、福利标签、详细地址、发布时间
- 字段提取率：93.3%，成功率：100%

### 3. 数据处理
- **去重**：使用岗位链接作为唯一标识
- **省份解析**：从城市名自动映射省份（CITY_TO_PROVINCE 字典）
- **断点续爬**：加载已有数据，跳过已爬取的链接

## 反爬策略

### 猎聘限制机制
- **IP限制**：频繁访问后返回0条数据
- **冷却时间**：3-5分钟可恢复
- **浏览器指纹**：检测自动化工具

### 应对方案
1. **SmartRateLimiter**：智能限速器
   - 最小延时：5秒
   - 最大延时：180秒
   - 退避因子：2.0
   - 成功后逐步恢复
2. **浏览器实例复用**：避免频繁创建新实例
3. **行业间冷却**：60-120秒
4. **每10页额外等待**：30-60秒

## 数据模板（23列）
1. 序号
2. 招聘平台（固定：猎聘）
3. 岗位类型\n一级
4. 岗位类型\n二级
5. 岗位名称
6. 岗位类型\n企业/公务员/事业单位/军队文职
7. 公司名称
8. 公司规模
9. 所在省份
10. 城市
11. 详细地址
12. 学历要求
13. 经验要求
14. 薪资范围
15. 福利标签
16. 工作内容
17. 任职要求
18. 岗位链接
19. 发布时间
20. 投递起始时间
21. 投递截止时间
22. 证书要求
23. 备注（技能要求）

## 目标行业

### 能源/化工/环保
- 矿产开采、金属冶炼、电力/热力/水务、新能源、石化/化工、环保
- URL：`https://www.liepin.com/career/nengyuankuangchanhuanbao/`

### 政府/非营利/农林牧渔
- 政府/公共事业、非营利组织、农林牧渔
- URL：`https://www.liepin.com/career/gongwuyuannonglinmuyuqt/`

## 运行方式

### 启动爬虫
```bash
cd /Users/meteor/爬虫实习项目/猎聘/爬虫代码
/Users/meteor/github/omnicrawl/.venv312/bin/python3 -u liepin_scraper_final.py > scraper_final.log 2>&1 &
```

### 检查状态
```bash
ps aux | grep "liepin_scraper_final.py" | grep -v grep
tail -20 scraper_final.log
```

### 停止爬虫
```bash
kill <PID>
```

## 注意事项
1. **不要频繁重启**：重启会导致丢失当前进度
2. **等待冷却**：被封后需要等待3-5分钟
3. **监控日志**：检查是否有"被限制"或"提取 0 条"的警告
4. **定期保存**：每50条自动保存到Excel
