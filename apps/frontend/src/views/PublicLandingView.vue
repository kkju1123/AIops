<script setup lang="ts">
import {
  Activity,
  ArrowRight,
  BookOpen,
  Bot,
  Cable,
  CheckCircle2,
  Database,
  GitBranch,
  LockKeyhole,
  MessageSquare,
  Server,
  ShieldCheck,
  Sparkles
} from "lucide-vue-next";

const capabilities = [
  { icon: MessageSquare, title: "Agent 对话", description: "流式回答、会话记忆、Prompt 与 Skill 配置，以及可追溯的工具调用。" },
  { icon: BookOpen, title: "知识检索", description: "文档切分、混合检索、重排与引用展示，回答来源可审查。" },
  { icon: Activity, title: "智能诊断", description: "Plan–Execute–Replan 工作流，汇总告警、真实工具证据和最终报告。" },
  { icon: Cable, title: "MCP 连接", description: "管理真实 MCP Server、发现工具，并保留连接检查与调用审计。" }
] as const;

const architecture = [
  { icon: Bot, label: "Vue 3 + TypeScript", detail: "响应式产品界面与严格类型客户端" },
  { icon: Server, label: "FastAPI", detail: "认证、SSE、业务 API 与后台任务" },
  { icon: GitBranch, label: "LangGraph / LangChain", detail: "可控 Agent 与诊断编排" },
  { icon: Database, label: "SQLite + pgvector", detail: "租户数据、任务状态与向量检索" }
] as const;
</script>

<template>
  <main class="portfolio-view">
    <header class="portfolio-view__nav">
      <RouterLink class="portfolio-view__brand" to="/" aria-label="Super AI 项目首页">
        <Sparkles :size="19" aria-hidden="true" />
        <span>SUPER AI</span>
      </RouterLink>
      <nav aria-label="项目导航">
        <a href="#capabilities">核心能力</a>
        <a href="#architecture">技术架构</a>
        <RouterLink to="/login">所有者登录</RouterLink>
      </nav>
    </header>

    <section class="portfolio-view__hero" aria-labelledby="portfolio-title">
      <div class="portfolio-view__hero-copy">
        <p class="portfolio-view__eyebrow"><span aria-hidden="true"></span>SYSTEM / AIOPS WORKSPACE</p>
        <h1 id="portfolio-title">让 Agent 基于真实证据<br /><em>完成运维诊断</em></h1>
        <p class="portfolio-view__summary">Super AI 是一个本地优先的智能运维工作台，把对话、知识检索、MCP 工具和可解释诊断整合进同一条工作流。</p>
        <div class="portfolio-view__actions">
          <RouterLink class="portfolio-view__primary" to="/drill">进入工作台 · 触发一次故障<ArrowRight :size="17" aria-hidden="true" /></RouterLink>
          <RouterLink class="portfolio-view__secondary" to="/login">所有者登录</RouterLink>
        </div>
        <p class="portfolio-view__safety"><ShieldCheck :size="15" aria-hidden="true" />无需注册：系统为你创建独立的临时访客账号，演练与对话按次数限额；演练日志与指标由故障模拟器生成，凭据始终保留在服务端。</p>
      </div>
      <div class="portfolio-view__terminal" aria-label="项目工作流摘要">
        <header><span>SUPER_AI / PIPELINE</span><small>ONLINE</small></header>
        <ol>
          <li><span>01</span><strong>OBSERVE</strong><small>告警 · 问题 · 上下文</small></li>
          <li><span>02</span><strong>RETRIEVE</strong><small>SOP · 历史案例 · 引用</small></li>
          <li><span>03</span><strong>EXECUTE</strong><small>MCP 工具 · 真实证据</small></li>
          <li><span>04</span><strong>REPORT</strong><small>根因 · 置信度 · 建议</small></li>
        </ol>
        <footer><CheckCircle2 :size="15" aria-hidden="true" />AUTH BOUNDARY PRESERVED</footer>
      </div>
    </section>

    <section id="capabilities" class="portfolio-view__section" aria-labelledby="capabilities-title">
      <header class="portfolio-view__section-heading">
        <p>// PRODUCT MODULES</p>
        <h2 id="capabilities-title">一个工作台，四个完整模块</h2>
      </header>
      <div class="portfolio-view__capabilities">
        <article v-for="(item, index) in capabilities" :key="item.title">
          <span class="portfolio-view__index">0{{ index + 1 }}</span>
          <component :is="item.icon" :size="21" aria-hidden="true" />
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section id="architecture" class="portfolio-view__section portfolio-view__architecture" aria-labelledby="architecture-title">
      <header class="portfolio-view__section-heading">
        <p>// ENGINEERING SYSTEM</p>
        <h2 id="architecture-title">不只是界面原型</h2>
        <span>真实认证、tenant 隔离、持久任务、SSE 和外部工具边界共同组成可运行系统。</span>
      </header>
      <div class="portfolio-view__stack">
        <article v-for="item in architecture" :key="item.label">
          <component :is="item.icon" :size="20" aria-hidden="true" />
          <div><strong>{{ item.label }}</strong><small>{{ item.detail }}</small></div>
        </article>
      </div>
      <div class="portfolio-view__boundary">
        <LockKeyhole :size="22" aria-hidden="true" />
        <div><strong>安全设计是产品的一部分</strong><p>每位访客都有独立的临时账号，只能读取自己触发的演练诊断和只读 SOP 库，不能上传知识、管理 MCP 或查询真实云日志。模型密钥与云凭据始终保留在服务端。</p></div>
      </div>
    </section>

    <footer class="portfolio-view__footer">
      <div><Sparkles :size="17" aria-hidden="true" /><strong>SUPER AI</strong><span>LOCAL-FIRST AIOPS WORKSPACE</span></div>
      <RouterLink to="/drill">进入工作台<ArrowRight :size="15" aria-hidden="true" /></RouterLink>
    </footer>
  </main>
