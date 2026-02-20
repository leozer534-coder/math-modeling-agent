<script setup lang="ts">
import { QQ_GROUP, TWITTER, DISCORD } from "@/utils/const";
import {
  ArrowRight,
  Brain,
  Code,
  FileText,
  Layers,
  PenTool,
  Sigma,
  Sparkles,
  Twitter,
  Users,
  Zap,
  Shield,
  BarChart3,
  MessageCircle,
  ChevronDown,
  Play,
  Search,
  FlaskConical,
  CheckCircle,
  Target,
  Lightbulb,
  Eye,
  Award,
  UserCog,
} from "lucide-vue-next";
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

/** 滚动淡入动画 */
const observerRef = ref<IntersectionObserver | null>(null);

onMounted(() => {
  observerRef.value = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }
      }
    },
    { threshold: 0.15, rootMargin: "0px 0px -60px 0px" }
  );

  const elements = document.querySelectorAll(".fade-in-up");
  for (const el of elements) {
    observerRef.value.observe(el);
  }
});

onUnmounted(() => {
  observerRef.value?.disconnect();
});

/** 智能体分组 */
const agentGroups = [
  {
    title: "核心流程",
    agents: [
      { icon: Zap, name: "Coordinator", label: "协调器", desc: "智能拆解题目，统筹全局流程", color: "#8b5cf6" },
      { icon: Brain, name: "Modeler", label: "建模手", desc: "构建数学模型，设计求解方案", color: "#3b82f6" },
      { icon: Code, name: "Coder", label: "代码手", desc: "编写代码运行，自动调试优化", color: "#22c55e" },
      { icon: PenTool, name: "Writer", label: "论文手", desc: "生成规范论文，符合竞赛标准", color: "#f97316" },
    ],
  },
  {
    title: "深度分析",
    agents: [
      { icon: Search, name: "ProblemAnalyzer", label: "问题分析", desc: "深度理解题目，结构化分析", color: "#ec4899" },
      { icon: Eye, name: "InsightAnalyzer", label: "洞察分析", desc: "透过表象，发现问题本质", color: "#14b8a6" },
      { icon: BarChart3, name: "DataExpert", label: "数据理解", desc: "全方位数据质量与特征分析", color: "#f59e0b" },
    ],
  },
  {
    title: "智能建模",
    agents: [
      { icon: Target, name: "ModelSelector", label: "模型选择", desc: "30+ 模型知识库，智能推荐", color: "#6366f1" },
      { icon: Lightbulb, name: "SmartModeler", label: "创新建模", desc: "模型改进与方法论创新", color: "#10b981" },
      { icon: FlaskConical, name: "ExperimentDesigner", label: "实验设计", desc: "科学实验方案与验证策略", color: "#8b5cf6" },
    ],
  },
  {
    title: "质量保障",
    agents: [
      { icon: Award, name: "AbstractGenerator", label: "摘要生成", desc: "竞赛级高质量摘要撰写", color: "#f97316" },
      { icon: CheckCircle, name: "ValidationExpert", label: "验证专家", desc: "模型性能与结果可靠性验证", color: "#22c55e" },
      { icon: Shield, name: "Reviewer", label: "质量评审", desc: "模拟评委，多维度论文评审", color: "#ef4444" },
      { icon: UserCog, name: "InteractiveCoord", label: "交互协调", desc: "渐进式分析，支持人机协作", color: "#0ea5e9" },
    ],
  },
];

/** 核心特性 */
const features = [
  {
    icon: Sparkles,
    title: "全自动建模",
    desc: "从题目分析到论文产出，全流程 AI 驱动，零人工干预",
  },
  {
    icon: Layers,
    title: "多模型兼容",
    desc: "OpenAI、Claude、DeepSeek 等主流 LLM，自由切换",
  },
  {
    icon: FileText,
    title: "竞赛级论文",
    desc: "Markdown / LaTeX 自动排版，国赛美赛模板一键切换",
  },
  {
    icon: Shield,
    title: "安全执行",
    desc: "沙箱隔离运行代码，数据安全可控",
  },
  {
    icon: BarChart3,
    title: "效率革命",
    desc: "传统 72 小时压缩至 1 小时，效率提升 70 倍",
  },
  {
    icon: Brain,
    title: "深度质量保障",
    desc: "验证专家 + 评审专家，多维度保障产出质量",
  },
];

