# Requirements

## v1 Requirements

### 数据爬取
- [ ] **SCRAPER-01**: 能从猎聘行业分类页面爬取职位列表
- [ ] **SCRAPER-02**: 能从猎聘搜索结果页爬取职位列表
- [ ] **SCRAPER-03**: 能从详情页提取完整职位信息（工作内容、任职要求、福利标签等）
- [ ] **SCRAPER-04**: 支持智能限速，被封时自动退避
- [ ] **SCRAPER-05**: 支持断点续爬，避免重复爬取

### 数据处理
- [ ] **DATA-01**: 输出格式严格按照23列模板
- [ ] **DATA-02**: 自动解析城市到省份映射
- [ ] **DATA-03**: 使用岗位链接进行数据去重
- [ ] **DATA-04**: 每50条自动保存到Excel

### 行业覆盖
- [ ] **INDUSTRY-01**: 爬取能源/化工/环保行业（矿产开采、金属冶炼、电力/热力/水务、新能源、石化/化工、环保）
- [ ] **INDUSTRY-02**: 爬取政府/非营利/农林牧渔行业（政府/公共事业、非营利组织、农林牧渔）

## v2 Requirements

(None yet — ship to validate)

## Out of Scope

- 其他招聘平台（智联招聘、BOSS直聘等）— 本次只爬取猎聘
- 实时数据监控 — 只做一次性爬取
- 数据清洗和分析 — 爬取完成后由用户处理
- 40万条数据量目标 — 受限于猎聘平台实际数据量

## Acceptance Criteria

- 所有v1 requirements必须满足
- 数据字段填充率：公司名称、薪资、学历、经验 > 95%
- 详情字段填充率：工作内容、任职要求 > 80%
- 无重复数据（基于岗位链接去重）
- 输出文件可直接使用，无需额外处理

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCRAPER-01 | Phase 1 | ✓ Validated |
| SCRAPER-02 | Phase 1 | ✓ Validated |
| SCRAPER-03 | Phase 1 | ✓ Validated |
| SCRAPER-04 | Phase 1 | ✓ Validated |
| SCRAPER-05 | Phase 1 | ✓ Validated |
| DATA-01 | Phase 1 | ✓ Validated |
| DATA-02 | Phase 1 | ✓ Validated |
| DATA-03 | Phase 1 | ✓ Validated |
| DATA-04 | Phase 1 | ✓ Validated |
| INDUSTRY-01 | Phase 2 | In Progress |
| INDUSTRY-02 | Phase 2 | In Progress |
