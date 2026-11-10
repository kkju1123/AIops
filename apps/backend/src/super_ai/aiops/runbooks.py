"""Category-level troubleshooting runbooks for the e-commerce drill.

Each runbook covers one failure category and lists several candidate root causes with the
evidence that separates them, the way a real team runbook does. None of them is written
for a specific scenario, so a diagnosis has to pick the cause from the evidence it collects.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Hypothesis:
    cause: str
    supporting: str
    ruling_out: str


@dataclass(frozen=True, slots=True)
class Runbook:
    runbook_id: str
    title: str
    applies_to: tuple[str, ...]
    hypotheses: tuple[Hypothesis, ...]
    investigation: tuple[str, ...]
    mitigation: tuple[str, ...]
    verification: str

    @property
    def filename(self) -> str:
        return f"{self.runbook_id}.md"

    def render(self) -> str:
        applies = "\n".join(f"- {item}" for item in self.applies_to)
        rows = "\n".join(
            f"| {index} | {item.cause} | {item.supporting} | {item.ruling_out} |"
            for index, item in enumerate(self.hypotheses, start=1)
        )
        steps = "\n".join(
            f"{index}. {step}" for index, step in enumerate(self.investigation, start=1)
        )
        mitigation = "\n".join(
            f"{index}. {step}" for index, step in enumerate(self.mitigation, start=1)
        )
        return f"""# {self.title}

- **Runbook ID**: `{self.runbook_id}`
- 本手册按故障类别编写，适用于多个服务。下列根因假设只是常见候选，
  必须用本次查询到的日志与指标逐一验证，选出有证据支持的一项；证据不足时如实说明。

## 适用告警特征

{applies}

## 常见根因假设与区分证据

| # | 候选根因 | 支持证据 | 排除证据 |
|---|---------|---------|---------|
{rows}

## 排查步骤

{steps}

## 止血与恢复

{mitigation}

## 恢复验证

{self.verification}

## 风险控制

