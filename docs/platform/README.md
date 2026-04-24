# TrendRadar 平台化 · 文档索引

> 把单用户爬虫 `trend-radar` 平台化为多租户 SaaS 的设计文档集。

## 文档列表

| 顺序 | 文档 | 版本 | 状态 | 内容 |
|---|---|---|---|---|
| 1 | [product-spec.md](./product-spec.md) | v0.3 | ✅ Aligned | 产品方案：用户画像 / 价值主张 / V1-V3 功能范围 / 用户旅程 / 反向边界 / 成功指标 |
| 2 | [architecture.md](./architecture.md) | v0.2 | ✅ Aligned | 架构选型：整体架构图 / 9 条 ADR / 部署拓扑 / 成本估算 / 回退 / 观测性 / 安全 |
| 3 | [technical-design.md](./technical-design.md) | v0.1 | ✅ Aligned | 技术方案：C4 组件图 / ER 图 / 时序图 / 模块依赖 / 迁移路径 / 容量估算 / 测试策略 |

## 阅读顺序

1. **product → architecture → technical**：前一篇是后一篇的约束
2. 每篇顶部有 Review Status 表和 **验收标准自检**，快速判断覆盖完整性
3. 每篇末尾的"待定事项"记录了已决策（✅）和未决（⏳）项

## 关键决策摘要

| 维度 | 决策 |
|---|---|
| 目标用户 | AI 研发 + AI PM（V1 5-10 人内测） |
| 接收渠道 | Telegram（个人）+ 飞书群（被动接收） |
| **控制面** | 统一 TG Bot（ADR-004 v0.2：砍 Web form） |
| 计算平台 | Oracle VM Always Free（Ampere 4c/24GB） |
| 数据层 | Postgres 16 + Redis 7 |
| 调度 | Celery 5 + Beat（V1 `--concurrency=1`） |
| 匹配 | contains（V1）→ embedding（V2 候选） |
| 观测 | Sentry × 4 进程 + Uptimerobot + worker heartbeat |

## 实施状态

见仓库根目录 [Tasks](../../#tasks) 或 `/tasks` 清单。