/** 社交链接 */
const socialLinks = [
  { href: TWITTER, icon: Twitter, label: "Twitter" },
  { href: DISCORD, icon: MessageCircle, label: "Discord" },
];
</script>

<template>
  <div class="apple-landing">
    <!-- 导航栏 -->
    <nav class="nav-bar">
      <div class="nav-inner">
        <button class="nav-logo" @click="router.push('/')">
          <div class="logo-icon">
            <Sigma class="w-4 h-4 text-white" />
          </div>
          <span class="logo-text">MathModelAgent</span>
        </button>
        <div class="nav-actions">
          <button class="nav-link" @click="router.push('/login')">登录</button>
          <button class="nav-cta" @click="router.push('/chat')">
            开始使用
          </button>
        </div>
      </div>
    </nav>

    <!-- ═══════════ Section 1: Hero ═══════════ -->
    <section class="hero-section">
      <div class="hero-glow" />

      <div class="hero-content">
        <p class="hero-eyebrow fade-in-up">数学建模 · 多智能体 · 全自动</p>
        <h1 class="hero-title fade-in-up">
          <span class="hero-title-line">数学建模竞赛的</span>
          <span class="hero-title-gradient">AI 超级助手</span>
        </h1>
        <p class="hero-subtitle fade-in-up">
          多智能体协作，从题目分析到论文产出，一键完成。
        </p>

        <div class="hero-buttons fade-in-up">
          <button class="btn-primary" @click="router.push('/chat')">
            <Play class="w-4 h-4" />
            立即体验
          </button>
          <button class="btn-secondary" @click="router.push('/login')">
            了解更多
            <ArrowRight class="w-4 h-4" />
          </button>
        </div>

        <div class="scroll-hint fade-in-up">
          <ChevronDown class="w-5 h-5 animate-bounce" />
        </div>
      </div>
    </section>

    <!-- ═══════════ Section 2: 数据指标 ═══════════ -->
    <section class="stats-section">
      <div class="stats-grid fade-in-up">
        <div class="stat-item">
          <span class="stat-number">70×</span>
          <span class="stat-label">效率提升</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-number">20+</span>
          <span class="stat-label">专业智能体</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-number">4</span>
          <span class="stat-label">智能体分组</span>
        </div>
      </div>
    </section>

    <!-- ═══════════ Section 3: 多智能体 ═══════════ -->
    <section class="agents-section">
      <div class="section-inner">
        <h2 class="section-title fade-in-up">
          20+ 智能体<br />
          <span class="text-gradient">协作无间</span>
        </h2>
        <p class="section-desc fade-in-up">
          从问题分析到论文评审，覆盖建模全流程的专业智能体团队。
        </p>

        <div
          v-for="group in agentGroups"
          :key="group.title"
          class="agent-group fade-in-up"
        >
          <h3 class="group-title">{{ group.title }}</h3>
          <div class="agents-grid" :class="{ 'agents-grid-3': group.agents.length === 3 }">
            <div
              v-for="agent in group.agents"
              :key="agent.name"
              class="agent-card"
              :style="{ '--accent': agent.color }"
            >
              <div class="agent-icon">
                <component :is="agent.icon" class="w-6 h-6" />
              </div>
              <div class="agent-info">
                <h3 class="agent-label">{{ agent.label }}</h3>
                <p class="agent-name">{{ agent.name }}</p>
              </div>
              <p class="agent-desc">{{ agent.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════ Section 4: 工作流程 ═══════════ -->
    <section class="workflow-section">
      <div class="section-inner">
        <h2 class="section-title fade-in-up">
          四步完成建模
        </h2>
        <p class="section-desc fade-in-up">
          极简操作，AI 完成剩余全部工作。
        </p>

        <div class="workflow-steps fade-in-up">
          <div class="workflow-step" v-for="(step, i) in [
            { num: '01', title: '上传题目', desc: '粘贴题目文本，上传附件数据' },
            { num: '02', title: '智能建模', desc: '多 Agent 协作分析，构建模型' },
            { num: '03', title: '代码求解', desc: '自动编写代码，运行计算优化' },
            { num: '04', title: '论文输出', desc: '生成竞赛标准的完整论文' },
          ]" :key="step.num">
            <span class="step-num">{{ step.num }}</span>
            <h3 class="step-title">{{ step.title }}</h3>
            <p class="step-desc">{{ step.desc }}</p>
            <div v-if="i < 3" class="step-connector" />
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════ Section 5: 核心特性 ═══════════ -->
    <section class="features-section">
      <div class="section-inner">
        <h2 class="section-title fade-in-up">
          为什么选择<br />
          <span class="text-gradient">MathModelAgent</span>
        </h2>

        <div class="features-grid fade-in-up">
          <div
            v-for="feature in features"
            :key="feature.title"
            class="feature-card"
          >
            <div class="feature-icon">
              <component :is="feature.icon" class="w-5 h-5" />
            </div>
            <h3 class="feature-title">{{ feature.title }}</h3>
            <p class="feature-desc">{{ feature.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════ Section 6: CTA ═══════════ -->
    <section class="cta-section">
      <div class="cta-glow" />
      <div class="cta-content fade-in-up">
        <h2 class="cta-title">
          准备好开启<br />
          AI 建模之旅了吗
        </h2>
        <p class="cta-desc">
          无论国赛还是美赛，一键生成高质量建模解决方案。
        </p>
        <div class="cta-buttons">
          <button class="btn-primary btn-large" @click="router.push('/chat')">
            免费开始使用
            <ArrowRight class="w-5 h-5" />
          </button>
          <button class="btn-ghost" @click="router.push('/login')">
            注册账号
          </button>
        </div>
      </div>
    </section>

    <!-- ═══════════ Footer ═══════════ -->
    <footer class="site-footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <div class="logo-icon logo-icon-sm">
            <Sigma class="w-3.5 h-3.5 text-white" />
          </div>
          <span>MathModelAgent</span>
        </div>
        <div class="footer-links">
          <a
            v-for="link in socialLinks"
            :key="link.label"
            :href="link.href"
            target="_blank"
            rel="noopener noreferrer"
            :title="link.label"
            class="footer-link"
          >
            <component :is="link.icon" class="w-4 h-4" />
          </a>
          <a :href="QQ_GROUP" target="_blank" rel="noopener noreferrer" title="QQ群" class="footer-link">
            <Users class="w-4 h-4" />
          </a>
        </div>
      </div>
      <div class="footer-copy">
        <p>© 2025 MathModelAgent · 数学建模智能体</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* ────────────────────────────────────────────
   苹果风格设计系统 — 白色主题
   ──────────────────────────────────────────── */

.apple-landing {
  --color-bg: #ffffff;
  --color-bg-alt: #f5f5f7;
  --color-text: #1d1d1f;
  --color-text-secondary: #6e6e73;
  --color-border: rgba(0, 0, 0, 0.06);
  --color-card: #ffffff;
  --brand-start: #a855f7;
  --brand-mid: #7c3aed;
  --brand-end: #6d28d9;
  --brand-glow: rgba(139, 92, 246, 0.12);

  background: var(--color-bg);
  color: var(--color-text);
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text',
    'Helvetica Neue', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
}

/* 滚动淡入动画 */
.fade-in-up {
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              transform 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.fade-in-up.visible {
  opacity: 1;
  transform: translateY(0);
}

/* 渐变文字 */
.text-gradient {
  background: linear-gradient(135deg, var(--brand-start), var(--brand-end));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.hero-title-gradient {
  background: linear-gradient(135deg, var(--brand-start), var(--brand-mid), var(--brand-end));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

/* ═══════════ 导航栏 ═══════════ */
.nav-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 0.5px solid var(--color-border);
}
.nav-inner {
  max-width: 1024px;
  margin: 0 auto;
  padding: 0 24px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.nav-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text);
}
.logo-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--brand-start), var(--brand-end));
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo-icon-sm {
  width: 24px;
  height: 24px;
  border-radius: 6px;
}
.logo-text {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.nav-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}
.nav-link {
  font-size: 12px;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color 0.2s;
  cursor: pointer;
  background: none;
  border: none;
  display: flex;
  align-items: center;
}
.nav-link:hover {
  color: var(--color-text);
}
.nav-cta {
  font-size: 12px;
  padding: 6px 16px;
  border-radius: 980px;
  background: linear-gradient(135deg, var(--brand-start), var(--brand-end));
  color: white;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: opacity 0.2s;
}
.nav-cta:hover {
  opacity: 0.85;
}

/* ═══════════ Hero ═══════════ */
.hero-section {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  overflow: hidden;
  background: var(--color-bg);
}
.hero-glow {
  position: absolute;
  top: -200px;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  height: 600px;
  background: radial-gradient(ellipse, var(--brand-glow), transparent 70%);
  pointer-events: none;
}
.hero-content {
  text-align: center;
  max-width: 820px;
  position: relative;
}
.hero-eyebrow {
  font-size: 16px;
  letter-spacing: 0.04em;
  color: var(--color-text-secondary);
  margin-bottom: 24px;
  font-weight: 500;
}
.hero-title {
  font-size: clamp(48px, 8vw, 80px);
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.025em;
  margin-bottom: 24px;
  color: var(--color-text);
}
.hero-title-line {
  display: block;
}
.hero-subtitle {
  font-size: clamp(18px, 2.5vw, 24px);
  color: var(--color-text-secondary);
  font-weight: 400;
  line-height: 1.5;
  max-width: 600px;
  margin: 0 auto 48px;
}
.hero-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}
.scroll-hint {
  position: absolute;
  bottom: -80px;
  left: 50%;
  transform: translateX(-50%);
  color: var(--color-text-secondary);
}

/* ═══════════ 按钮系统 ═══════════ */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  border-radius: 980px;
  background: linear-gradient(135deg, var(--brand-start), var(--brand-end));
  color: white;
  font-size: 16px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
}
.btn-primary:hover {
  transform: scale(1.03);
  box-shadow: 0 8px 30px var(--brand-glow);
}
.btn-primary.btn-large {
  padding: 18px 36px;
  font-size: 18px;
}
.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  border-radius: 980px;
  background: transparent;
  color: var(--color-text);
  font-size: 16px;
  font-weight: 500;
  border: 1px solid rgba(0, 0, 0, 0.12);
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
}
.btn-secondary:hover {
  background: rgba(0, 0, 0, 0.04);
  border-color: rgba(0, 0, 0, 0.2);
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 18px 36px;
  border-radius: 980px;
  background: transparent;
  color: var(--brand-start);
  font-size: 18px;
  font-weight: 500;
  border: 1.5px solid rgba(168, 85, 247, 0.25);
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
}
.btn-ghost:hover {
  background: rgba(168, 85, 247, 0.06);
  border-color: rgba(168, 85, 247, 0.4);
}

