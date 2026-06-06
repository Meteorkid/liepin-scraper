# Roadmap

## Phase 1: 基础爬虫框架
**Goal:** 实现猎聘数据爬取的核心功能，包括列表页爬取、详情页提取、智能限速
**Mode:** mvp
**Success Criteria:**
1. 能从猎聘行业分类页面爬取职位列表
2. 能从详情页提取完整职位信息
3. 智能限速正常工作，被封时自动退避
4. 输出格式严格按照23列模板
**Requirements:** SCRAPER-01, SCRAPER-02, SCRAPER-03, SCRAPER-04, SCRAPER-05, DATA-01, DATA-02, DATA-03, DATA-04
**UI hint:** no

## Phase 2: 行业覆盖
**Goal:** 覆盖所有9个目标行业，包括能源/化工/环保和政府/非营利/农林牧渔
**Mode:** mvp
**Success Criteria:**
1. 能从能源/化工/环保行业爬取数据
2. 能从政府/非营利/农林牧渔行业爬取数据
3. 每个行业至少爬取10页数据
4. 数据量达到1万条以上
**Requirements:** INDUSTRY-01, INDUSTRY-02
**UI hint:** no

## Phase 3: 数据优化
**Goal:** 优化爬虫性能，提高数据质量和完整性
**Mode:** mvp
**Success Criteria:**
1. 详情字段填充率 > 80%
2. 无重复数据
3. 爬取速度提升50%
4. 支持长时间稳定运行
**Requirements:** (从Phase 1-2的经验中提炼)
**UI hint:** no