- 先止血再根治：恢复动作必须可回滚，变更前记录当前配置。
- 任何重试或重放都必须保留业务幂等键，避免重复扣款、重复扣减库存或重复创建运单。
- 报告只能引用实际查询到的日志与指标；没有证据支持的假设必须写明“未验证”。
"""


RUNBOOK_DOWNSTREAM_DEPENDENCY = Runbook(
    runbook_id="runbook-downstream-dependency",
    title="下游依赖超时、不可用与熔断排查手册",
    applies_to=(
        "调用外部或内部下游服务出现超时（SocketTimeoutException、ReadTimeout）或 5xx。",
        "熔断器打开（CallNotPermittedException），网关或调用方快速失败。",
        "业务请求停留在中间状态（如 PAYING、待分配物流），重试次数上升。",
    ),
    hypotheses=(
        Hypothesis(
            "调用方连接池或线程池耗尽，请求在本地排队",
            "连接池 pending 升高、获取连接超时；下游侧未见请求",
            "连接池空闲充足，下游已收到请求",
        ),
        Hypothesis(
            "下游服务自身故障或错误率升高，触发调用方熔断",
            "熔断器状态变更日志给出下游失败率超过阈值；半开探测仍失败；下游自身告警同时触发",
            "下游错误率正常，熔断阈值或窗口配置近期被修改",
        ),
        Hypothesis(
            "下游计划内维护或限流，返回 503 / 429 并带 Retry-After",
            "响应携带 Retry-After 或维护说明；下游状态页公告维护",
            "响应无 Retry-After，下游状态页正常",
        ),
        Hypothesis(
            "调用方重试策略缺陷（无退避、无上限）放大流量",
            "同一请求短时间内多次立即重试；出站 QPS 显著高于业务流量",
            "重试带指数退避且出站 QPS 与入站一致",
        ),
        Hypothesis(
            "网络或 TLS 层变慢（DNS、TCP 建连、TLS 握手）占满超时预算",
            "日志中连接/握手阶段耗时明显升高，而下游处理耗时正常",
            "建连与握手耗时正常，慢在下游处理阶段",
        ),
    ),
    investigation=(
        "确认受影响接口、下游名称与首次报错时间，区分超时、5xx 与熔断快速失败。",
        "查看调用日志中的阶段耗时（DNS、建连、TLS 握手、读取）与响应码、响应头。",
        "检查熔断器状态变更、失败率与半开探测结果，确认真正失败的下游。",
        "对比出站请求量与入站业务量，判断是否存在重试放大。",
        "核对下游状态页、维护公告与近期变更。",
    ),
    mitigation=(
        "切换到备用通道或降级路径，保持幂等键不变。",
        "对下游维护或限流：遵守 Retry-After，暂停即时重试，改为带抖动的指数退避。",
        "对网络/TLS 问题：联系下游或网络团队，必要时临时调整超时并开启会话复用。",
        "下游恢复后按幂等键有界重放积压请求。",
    ),
    verification="连续 10 分钟下游调用成功率高于 99%、超时率低于 1%，熔断器保持 CLOSED。",
)

RUNBOOK_DATABASE_CONTENTION = Runbook(
    runbook_id="runbook-database-contention",
    title="数据库连接池耗尽与锁等待排查手册",
    applies_to=(
        "获取数据库连接超时（SQLTransientConnectionException、HikariPool 无可用连接）。",
        "锁等待超时或死锁（CannotAcquireLockException、Lock wait timeout exceeded）。",
        "接口延迟升高并伴随 503，连接池 pending 指标上升。",
    ),
    hypotheses=(
        Hypothesis(
            "流量突增超过连接池容量",
            "入站 QPS 明显上升，SQL 单次耗时正常",
            "入站流量平稳",
        ),
        Hypothesis(
            "慢 SQL（缺索引、缺分页、全表扫描）长时间占用连接",
            "慢查询日志出现大量 rows_examined 的语句，耗时与连接占用时间吻合",
            "慢查询日志为空，SQL 平均耗时正常",
        ),
        Hypothesis(
            "数据库实例资源瓶颈（CPU、IO、主从切换）",
            "数据库实例指标异常或有切换事件，所有语句普遍变慢",
            "实例指标正常，只有个别语句慢",
        ),
        Hypothesis(
            "连接泄漏或连接未及时归还（长事务、异常路径未关闭）",
            "连接泄漏检测日志指出某段代码长时间持有连接；活跃连接不随流量下降",
            "连接持有时间短，活跃连接随流量变化",
        ),
        Hypothesis(
            "大事务或批处理长时间持有行锁，与在线更新竞争",
            "存在长时间未提交的事务或批处理任务；锁等待日志指向同一阻塞事务",
            "无长事务，锁等待分散且短暂",
        ),
    ),
    investigation=(
        "确认报错类型：获取连接超时、锁等待超时还是 SQL 执行超时。",
        "查看连接池状态（total/active/idle/waiting）与泄漏检测日志，定位占用连接的代码路径。",
        "查看慢查询日志与锁等待日志，找出持有资源最久的语句或事务。",
        "核对同时间段的批处理任务、发布与配置变更。",
        "对比入站流量，排除单纯流量突增。",
    ),
    mitigation=(
        "终止确认安全的长事务或慢查询，释放连接与行锁。",
        "暂停或拆分批处理任务，改为小批量提交。",
        "回滚引入慢 SQL 的版本；不要只靠扩大连接池掩盖问题。",
        "恢复期间对受影响接口限流，避免排队请求继续堆积。",
    ),
    verification=(
        "连续 10 分钟无获取连接超时与锁等待超时，连接池 pending 接近 0，接口 p95 恢复基线。"
    ),
)

RUNBOOK_CACHE_LATENCY = Runbook(
    runbook_id="runbook-cache-latency",
    title="缓存（Redis）延迟与超时排查手册",
    applies_to=(
        "Redis 命令超时（RedisCommandTimeoutException）或 p99 延迟升高。",
        "依赖缓存的读接口变慢或失败，回源流量上升。",
    ),
    hypotheses=(
        Hypothesis(
            "服务端执行慢命令（KEYS、大范围 SCAN、大集合操作）阻塞单线程",
            "Redis SLOWLOG 出现 O(N) 命令，服务端 CPU 升高",
            "SLOWLOG 无慢命令",
        ),
        Hypothesis(
            "客户端 I/O 线程（事件循环）被阻塞，命令在本地排队",
            "客户端日志显示事件循环阻塞、排队命令数上升，而 Redis 服务端耗时正常",
            "客户端事件循环无阻塞告警",
        ),
        Hypothesis(
            "热 key 或大 value：单个 key 访问集中或体积过大，读取与反序列化耗时高",
            "慢日志集中在同一个 key，value 体积达到 MB 级，客户端反序列化耗时高",
            "慢请求分散在不同 key，value 体积小",
        ),
        Hypothesis(
            "内存不足触发淘汰或持久化 fork 阻塞",
            "内存接近 maxmemory、evicted_keys 上升或有 fork 耗时日志",
            "内存充足，无淘汰与 fork",
        ),
        Hypothesis(
            "网络抖动或主从切换",
            "连接重建、切换事件日志，所有 key 同时变慢",
            "无切换事件，只有部分 key 慢",
        ),
    ),
    investigation=(
        "确认慢请求是否集中在少数 key，记录 key 名与 value 体积。",
        "区分耗时发生在服务端执行、网络还是客户端反序列化/事件循环。",
        "检查 SLOWLOG、内存、淘汰与持久化指标。",
        "核对近期写入该 key 的变更（数据量增长、序列化格式调整）。",
    ),
    mitigation=(
        "对大 value 拆分或改为按需读取，热点 key 增加本地缓存。",
        "把耗时的反序列化移出 I/O 线程。",
        "禁止线上执行 O(N) 命令，必要时临时降级到回源读取并限流。",
    ),
    verification="连续 10 分钟 Redis 命令 p99 低于阈值，读接口错误率低于 1%。",
)

RUNBOOK_CPU_SATURATION = Runbook(
    runbook_id="runbook-cpu-saturation",
    title="应用 CPU 饱和与计算超时排查手册",
    applies_to=(
        "实例 CPU 持续接近满载，接口延迟升高并出现 TimeoutException。",
        "扩容后改善有限，说明单请求计算量异常。",
    ),
    hypotheses=(
        Hypothesis(
            "代码发布引入低效实现",
            "CPU 上升与发布时间对齐，火焰图集中在新代码路径",
            "故障时段无发布",
        ),
        Hypothesis(
            "新规则、配置或数据导致单次计算量剧增（组合爆炸、深度递归、正则回溯）",
            "CPU 上升紧跟某次规则/配置发布；日志显示单请求计算的候选数或耗时异常",
            "近期无规则或配置变更，单请求耗时正常",
        ),
        Hypothesis(
            "流量突增或爬虫",
            "入站 QPS 明显上升，单请求耗时正常",
            "入站流量平稳",
        ),
        Hypothesis(
            "频繁 GC 或内存泄漏导致 CPU 消耗在垃圾回收",
            "GC 日志显示停顿时间与频率显著升高，老年代持续增长",
            "GC 停顿短且稳定",
        ),
    ),
    investigation=(
        "确认 CPU 上升的开始时间，对齐同一时间段的发布、规则与配置变更。",
        "查看单请求计算相关日志（候选数、迭代次数、耗时），找出异常输入或规则。",
        "检查 GC 日志与入站流量，排除 GC 和流量因素。",
    ),
    mitigation=(
        "下线或回滚引起计算量剧增的规则/配置，为计算增加上限与超时保护。",
        "回滚有问题的代码版本；必要时临时扩容止血。",
    ),
    verification="连续 10 分钟 CPU 低于 70%，接口 p95 恢复基线且无计算超时。",
)

RUNBOOK_MESSAGE_CONSUMER_LAG = Runbook(
    runbook_id="runbook-message-consumer-lag",
    title="消息消费积压排查手册",
    applies_to=(
        "Kafka 消费组 lag 持续上升，下游状态更新延迟。",
        "消费者监听器异常（ListenerExecutionFailedException）。",
    ),
    hypotheses=(
        Hypothesis(
            "消费者处理变慢（下游依赖慢、批量过大）",
            "单条处理耗时上升但无错误，offset 缓慢前进",
            "处理耗时正常",
        ),
        Hypothesis(
            "消费者实例减少或频繁 rebalance",
            "rebalance 日志频繁，消费者实例数下降",
            "消费组成员稳定",
        ),
        Hypothesis(
            "毒消息：某条消息无法处理（反序列化失败、数据不兼容），消费者反复重试同一 offset",
            "错误日志反复出现同一 partition/offset；同一时间有生产者 schema 或字段变更",
            "失败 offset 不断前进，错误分散在不同消息",
        ),
        Hypothesis(
            "生产流量突增",
            "生产速率明显上升，消费速率正常",
            "生产速率平稳",
        ),
    ),
    investigation=(
        "确认 lag 集中在哪些 partition，消费 offset 是否停滞。",
        "查看消费错误日志：是否反复失败于同一 offset，失败原因是什么。",
        "核对生产者近期发布与消息 schema 变更。",
        "检查 rebalance 与消费者实例数、处理耗时。",
    ),
    mitigation=(
        "把无法处理的消息转入死信队列并跳过，恢复消费。",
        "升级消费者以兼容新的消息格式，再从死信队列重放。",
        "为消费者配置有限重试与死信策略，避免单条消息阻塞分区。",
    ),
    verification="lag 持续下降并在 30 分钟内回到基线，死信队列消息已处理或有明确处理计划。",
)

RUNBOOK_SEARCH_CLUSTER = Runbook(
    runbook_id="runbook-search-cluster",
    title="搜索集群（Elasticsearch）超时与拒绝排查手册",
    applies_to=(
        "搜索请求超时（TransportException）或返回降级结果。",
        "search 线程池 rejected 上升。",
    ),
    hypotheses=(
        Hypothesis(
            "集群资源问题（节点故障、分片重分配、GC 停顿）",
            "节点离线、分片 relocating/unassigned 或 GC 停顿日志",
            "集群状态 green，节点 GC 正常",
        ),
        Hypothesis(
            "昂贵查询（前导通配符、大范围聚合、深分页）占满 search 线程池",
            "慢查询日志出现 wildcard/regexp/大聚合语句，耗时数秒；线程池 active 满载",
            "慢查询日志为空",
        ),
        Hypothesis(
            "查询流量突增",
            "搜索 QPS 明显上升，单查询耗时正常",
            "搜索 QPS 平稳",
        ),
        Hypothesis(
            "索引写入或合并压力挤占资源",
            "批量写入或 force merge 与故障时间重叠",
            "无大规模写入",
        ),
    ),
    investigation=(
        "确认超时与 rejected 的开始时间及影响的查询类型。",
        "查看慢查询日志，找出耗时最长的查询模式与字段。",
        "检查集群健康、节点 GC、分片状态与写入压力。",
        "对比搜索 QPS，排除流量突增。",
    ),
    mitigation=(
        "在应用层禁止或改写昂贵查询（禁止前导通配符、限制返回数量与超时）。",
        "必要时对搜索接口限流并返回降级结果。",
        "处理节点或分片问题后逐步恢复流量。",
    ),
    verification="连续 10 分钟 search rejected 为 0，搜索 p95 恢复基线。",
)

RUNBOOK_AUTH_TOKEN_VALIDATION = Runbook(
    runbook_id="runbook-auth-token-validation",
    title="鉴权与 Token 验签失败排查手册",
    applies_to=(
        "JWT 验签失败率升高，受保护接口大量返回 401。",
        "新登录或部分用户无法访问，旧会话可能正常。",
    ),
    hypotheses=(
        Hypothesis(
            "服务器时钟漂移导致 exp/nbf 校验失败",
            "错误为 token 过期或尚未生效，且实例时钟与 NTP 偏差大",
            "时钟同步正常",
        ),
        Hypothesis(
            "鉴权配置变更（issuer、audience、算法）",
            "错误为 issuer/audience 不匹配，与配置发布时间对齐",
            "近期无鉴权配置变更",
        ),
        Hypothesis(
            "身份提供方轮换签名 key，本地 JWK 缓存未更新且刷新失败",
            "日志出现未知 kid；JWK 刷新请求失败（网络、DNS、代理、证书错误）",
            "JWK 刷新成功且缓存包含新 kid",
        ),
        Hypothesis(
            "身份提供方自身故障",
            "身份提供方健康检查失败，登录接口同时报错",
            "身份提供方健康，可正常签发 token",
        ),
    ),
    investigation=(
        "确认失败的具体原因：未知 kid、签名无效、过期还是 issuer/audience 不匹配。",
        "若为未知 kid：检查 JWK 刷新日志与刷新请求的网络路径（DNS、出口代理、证书）。",
        "核对身份提供方的 key 轮换公告与本地缓存中的 kid 列表。",
        "检查实例时钟与近期鉴权配置变更。",
    ),
    mitigation=(
        "修复 JWK 刷新的网络路径后强制刷新缓存。",
        "临时手动导入新的公钥，或在确认安全的前提下延长旧 key 的接受窗口。",
        "为 JWK 刷新失败增加告警，避免缓存长期过期。",
    ),
    verification="连续 10 分钟验签失败率低于 0.5%，401 比例恢复基线。",
)

RUNBOOKS: tuple[Runbook, ...] = (
    RUNBOOK_DOWNSTREAM_DEPENDENCY,
    RUNBOOK_DATABASE_CONTENTION,
    RUNBOOK_CACHE_LATENCY,
    RUNBOOK_CPU_SATURATION,
    RUNBOOK_MESSAGE_CONSUMER_LAG,
    RUNBOOK_SEARCH_CLUSTER,
    RUNBOOK_AUTH_TOKEN_VALIDATION,
)


def find_runbook(runbook_id: str) -> Runbook:
    for runbook in RUNBOOKS:
        if runbook.runbook_id == runbook_id:
            return runbook
    raise KeyError(runbook_id)