/* ═══════════ Stats ═══════════ */
.stats-section {
  padding: 100px 24px;
  background: var(--color-bg-alt);
}
.stats-grid {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 48px;
}
.stat-item {
  text-align: center;
}
.stat-number {
  display: block;
  font-size: clamp(48px, 6vw, 64px);
  font-weight: 700;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, var(--brand-start), var(--brand-end));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.stat-label {
  display: block;
  font-size: 15px;
  color: var(--color-text-secondary);
  margin-top: 8px;
  font-weight: 500;
}
.stat-divider {
  width: 1px;
  height: 64px;
  background: rgba(0, 0, 0, 0.08);
}

/* ═══════════ Section 通用 ═══════════ */
.section-inner {
  max-width: 1024px;
  margin: 0 auto;
  padding: 0 24px;
}
.section-title {
  font-size: clamp(36px, 5vw, 56px);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.025em;
  text-align: center;
  margin-bottom: 16px;
  color: var(--color-text);
}
.section-desc {
  font-size: 18px;
  color: var(--color-text-secondary);
  text-align: center;
  margin-bottom: 64px;
  font-weight: 400;
}

/* ═══════════ Agents ═══════════ */
.agents-section {
  padding: 140px 24px;
  background: var(--color-bg);
}
.agent-group {
  margin-bottom: 48px;
}
.agent-group:last-child {
  margin-bottom: 0;
}
.group-title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-text-secondary);
  margin-bottom: 20px;
  padding-left: 4px;
}
.agents-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}
.agents-grid-3 {
  grid-template-columns: repeat(3, 1fr);
}
@media (max-width: 768px) {
  .agents-grid,
  .agents-grid-3 {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 480px) {
  .agents-grid,
  .agents-grid-3 {
    grid-template-columns: 1fr;
  }
}
.agent-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  padding: 32px 24px;
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
  overflow: hidden;
}
.agent-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0;
  transition: opacity 0.4s;
}
.agent-card:hover {
  border-color: rgba(0, 0, 0, 0.1);
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.06);
}
.agent-card:hover::before {
  opacity: 1;
}
.agent-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  color: var(--accent);
  transition: background 0.3s;
}
.agent-card:hover .agent-icon {
  background: color-mix(in srgb, var(--accent) 15%, transparent);
}
.agent-info {
  margin-bottom: 12px;
}
.agent-label {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--color-text);
}
.agent-name {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}
.agent-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

