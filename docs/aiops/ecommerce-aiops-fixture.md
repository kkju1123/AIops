# Java 电商微服务 AIOps 测试数据

这套辅助数据用于验证真实 CLS、Alertmanager、知识库检索和 AIOps 证据链。应用服务仍在本地运行，Docker 默认只需提供 PostgreSQL + pgvector；Alertmanager 按需启动。

## 数据规模与关联

脚本一次生成 10 套 Java 电商微服务故障。每套包含：

- 1 条带异常、指标、阈值和依赖信息的 CLS 关键日志；
- 1 条带 `environment=test`、`fixture=java-ecommerce` 的活动告警；
- 1 个独立的 32 位 trace ID；
- 1 份所属故障类别的通用排查手册（runbook），告警 annotation `runbook` 指向它。

日志与告警通过 `incident_id`、`service`、`alertname`、`trace_id`、`runbook` 关联。10 个场景共用 7 份类别手册（下游依赖、数据库争用、缓存、CPU、消息消费、搜索集群、鉴权），手册列出多个候选根因及区分证据，**不包含任何场景的具体根因**。下表的“故障逻辑”是评测用的标准答案，只保存在 fixture 和本文档中，不会进入知识库、日志或告警。

| # | Java 服务 | 告警 | 故障逻辑 |
|---|---|---|---|
| 1 | `payment-service` | `PaymentGatewayTimeoutHigh` | 支付网关 TLS/读取超时导致订单停留在 PAYING |
| 2 | `inventory-service` | `InventoryReservationLockWaitHigh` | 补库存长事务与热门 SKU 预占发生行锁竞争 |
| 3 | `order-service` | `OrderDatabasePoolExhausted` | 无分页慢查询占满 HikariCP 连接池 |
| 4 | `cart-service` | `CartRedisLatencyHigh` | 促销索引热 key 大对象反序列化阻塞 Redis |
| 5 | `api-gateway` | `GatewayCheckoutCircuitOpen` | 库存服务错误触发结算熔断器打开 |
| 6 | `promotion-service` | `PromotionRuleEvaluationCpuHigh` | 组合促销规则导致指数级计算和 CPU 饱和 |
| 7 | `order-event-consumer` | `OrderEventConsumerLagHigh` | 新枚举值反序列化失败，poison message 持续重试 |
| 8 | `product-search-service` | `ProductSearchTimeoutHigh` | wildcard 查询耗尽 Elasticsearch search 线程池 |
| 9 | `auth-service` | `AuthJwkRefreshFailureHigh` | key 轮换后代理 DNS 故障导致 JWK 缓存无法刷新 |
| 10 | `fulfillment-service` | `FulfillmentProviderUnavailable` | 物流供应商 503 且无退避重试造成请求放大 |

## 执行步骤

1. 启动所需基础设施：

   ```bash
   docker compose -f infra/compose.yaml up -d --wait postgres
   docker compose -f infra/compose.yaml --profile observability up -d alertmanager
   ```

2. 使用本地启动脚本或开发命令启动后端、前端和 CLS MCP Server。

3. 上传 10 条真实 CLS 日志：

   ```bash
   cd apps/backend
   uv run python scripts/generate_and_upload_cls_logs.py --profile java-ecommerce
   ```

4. 向本地 Alertmanager 发布 10 条活动告警：

   ```bash
   uv run python scripts/publish_java_ecommerce_alerts.py --profile java-ecommerce
   ```

5. 为配置的演示用户上传并索引 7 份类别手册（同时删除旧版场景 SOP）：

   ```bash
   uv run python scripts/seed_ecommerce_aiops_sop.py --profile runbooks
   ```

6. 打开 AIOps 工作区，刷新活动告警，选择任一 Java 电商告警进行诊断。日志查询应命中告警 annotations 中的 trace ID，Planner 应检索到该场景所属类别的手册。

## 兼容量化场景

原有量化服务 fixture 保留，可显式执行：

```bash
uv run python scripts/generate_and_upload_cls_logs.py --profile quant --count 16
uv run python scripts/publish_ecommerce_quant_alert.py --profile quant
uv run python scripts/seed_ecommerce_aiops_sop.py --profile quant
```

所有数据均为 `test` fixture，不包含真实用户信息、密码、token 或云凭据。重复上传 SOP 使用稳定文件名和 overwrite 策略。
