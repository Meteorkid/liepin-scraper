# 猎聘数据爬取项目

## What This Is

从猎聘网（liepin.com）爬取特定行业的招聘数据，包括能源/化工/环保和政府/非营利/农林牧渔两大行业类别。数据用于师融百工项目的人才数据分析。

## Core Value

**获取完整、准确的招聘数据**，包括职位信息、公司信息、工作内容、任职要求等字段，严格按照指定的23列模板格式输出。

## Context

### 项目背景
- 用户刘鑫宇需要完成实习数据爬取任务
- 目标数据量：40万条（实际受限于猎聘平台数据量）
- 输出格式：`师融百工-数据模板.xlsx`（23列格式）
- 时间要求：明天中午前完成

### 技术环境
- Python 3.12 + Camoufox（反检测浏览器）
- curl_cffi（模拟浏览器请求）
- BeautifulSoup（HTML解析）
- pandas + openpyxl（Excel处理）

### 已有进展
- 列表页爬取：已实现，能提取基本字段
- 详情页提取：已实现，通过 Schema.org 结构化数据提取
- 智能限速：已实现，避免被猎聘封禁
- 数据量：当前约1,600条，持续爬取中

## Requirements

### Validated

- ✓ 列表页爬取：能从行业分类页面和搜索结果页提取职位信息
- ✓ 详情页提取：能从 Schema.org 结构化数据中提取完整字段
- ✓ 智能限速：被封时自动退避，成功后逐步恢复
- ✓ 数据去重：使用岗位链接作为唯一标识
- ✓ 省份解析：从城市名自动映射省份
- ✓ 增量保存：每50条自动保存到Excel

### Active

- [ ] 覆盖所有9个目标行业
- [ ] 补全所有23个字段
- [ ] 达到40万条数据量目标
- [ ] 处理详情页反爬限制

### Out of Scope

- 其他招聘平台（智联招聘、BOSS直聘等）— 本次只爬取猎聘
- 实时数据监控 — 只做一次性爬取
- 数据清洗和分析 — 爬取完成后由用户处理

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 使用Camoufox | 原生反检测浏览器，绕过JS环境检测 | ✓ 已采用 |
| 使用curl_cffi提取详情页 | 比浏览器更快，成功率高 | ✓ 已采用 |
| Schema.org结构化数据 | 详情页数据藏在script标签中，即使页面看似404也能提取 | ✓ 已验证 |
| 智能限速 | 猎聘反爬严格，需要动态调整请求间隔 | ✓ 已实现 |
| 断点续爬 | 避免重复爬取，支持长时间运行 | ✓ 已实现 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-06 after initialization*