/* ═══════════ Workflow ═══════════ */
.workflow-section {
  padding: 140px 24px;
  background: var(--color-bg-alt);
}
.workflow-steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  position: relative;
}
@media (max-width: 768px) {
  .workflow-steps {
    grid-template-columns: 1fr;
    gap: 32px;
  }
  .step-connector {
    display: none;
  }
}
.workflow-step {
  text-align: center;
  padding: 0 24px;
  position: relative;
}
.step-num {
  font-size: 56px;
  font-weight: 800;
  background: linear-gradient(180deg, rgba(168, 85, 247, 0.18), rgba(168, 85, 247, 0.04));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  line-height: 1;
  display: block;
  margin-bottom: 16px;
}
.step-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  letter-spacing: -0.01em;
  color: var(--color-text);
}
.step-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
.step-connector {
  position: absolute;
  right: -16px;
  top: 36px;
  width: 32px;
  height: 1px;
  background: linear-gradient(90deg, rgba(168, 85, 247, 0.25), rgba(168, 85, 247, 0.05));
}

/* ═══════════ Features ═══════════ */
.features-section {
  padding: 140px 24px;
  background: var(--color-bg);
}
.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
@media (max-width: 768px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 480px) {
  .features-grid {
    grid-template-columns: 1fr;
  }
}
.feature-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  padding: 32px;
  transition: all 0.4s;
}
.feature-card:hover {
  border-color: rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.06);
}
.feature-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.1), rgba(109, 40, 217, 0.1));
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  color: var(--brand-start);
}
.feature-title {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin-bottom: 8px;
  color: var(--color-text);
}
.feature-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* ═══════════ CTA ═══════════ */
.cta-section {
  position: relative;
  padding: 160px 24px;
  background: var(--color-bg-alt);
  overflow: hidden;
}
.cta-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 800px;
  height: 600px;
  background: radial-gradient(ellipse, var(--brand-glow), transparent 70%);
  pointer-events: none;
  opacity: 0.6;
}
.cta-content {
  position: relative;
  text-align: center;
}
.cta-title {
  font-size: clamp(40px, 6vw, 64px);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.025em;
  margin-bottom: 20px;
  color: var(--color-text);
}
.cta-desc {
  font-size: 18px;
  color: var(--color-text-secondary);
  margin-bottom: 48px;
}
.cta-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