</template>

<style scoped>
.portfolio-view { background: var(--canvas); color: var(--text-primary); min-height: 100vh; overflow: hidden; }
.portfolio-view__nav { align-items: center; background: rgb(5 7 11 / 94%); border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; min-height: 4.25rem; padding: 0 clamp(1rem, 5vw, 4.5rem); position: sticky; top: 0; z-index: 10; }
.portfolio-view__brand { align-items: center; color: var(--text-primary); display: inline-flex; font-size: 0.82rem; font-weight: 850; gap: 0.55rem; letter-spacing: 0.14em; text-decoration: none; }.portfolio-view__brand svg { color: var(--accent); filter: drop-shadow(0 0 7px rgb(0 255 255 / 55%)); }
.portfolio-view__nav nav { align-items: center; display: flex; gap: clamp(0.75rem, 2vw, 1.75rem); }.portfolio-view__nav nav a { color: var(--text-secondary); font-size: 0.68rem; letter-spacing: 0.08em; text-decoration: none; text-transform: uppercase; }.portfolio-view__nav nav a:hover { color: var(--accent); }
.portfolio-view__hero { display: grid; gap: clamp(2rem, 6vw, 6rem); grid-template-columns: minmax(0, 1.05fr) minmax(22rem, 0.95fr); margin: 0 auto; max-width: 88rem; min-height: calc(100vh - 4.25rem); padding: clamp(4rem, 9vw, 8rem) clamp(1.25rem, 5vw, 4.5rem); place-items: center stretch; position: relative; }.portfolio-view__hero::before { background: radial-gradient(circle, rgb(0 255 255 / 11%), transparent 68%); content: ""; height: 34rem; left: -18rem; pointer-events: none; position: absolute; top: 4rem; width: 34rem; }
.portfolio-view__eyebrow { align-items: center; color: var(--accent); display: flex; font-size: 0.67rem; font-weight: 750; gap: 0.55rem; letter-spacing: 0.16em; margin: 0 0 1.5rem; }.portfolio-view__eyebrow span { background: var(--accent); box-shadow: 0 0 10px var(--accent); height: 0.42rem; width: 0.42rem; }
.portfolio-view__hero h1 { font-size: clamp(2.4rem, 5.4vw, 5.7rem); letter-spacing: -0.055em; line-height: 0.98; margin: 0; max-width: 11ch; text-transform: none; }.portfolio-view__hero h1 em { color: var(--accent); font-style: normal; text-shadow: 0 0 18px rgb(0 255 255 / 38%); }.portfolio-view__summary { color: var(--text-secondary); font-size: clamp(0.88rem, 1.25vw, 1.02rem); line-height: 1.85; margin: 1.8rem 0 0; max-width: 40rem; }
.portfolio-view__actions { display: flex; flex-wrap: wrap; gap: 0.8rem; margin-top: 2.1rem; }.portfolio-view__actions a { align-items: center; display: inline-flex; font-size: 0.72rem; font-weight: 800; gap: 0.55rem; letter-spacing: 0.08em; min-height: 2.9rem; padding: 0 1rem; text-decoration: none; text-transform: uppercase; }.portfolio-view__primary { background: var(--accent); border: 1px solid var(--accent); box-shadow: var(--shadow-glow); color: var(--on-accent); }.portfolio-view__primary:hover { box-shadow: 0 0 28px rgb(0 255 255 / 48%); }.portfolio-view__secondary { border: 1px solid var(--accent-border); color: var(--accent); }.portfolio-view__secondary:hover { background: var(--accent-soft); box-shadow: var(--shadow-glow-sm); }
.portfolio-view__safety { align-items: center; color: var(--text-tertiary); display: flex; font-size: 0.66rem; gap: 0.45rem; line-height: 1.5; margin: 1.25rem 0 0; }.portfolio-view__safety svg { color: var(--success); flex: 0 0 auto; }
.portfolio-view__terminal { background: var(--surface-inset); border: 1px solid var(--accent-border); box-shadow: 0 0 30px rgb(0 255 255 / 12%); min-width: 0; position: relative; }.portfolio-view__terminal::after { border-bottom: 1px solid var(--accent); border-right: 1px solid var(--accent); bottom: -0.3rem; content: ""; height: 1.2rem; position: absolute; right: -0.3rem; width: 1.2rem; }.portfolio-view__terminal header, .portfolio-view__terminal footer { align-items: center; display: flex; font-size: 0.63rem; justify-content: space-between; letter-spacing: 0.1em; min-height: 3rem; padding: 0 1rem; }.portfolio-view__terminal header { border-bottom: 1px solid var(--line); color: var(--accent); }.portfolio-view__terminal header small { color: var(--success); }.portfolio-view__terminal ol { list-style: none; margin: 0; padding: 0.8rem 1rem; }.portfolio-view__terminal li { align-items: center; border-bottom: 1px solid var(--line); display: grid; gap: 0.75rem; grid-template-columns: 2.3rem minmax(0, 0.7fr) minmax(0, 1fr); min-height: 4.35rem; }.portfolio-view__terminal li:last-child { border-bottom: 0; }.portfolio-view__terminal li > span { color: var(--accent-ink); font-size: 0.68rem; }.portfolio-view__terminal li strong { font-size: 0.78rem; letter-spacing: 0.09em; }.portfolio-view__terminal li small { color: var(--text-tertiary); font-size: 0.68rem; line-height: 1.45; }.portfolio-view__terminal footer { border-top: 1px solid var(--line); color: var(--success); justify-content: flex-start; gap: 0.45rem; }
.portfolio-view__section { margin: 0 auto; max-width: 88rem; padding: clamp(4rem, 8vw, 7rem) clamp(1.25rem, 5vw, 4.5rem); }.portfolio-view__section-heading { max-width: 50rem; }.portfolio-view__section-heading > p { color: var(--accent-ink); font-size: 0.67rem; font-weight: 750; letter-spacing: 0.14em; margin: 0 0 0.8rem; }.portfolio-view__section-heading h2 { font-size: clamp(1.6rem, 3vw, 2.75rem); letter-spacing: -0.025em; margin: 0; text-transform: none; }.portfolio-view__section-heading > span { color: var(--text-secondary); display: block; font-size: 0.82rem; line-height: 1.75; margin-top: 0.85rem; }
.portfolio-view__capabilities { border-left: 1px solid var(--line); border-top: 1px solid var(--line); display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 2.5rem; }.portfolio-view__capabilities article { border-bottom: 1px solid var(--line); border-right: 1px solid var(--line); min-height: 15rem; padding: 1.35rem; position: relative; transition: background var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast); }.portfolio-view__capabilities article:hover { background: var(--accent-soft); border-color: var(--accent-border); box-shadow: inset 0 0 22px rgb(0 255 255 / 5%); }.portfolio-view__index { color: var(--text-tertiary); font-size: 0.62rem; position: absolute; right: 1rem; top: 1rem; }.portfolio-view__capabilities svg { color: var(--accent); margin-top: 2.1rem; }.portfolio-view__capabilities h3 { font-size: 0.9rem; margin: 1.15rem 0 0; }.portfolio-view__capabilities p { color: var(--text-secondary); font-size: 0.72rem; line-height: 1.75; margin: 0.7rem 0 0; }
.portfolio-view__architecture { display: grid; gap: 3rem; grid-template-columns: minmax(16rem, 0.7fr) minmax(24rem, 1.3fr); }.portfolio-view__stack { border-top: 1px solid var(--line); }.portfolio-view__stack article { align-items: center; border-bottom: 1px solid var(--line); display: grid; gap: 0.85rem; grid-template-columns: auto minmax(0, 1fr); min-height: 4.6rem; padding: 0 0.8rem; }.portfolio-view__stack svg { color: var(--accent); }.portfolio-view__stack strong, .portfolio-view__stack small { display: block; }.portfolio-view__stack strong { font-size: 0.76rem; }.portfolio-view__stack small { color: var(--text-tertiary); font-size: 0.66rem; margin-top: 0.2rem; }.portfolio-view__boundary { align-items: start; border: 1px solid var(--status-success-border); display: grid; gap: 0.9rem; grid-column: 1 / -1; grid-template-columns: auto minmax(0, 1fr); padding: 1rem; }.portfolio-view__boundary svg { color: var(--success); }.portfolio-view__boundary strong { color: var(--status-success-text); font-size: 0.78rem; }.portfolio-view__boundary p { color: var(--text-secondary); font-size: 0.7rem; line-height: 1.7; margin: 0.3rem 0 0; }
.portfolio-view__footer { align-items: center; border-top: 1px solid var(--line); display: flex; justify-content: space-between; margin: 0 auto; max-width: 88rem; min-height: 7rem; padding: 1rem clamp(1.25rem, 5vw, 4.5rem); }.portfolio-view__footer > div { align-items: center; display: flex; gap: 0.55rem; }.portfolio-view__footer svg { color: var(--accent); }.portfolio-view__footer strong { font-size: 0.74rem; letter-spacing: 0.12em; }.portfolio-view__footer span { color: var(--text-tertiary); font-size: 0.6rem; }.portfolio-view__footer > a { align-items: center; color: var(--accent); display: inline-flex; font-size: 0.68rem; gap: 0.35rem; text-decoration: none; }
@media (max-width: 900px) { .portfolio-view__hero { grid-template-columns: minmax(0, 1fr); }.portfolio-view__hero h1 { max-width: 13ch; }.portfolio-view__terminal { max-width: 44rem; }.portfolio-view__capabilities { grid-template-columns: repeat(2, minmax(0, 1fr)); }.portfolio-view__architecture { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 620px) { .portfolio-view__nav nav a:not(:last-child) { display: none; }.portfolio-view__hero { min-height: auto; padding-top: 4.5rem; }.portfolio-view__hero h1 { font-size: clamp(2.2rem, 13vw, 3.8rem); }.portfolio-view__terminal li { grid-template-columns: 2rem minmax(0, 1fr); padding: 0.65rem 0; }.portfolio-view__terminal li small { grid-column: 2; }.portfolio-view__capabilities { grid-template-columns: minmax(0, 1fr); }.portfolio-view__capabilities article { min-height: 12rem; }.portfolio-view__footer span { display: none; } }
</style>