/* ═══════════ Footer ═══════════ */
.site-footer {
  background: var(--color-bg);
  border-top: 0.5px solid var(--color-border);
  padding: 32px 24px 24px;
}
.footer-inner {
  max-width: 1024px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.footer-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}
.footer-links {
  display: flex;
  gap: 8px;
}
.footer-link {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  transition: all 0.2s;
  text-decoration: none;
}
.footer-link:hover {
  color: var(--color-text);
  background: rgba(0, 0, 0, 0.04);
}
.footer-copy {
  max-width: 1024px;
  margin: 20px auto 0;
  padding-top: 20px;
  border-top: 0.5px solid var(--color-border);
  text-align: center;
  font-size: 12px;
  color: var(--color-text-secondary);
  opacity: 0.6;
}

/* ═══════════ 平滑滚动 ═══════════ */
@media (prefers-reduced-motion: no-preference) {
  html {
    scroll-behavior: smooth;
  }
}

/* ═══════════ 移动端适配 ═══════════ */
@media (max-width: 640px) {
  .nav-inner {
    padding: 0 16px;
  }
  .hero-buttons {
    flex-direction: column;
    align-items: center;
  }
  .stats-grid {
    flex-direction: column;
    gap: 32px;
  }
  .stat-divider {
    width: 64px;
    height: 1px;
  }
  .cta-buttons {
    flex-direction: column;
    align-items: center;
  }
}
</style>
