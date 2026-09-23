<script setup lang="ts">
import { ref, nextTick, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import {
  ArrowLeft,
  Promotion,
  Download,
  Refresh,
  Plus,
  Loading,
  ChatDotRound,
  Edit,
  Monitor,
  DataAnalysis,
  Reading,
  MagicStick,
  ArrowDown,
  ArrowRight,
  Search,
} from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { useUserStore } from "@/pinia";
import katex from "katex";

defineOptions({ name: "CourseChat" });

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const courseId = computed(() => route.params.courseId as string);
const courseName = (route.query.name as string) || t("_courseChat.courseChat");

// ── Types ─────────────────────────────────────────────

interface Skill {
  key: string;
  displayName: string;
  icon: any;
}

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: string;
  /** 思考阶段数据 */
  thinking?: ThinkingData;
  /** 错误详情（仅错误消息使用） */
  errorDetail?: string;
  /** 用户反馈 */
  _liked?: boolean;
  _disliked?: boolean;
}

interface MemoryItem {
  topic: string;
  mastery: number;
}

interface ThinkingData {
  expanded: boolean;
  steps: ThinkingStep[];
  retrievalInfo: string;
  model: string;
  systemPrompt: string;
  memorySummary?: string;
  memoryPrompt?: string;
  memoryDetail?: MemoryItem[];
}

interface ThinkingStep {
  phase: string;
  message: string;
  retrievalCount?: number;
  retrievals?: RetrievalItem[];
  memorySummary?: string;
  memoryDetail?: MemoryItem[];
}

interface RetrievalItem {
  source: string;
  preview: string;
  relevance: string;
}

interface Session {
  id: number;
  title: string;
  updatedAt: string;
}

// ── State ─────────────────────────────────────────────

const skills: Skill[] = [
  { key: "qa", displayName: t("_courseChat.smartQA"), icon: ChatDotRound },
  { key: "formula", displayName: t("_courseChat.formulaDerivation"), icon: Edit },
  { key: "code_debug", displayName: t("_courseChat.codeDebugging"), icon: Monitor },
  { key: "lab_guide", displayName: t("_courseChat.labGuidance"), icon: DataAnalysis },
  { key: "paper_reader", displayName: t("_courseChat.paperReading"), icon: Reading },
];

const activeSkill = ref("qa");
const sessions = ref<Session[]>([]);
const activeSession = ref(0);
const inputText = ref("");
const isStreaming = ref(false);
const messages = ref<Message[]>([]);
const messagesRef = ref<HTMLElement>();
const currentThinking = ref<ThinkingData | null>(null);

// ── API base ──────────────────────────────────────────

const API_PREFIX = "/api";

// ── Sessions ──────────────────────────────────────────

const loadSessions = async () => {
  if (!courseId.value) return;
  try {
    const res = await apiFetch(`${API_PREFIX}/course/${courseId.value}/chat/sessions`);
    if (res.ok) {
      const json = await res.json();
      if (json.data) {
        sessions.value = (json.data || []).map((s: any) => ({
          id: s.id,
          title: s.title,
          updatedAt: s.updated_at
            ? new Date(s.updated_at).toLocaleString("zh-CN", {
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
              })
            : "",
        }));
      }
    }
  } catch {
    /* 401 已由 apiFetch 处理跳转，其余静默 */
  }
};

/** 创建会话，title 默认用用户第一句话 */
const createSession = async (title?: string): Promise<boolean> => {
  if (!courseId.value) return false;
  const skill = activeSkill.value;
  const sessionTitle = title || t("_courseChat.newSession");
  try {
    const res = await apiFetch(`${API_PREFIX}/course/${courseId.value}/chat/sessions`, {
      method: "POST",
      body: JSON.stringify({ course_id: Number(courseId.value), title: sessionTitle, skill }),
    });
    if (res.ok) {
      const json = await res.json();
      if (json.data) {
        sessions.value.unshift(json.data);
        activeSession.value = json.data.id;
        messages.value = [];
        currentThinking.value = null;
        return true;
      }
    }
    // HTTP 非 2xx 且非 401（apiFetch 已拦截 401）
    const errJson = await res.json().catch(() => ({}));
    ElMessage.error((errJson as any).message || t("_courseChat.createSessionFailed"));
    return false;
  } catch (err: any) {
    // 401 跳转已由 apiFetch 处理
    if (!String(err.message).includes(t("_courseChat.loginExpired"))) {
      ElMessage.error(t("_courseChat.createSessionNetworkError"));
    }
    return false;
  }
};

const loadMessages = async (sessionId: number) => {
  try {
    const res = await apiFetch(`${API_PREFIX}/course/${courseId.value}/chat/sessions/${sessionId}/messages`);
    if (res.ok) {
      const json = await res.json();
      if (json.data) {
        messages.value = json.data.map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: formatTime(m.created_at),
          sources: m.sources,
        }));
      }
    }
  } catch {
    /* 401 已由 apiFetch 处理跳转，其余静默 */
  }
};

const switchSession = (id: number) => {
  if (isStreaming.value) return;
  activeSession.value = id;
  currentThinking.value = null;
  loadMessages(id);
};

/** 新建空白对话：清空当前状态，等用户发送第一条消息时自动创建 */
const newSession = () => {
  if (isStreaming.value) return;
  activeSession.value = 0;
  messages.value = [];
  currentThinking.value = null;
  ElMessage.success(t("_courseChat.sessionCreated"));
};

// ── Auth helper ───────────────────────────────────────

const authHeaders = (): Record<string, string> => {
  const token = userStore.accessToken || "";
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
};

/** 统一的 fetch 封装：自动处理 401 跳转登录 */
const apiFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...((options.headers as Record<string, string>) || {}) },
  });
  if (res.status === 401) {
    // token 过期：清除登录态并跳转
    await userStore.logout();
    router.push("/login");
    throw new Error(t("_courseChat.loginExpired"));
  }
  return res;
};

// ── Format ────────────────────────────────────────────

const formatTime = (ts: string) => {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
};

/** 把后端错误信息转为用户可读的简短提示 */
const cleanError = (msg: string): { summary: string; detail: string } => {
  if (!msg) return { summary: t("_courseChat.unknownError"), detail: "" };

  // ── 1. 检测 HTML 错误页（DeepSeek / 反向代理 等） ──
  if (/<html|<body|<div|<style/i.test(msg)) {
    // 去掉 <style>/<script>/<head> 整块
    const text = msg
      .replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/<head[\s\S]*?<\/head>/gi, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/&#?\w+;/g, "")
      .replace(/\s+/g, " ")
      .trim();

    // 提取 Event ID
    const evtMatch = text.match(/Event\s*ID:\s*(\S+)/i);
    const eventId = evtMatch ? evtMatch[1] : "";

    if (/request\s*blocked/i.test(text) || /blocked/i.test(text)) {
      return {
        summary: eventId ? t("_courseChat.requestBlockedWithEvent", { eventId }) : t("_courseChat.requestBlocked"),
        detail: t("_courseChat.checkAgentApiConfig"),
      };
    }
    // 提取 <title> 内容
    const titleMatch = msg.match(/<title>([^<]*)<\/title>/i);
    const title = titleMatch ? titleMatch[1].trim() : "";
    const short = text.slice(0, 200).trim();
    return {
      summary: title || t("_courseChat.serverErrorResponse"),
      detail: short || t("_courseChat.checkAgentApiConfigBrief"),
    };
  }

  // ── 2. 检测 Django 调试页（You cannot call this / django） ──
  if (/django|traceback|you cannot call this|settings\.py|wsgi/i.test(msg)) {
    // 提取异常类名和描述
    const excMatch = msg.match(/(\w+(?:Error|Exception|Warning))(?:\s*:\s*|\s+at\s+|\s*\n\s*)(.+?)(?:\n|\.\s|$)/i);
    if (excMatch) {
      return { summary: excMatch[1], detail: excMatch[2].trim().slice(0, 300) };
    }
    return {
      summary: t("_courseChat.serverProcessingError"),
      detail: t("_courseChat.serverInternalErrorHint"),
    };
  }

  // ── 3. 检测 JSON（可能是 API 返回的结构化错误） ──
  try {
    const obj = JSON.parse(msg);
    const errMsg = obj.message || obj.error || obj.detail || "";
    const errCode = obj.code || obj.status || "";
    return {
      summary: errCode ? `${errCode}：${errMsg}`.trim() : errMsg || t("_courseChat.apiCallError"),
      detail: errMsg || JSON.stringify(obj).slice(0, 300),
    };
  } catch {
    /* not JSON */
  }

  // ── 4. 普通文本错误（包含中文/英文异常信息） ──
  const clean = msg.replace(/\s+/g, " ").trim();
  if (clean.length > 200) {
    return { summary: clean.slice(0, 200) + "...", detail: clean };
  }
  return { summary: clean, detail: clean };
};

// ── Send Message ──────────────────────────────────────

const sendMessage = async () => {
  const text = inputText.value.trim();
  if (!text || isStreaming.value) return;
  if (!activeSession.value) {
    const ok = await createSession(text); // 用第一句话做会话标题
    if (!ok) return; // 错误提示已在 createSession 中显示
  }

  const userMsg: Message = {
    id: Date.now(),
    role: "user",
    content: text,
    timestamp: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
  };
  messages.value.push(userMsg);
  inputText.value = "";
  await nextTick();
  scrollToBottom();

  isStreaming.value = true;

  // 创建 AI 消息占位 + 思考数据
  const thinkingData: ThinkingData = {
    expanded: true, // 默认展开
    steps: [],
    retrievalInfo: "",
    model: "",
    systemPrompt: "",
  };

  const aiMsg: Message = {
    id: Date.now() + 1,
    role: "assistant",
    content: "",
    timestamp: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
    thinking: thinkingData,
  };
  messages.value.push(aiMsg);
  currentThinking.value = thinkingData;

  await nextTick();
  scrollToBottom();

  // ── SSE 连接 ─────────────────────────────────────────
  try {
    const response = await apiFetch(`${API_PREFIX}/course/${courseId.value}/chat/completions`, {
      method: "POST",
      body: JSON.stringify({
        session_id: activeSession.value,
        message: text,
        skill: activeSkill.value,
      }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.message || t("_courseChat.requestFailed"));
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error(t("_courseChat.streamingNotSupported"));

    const decoder = new TextDecoder();
    let buffer = "";
    let answerStarted = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") continue;
        if (!raw) continue;

        try {
          const event = JSON.parse(raw);

          switch (event.type) {
            case "status": {
              // 添加思考步骤
              thinkingData.steps.push({
                phase: event.phase,
                message: event.message,
                retrievalCount: event.retrievalCount,
                retrievals: event.retrievals,
                memorySummary: event.memorySummary,
                memoryDetail: event.memoryDetail,
              });
              break;
            }
            case "thinking_start": {
              thinkingData.model = event.model || "";
              thinkingData.retrievalInfo = event.retrievalInfo || "";
              thinkingData.systemPrompt = event.systemPrompt || "";
              thinkingData.memorySummary = event.memorySummary || "";
              thinkingData.memoryPrompt = event.memoryPrompt || "";
              thinkingData.memoryDetail = event.memoryDetail || [];
              break;
            }
            case "content": {
              if (!answerStarted) {
                // 答案开始，自动折叠思考面板
                thinkingData.expanded = false;
                answerStarted = true;
              }
              messages.value[messages.value.length - 1].content += event.content;
              await nextTick();
              break;
            }
            case "done": {
              messages.value[messages.value.length - 1].sources = event.sources || "";
              // 完成时清除思考面板
              messages.value[messages.value.length - 1].thinking = undefined;
              currentThinking.value = null;
              break;
            }
            case "error": {
              // 出错时清除思考面板，只显示错误信息
              const lastMsg2 = messages.value[messages.value.length - 1];
              lastMsg2.thinking = undefined;
              const err2 = cleanError(event.message);
              lastMsg2.content = `❌ ${t("_courseChat.errorPrefix")}：${err2.summary}`;
              lastMsg2.errorDetail = err2.detail;
              break;
            }
          }
        } catch {
          // 忽略解析错误
        }
      }
    }
  } catch (err: any) {
    const lastMsg3 = messages.value[messages.value.length - 1];
    lastMsg3.thinking = undefined;
    const err3 = cleanError(err.message);
    lastMsg3.content = `❌ ${t("_courseChat.requestFailed")}：${err3.summary}`;
    lastMsg3.errorDetail = err3.detail;
  } finally {
    isStreaming.value = false;
    currentThinking.value = null;
    await nextTick();
    scrollToBottom();
  }
};

// ── Actions ───────────────────────────────────────────

const toggleThinking = (msg: Message) => {
  if (msg.thinking) {
    msg.thinking.expanded = !msg.thinking.expanded;
  }
};

const handleCodeClick = (e: MouseEvent) => {
  const target = e.target as HTMLElement;
  if (!target.classList.contains("code-btn")) return;
  const wrap = target.closest(".code-block-wrap") as HTMLElement | null;
  if (!wrap) return;
  const code = wrap.querySelector("code")?.textContent || "";
  const lang = wrap.dataset.lang || "text";
  const action = target.dataset.action;
  if (action === "copy") {
    navigator.clipboard.writeText(code).then(() => {
      ElMessage.success({ message: t("_courseChat.copied"), duration: 1000, showClose: false });
    });
  } else if (action === "download") {
    const extMap: Record<string, string> = {
      python: "py",
      javascript: "js",
      typescript: "ts",
      html: "html",
      css: "css",
      json: "json",
      sql: "sql",
      shell: "sh",
      bash: "sh",
      java: "java",
      cpp: "cpp",
      c: "c",
      go: "go",
      rust: "rs",
      yaml: "yml",
    };
    const blob = new Blob([code], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `snippet.${extMap[lang] || "txt"}`;
    a.click();
    URL.revokeObjectURL(url);
  }
};

const renderMarkdown = (content: string): string => {
  // Protect code blocks from other transforms
  const codeBlocks: string[] = [];
  let html = content.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // Code blocks ```language\n...```
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_m: string, lang: string, code: string) => {
    const langLabel = lang || "text";
    const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
    codeBlocks.push(
      `<div class="code-block-wrap" data-lang="${langLabel}"><div class="code-block-header"><span class="code-lang">${langLabel}</span><span class="code-actions"><span class="code-btn" data-action="copy" title="${t("_courseChat.copy")}">📋 ${t("_courseChat.copy")}</span><span class="code-btn" data-action="download" title="${t("_courseChat.download")}">⬇ ${t("_courseChat.download")}</span></span></div><pre class="code-block"><code>${code}</code></pre></div>`
    );
    return placeholder;
  });
  // Inline code `code`
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
  // Bold **text**
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Block LaTeX $$...$$ → KaTeX rendered
  html = html.replace(/\$\$([\s\S]+?)\$\$/g, (_m: string, tex: string) => {
    try {
      return `<div class="latex-block">${katex.renderToString(tex.trim(), { throwOnError: false, displayMode: true, strict: false })}</div>`;
    } catch {
      return `<div class="latex-block latex-error">$$${tex}$$</div>`;
    }
  });
  // Inline LaTeX $...$ → KaTeX rendered (avoid matching escaped \$ or currency)
  html = html.replace(/(?<!\$)\$(?!\$)((?:[^$\\]|\\.)+?)\$(?!\d)/g, (_m: string, tex: string) => {
    try {
      return `<span class="latex-inline">${katex.renderToString(tex.trim(), { throwOnError: false, strict: false })}</span>`;
    } catch {
      return `<span class="latex-inline">$${tex}$</span>`;
    }
  });

  // Unordered lists
  html = html.replace(/(?:^|\n)((?:[\t ]*[-*+][\s\S]+?\n?)+)/g, (_m: string, list: string) => {
    const items = list
      .split(/\n/)
      .filter((l: string) => /^[\t ]*[-*+]\s/.test(l))
      .map((l: string) => `<li>${l.replace(/^[\t ]*[-*+]\s/, "")}</li>`)
      .join("");
    return `<ul class="md-list">${items}</ul>`;
  });
  // Ordered lists
  html = html.replace(/(?:^|\n)((?:[\t ]*\d+\.[\s\S]+?\n?)+)/g, (_m: string, list: string) => {
    const items = list
      .split(/\n/)
      .filter((l: string) => /^[\t ]*\d+\.\s/.test(l))
      .map((l: string) => `<li>${l.replace(/^[\t ]*\d+\.\s/, "")}</li>`)
      .join("");
    return `<ol class="md-list">${items}</ol>`;
  });
  // Line breaks
  html = html.replace(/\n/g, "<br>");
  // Headings
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-heading">$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-heading">$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-heading">$1</h2>');

  // Restore code blocks
  codeBlocks.forEach((block, i) => {
    html = html.replace(`__CODEBLOCK_${i}__`, block);
  });

  return html;
};

const scrollToBottom = () => {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
  }
};

/** 切换技能：清空当前对话，等用户发送第一条消息时自动创建新会话 */
/** 复制 AI 回复全文 */
const copyMessage = (msg: Message) => {
  navigator.clipboard.writeText(msg.content).then(() => {
    ElMessage.success({ message: t("_courseChat.copied"), duration: 1000, showClose: false });
  });
};

/** 重新生成：删除最后一个 AI 消息并重新发送上一条用户消息 */
const regenerateLast = async () => {
  if (isStreaming.value) return;
  const lastUser = [...messages.value].reverse().find(m => m.role === "user");
  if (!lastUser) return;
  // 删掉最后一个 AI 消息（如果存在）
  const lastIdx = messages.value.length - 1;
  if (messages.value[lastIdx]?.role === "assistant") messages.value.pop();
  // 重新发送
  const text = lastUser.content;
  inputText.value = text;
  await sendMessage();
};

const likeMsg = (msg: Message) => {
  msg._liked = !msg._liked;
  if (msg._liked) msg._disliked = false;
  ElMessage.success({
    message: msg._liked ? t("_courseChat.thanksFeedback") : t("_courseChat.cancelled"),
    duration: 1000,
    showClose: false,
  });
};

const dislikeMsg = (msg: Message) => {
  msg._disliked = !msg._disliked;
  if (msg._disliked) msg._liked = false;
  ElMessage.success({
    message: msg._disliked ? t("_courseChat.feedbackReceived") : t("_courseChat.cancelled"),
    duration: 1000,
    showClose: false,
  });
};

/** 切换技能：清空当前对话，等用户发送第一条消息时自动创建新会话 */
const switchSkill = (key: string) => {
  if (isStreaming.value) return;
  if (activeSkill.value === key) return;
  activeSkill.value = key;
  activeSession.value = 0;
  messages.value = [];
  currentThinking.value = null;
  ElMessage.success(t("_courseChat.switchMode", { skill: skills.find(s => s.key === key)?.displayName }));
};

const exportMarkdown = () => {
  let md = `# ${courseName}——${t("_courseChat.chatRecord")}\n`;
  md += `> ${t("_courseChat.exportTime")}：${new Date().toLocaleString()}\n`;
  md += `> ${t("_courseChat.exportSkill")}：${skills.find(s => s.key === activeSkill.value)?.displayName}\n`;
  md += `> ${t("_courseChat.exportTotalMessages")}：${messages.value.length} ${t("_courseChat.messagesUnit")}\n\n## ${t("_courseChat.chatDetails")}\n\n`;
  messages.value.forEach(m => {
    md += `### ${m.role === "user" ? t("_courseChat.user") : t("_courseChat.ai")} · ${m.timestamp}\n`;
    md += `${m.content}\n\n`;
    if (m.sources) md += `> ${t("_courseChat.source")}${m.sources}\n\n`;
  });
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${courseName}_${new Date().toISOString().split("T")[0]}.md`;
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success(t("_courseChat.exportSuccess"));
};

const clearChat = () => {
  messages.value = [];
  currentThinking.value = null;
  ElMessage.success(t("_courseChat.chatCleared"));
};

onMounted(async () => {
  await loadSessions();
  if (sessions.value.length > 0) {
    activeSession.value = sessions.value[0].id;
    await loadMessages(sessions.value[0].id);
  }
  scrollToBottom();
});

// Floating summary button
const fabPos = ref({ x: window.innerWidth - 180, y: window.innerHeight - 160 });
const fabDragging = ref(false);
const fabDragStart = ref({ x: 0, y: 0 });
const fabStartPos = ref({ x: 0, y: 0 });

const onFabMouseDown = (e: MouseEvent) => {
  e.preventDefault();
  fabDragging.value = false;
  fabDragStart.value = { x: e.clientX - fabPos.value.x, y: e.clientY - fabPos.value.y };
  fabStartPos.value = { x: e.clientX, y: e.clientY };
  window.addEventListener("mousemove", onFabMouseMove);
  window.addEventListener("mouseup", onFabMouseUp);
};

const onFabMouseMove = (e: MouseEvent) => {
  const dx = e.clientX - fabStartPos.value.x;
  const dy = e.clientY - fabStartPos.value.y;
  if (Math.abs(dx) > 2 || Math.abs(dy) > 2) fabDragging.value = true;
  if (!fabDragging.value) return;
  fabPos.value = {
    x: Math.min(window.innerWidth - 60, Math.max(10, e.clientX - fabDragStart.value.x)),
    y: Math.min(window.innerHeight - 60, Math.max(10, e.clientY - fabDragStart.value.y)),
  };
};

const onFabMouseUp = () => {
  window.removeEventListener("mousemove", onFabMouseMove);
  window.removeEventListener("mouseup", onFabMouseUp);
};

const onClickFab = () => {
  if (!fabDragging.value) {
    router.push({ name: "CourseSummary", query: { name: courseName } });
  }
};
</script>

<template>
  <div class="chat-page">
    <!-- Left Sidebar -->
    <aside class="chat-sidebar">
      <div class="sidebar-top">
        <el-button :icon="ArrowLeft" text @click="router.push({ name: 'CourseDashboard' })">
          {{ $t("_courseChat.back") }}
        </el-button>
      </div>

      <!-- Skill Selector -->
      <div class="skill-section">
        <div class="sidebar-label">{{ $t("_courseChat.skillSelector") }}</div>
        <div class="skill-list">
          <div
            v-for="skill in skills"
            :key="skill.key"
            class="skill-item"
            :class="{ active: activeSkill === skill.key }"
            @click="switchSkill(skill.key)"
          >
            <el-icon :size="16"><component :is="skill.icon" /></el-icon>
            <span class="skill-name">{{ skill.displayName }}</span>
          </div>
        </div>
      </div>

      <el-divider style="margin: 12px 0" />

      <!-- Session List -->
      <div class="session-section">
        <div class="sidebar-label">
          <span>{{ $t("_courseChat.sessionList") }}</span>
          <el-button :icon="Plus" text size="small" @click="newSession" />
        </div>
        <div class="session-list">
          <div
            v-for="session in sessions"
            :key="session.id"
            class="session-item"
            :class="{ active: activeSession === session.id }"
            @click="switchSession(session.id)"
          >
            <span class="session-title">{{ session.title }}</span>
            <span class="session-date">{{ session.updatedAt }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="chat-main">
      <div class="chat-actions">
        <button class="action-btn" @click="exportMarkdown">
          <el-icon :size="14"><Download /></el-icon>
          <span>{{ $t("_courseChat.exportChat") }}</span>
        </button>
        <button class="action-btn" @click="clearChat">
          <el-icon :size="14"><Refresh /></el-icon>
          <span>{{ $t("_courseChat.clearChat") }}</span>
        </button>
      </div>

      <!-- Messages -->
      <div ref="messagesRef" class="chat-messages" @click="handleCodeClick">
        <div v-if="messages.length === 0" class="chat-empty">
          <div class="empty-illustration">
            <div class="empty-circle" />
            <div class="empty-dots">
              <span />
              <span />
              <span />
            </div>
          </div>
          <p class="empty-title">{{ $t("_courseChat.emptyChatHint1") }}</p>
          <p class="empty-sub">{{ $t("_courseChat.emptyChatHint2") }}</p>
        </div>

        <div v-for="msg in messages" :key="msg.id" class="message-item" :class="msg.role">
          <div class="msg-inner">
            <div class="message-avatar">
              <span>{{ msg.role === "user" ? $t("_courseChat.user") : $t("_courseChat.ai") }}</span>
            </div>
            <div class="message-body">
              <!-- ═══════ 思考面板 (仅 AI 消息，且有待思考数据) ═══════ -->
              <div
                v-if="msg.role === 'assistant' && msg.thinking && msg.thinking.steps.length > 0"
                class="thinking-panel"
                :class="{ collapsed: !msg.thinking.expanded }"
              >
                <div class="thinking-header" @click="toggleThinking(msg)">
                  <div class="thinking-header-left">
                    <span class="thinking-dot" :class="{ active: !msg.content }" />
                    <span class="thinking-title">
                      {{ msg.content ? $t("_courseChat.thinkingProcess") : $t("_courseChat.thinking") }}
                    </span>
                    <span v-if="msg.thinking.model" class="thinking-model">{{ msg.thinking.model }}</span>
                  </div>
                  <el-icon :size="14" class="thinking-chevron" :class="{ rotated: msg.thinking.expanded }">
                    <ArrowDown />
                  </el-icon>
                </div>

                <div v-show="msg.thinking.expanded" class="thinking-body">
                  <!-- 步骤列表 -->
                  <div
                    v-for="(step, idx) in msg.thinking.steps"
                    :key="idx"
                    class="thinking-step"
                    :class="'phase-' + step.phase"
                  >
                    <span class="step-indicator">
                      {{
                        step.phase === "generating"
                          ? "✍️"
                          : step.phase === "searching"
                            ? "🔍"
                            : step.phase === "found"
                              ? "📚"
                              : step.phase === "analyzing"
                                ? "🔄"
                                : step.phase === "memory"
                                  ? "🧠"
                                  : step.phase === "memory_updated"
                                    ? "✅"
                                    : "⏳"
                      }}
                    </span>
                    <span class="step-message">{{ step.message }}</span>
                  </div>

                  <!-- 检索到的文档 -->
                  <div v-for="(step, idx) in msg.thinking.steps" :key="'retr-' + idx">
                    <div v-if="step.retrievals && step.retrievals.length > 0" class="retrievals-list">
                      <div v-for="(item, rIdx) in step.retrievals" :key="rIdx" class="retrieval-card">
                        <div class="retrieval-header">
                          <el-icon :size="12"><Search /></el-icon>
                          <span class="retrieval-source">{{ item.source }}</span>
                          <span class="retrieval-relevance">{{ item.relevance }}</span>
                        </div>
                        <div class="retrieval-preview">{{ item.preview }}</div>
                      </div>
                    </div>
                  </div>

                  <!-- 学生画像 / 记忆 -->
                  <div v-if="msg.thinking.memorySummary" class="memory-section">
                    <div class="sp-label">🧠 {{ $t("_courseChat.studentProfile") }}</div>
                    <div class="memory-summary-text">{{ msg.thinking.memorySummary }}</div>
                    <div v-if="msg.thinking.memoryDetail && msg.thinking.memoryDetail.length > 0" class="memory-bars">
                      <div
                        v-for="(item, mIdx) in msg.thinking.memoryDetail"
                        :key="'mem-' + mIdx"
                        class="memory-bar-item"
                      >
                        <span class="memory-topic">{{ item.topic }}</span>
                        <div class="memory-bar-track">
                          <div
                            class="memory-bar-fill"
                            :class="item.mastery < 0.5 ? 'low' : item.mastery < 0.75 ? 'mid' : 'high'"
                            :style="{ width: item.mastery * 100 + '%' }"
                          />
                        </div>
                        <span class="memory-pct">{{ Math.round(item.mastery * 100) }}%</span>
                      </div>
                    </div>
                  </div>

                  <!-- System Prompt 预览（简洁版） -->
                  <div
                    v-if="msg.thinking.systemPrompt"
                    class="system-prompt-preview"
                    @click="msg._showSp = !msg._showSp"
                  >
                    <span class="sp-label">📝 System Prompt</span>
                    <span class="sp-toggle">
                      {{ msg._showSp ? $t("_courseChat.collapse") : $t("_courseChat.expand") }}
                    </span>
                    <div v-if="msg._showSp" class="sp-content">{{ msg.thinking.systemPrompt }}</div>
                    <div v-else class="sp-content sp-content--truncated">
                      {{ msg.thinking.systemPrompt.slice(0, 200) }}...
                    </div>
                  </div>
                </div>
              </div>

              <!-- ═══════ 答案内容 (黑色/深色) ═══════ -->
              <div
                v-if="msg.content"
                class="message-bubble"
                :class="{
                  'is-streaming':
                    msg.role === 'assistant' && isStreaming && messages[messages.length - 1]?.id === msg.id,
                }"
              >
                <div class="message-content" v-html="renderMarkdown(msg.content)" />
              </div>

              <!-- 空内容且流式进行中：显示闪烁光标 -->
              <div
                v-else-if="msg.role === 'assistant' && isStreaming && messages[messages.length - 1]?.id === msg.id"
                class="message-bubble message-bubble--empty"
              >
                <span class="thinking-dots">
                  {{ $t("_courseChat.thinkingBrief") }}
                  <span class="dot-anim">
                    <span>.</span>
                    <span>.</span>
                    <span>.</span>
                  </span>
                </span>
              </div>

              <!-- ═══════ 错误详情（可展开） ═══════ -->
              <div v-if="msg.errorDetail" class="error-detail-section">
                <div class="error-detail-toggle" @click="msg._showDetail = !msg._showDetail">
                  <el-icon :size="14"><component :is="msg._showDetail ? ArrowDown : ArrowRight" /></el-icon>
                  <span>{{ msg._showDetail ? $t("_courseChat.collapseDetail") : $t("_courseChat.viewDetail") }}</span>
                </div>
                <div v-if="msg._showDetail" class="error-detail-content">{{ msg.errorDetail }}</div>
              </div>

              <!-- ═══════ AI 消息操作按钮（完成且非错误） ═══════ -->
              <div
                v-if="
                  msg.role === 'assistant' &&
                  msg.content &&
                  !msg.errorDetail &&
                  !(isStreaming && messages[messages.length - 1]?.id === msg.id)
                "
                class="msg-actions"
              >
                <span class="msg-btn" @click="copyMessage(msg)">📋 {{ $t("_courseChat.copy") }}</span>
                <span class="msg-btn" @click="regenerateLast">🔄 {{ $t("_courseChat.regenerate") }}</span>
                <span class="msg-btn" :class="{ active: msg._liked }" @click="likeMsg(msg)">
                  👍 {{ msg._liked ? $t("_courseChat.liked") : $t("_courseChat.like") }}
                </span>
                <span class="msg-btn" :class="{ active: msg._disliked }" @click="dislikeMsg(msg)">
                  👎 {{ msg._disliked ? $t("_courseChat.disliked") : $t("_courseChat.dislike") }}
                </span>
              </div>

              <!-- 元信息 -->
              <div class="message-meta">
                <span v-if="msg.sources" class="message-source">
                  <el-icon :size="12"><Icon icon="ep:document" /></el-icon>
                  {{ msg.sources }}
                </span>
                <span class="message-time">{{ msg.timestamp }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="composer">
        <div class="composer-input">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="1"
            :placeholder="$t('_courseChat.inputPlaceholder')"
            resize="none"
            @keydown.enter.exact.prevent="sendMessage"
          />
        </div>
        <button class="send-btn" :class="{ loading: isStreaming }" @click="sendMessage">
          <el-icon v-if="!isStreaming" :size="18"><Promotion /></el-icon>
          <el-icon v-else :size="18" class="is-loading"><Loading /></el-icon>
        </button>
      </div>
    </main>

    <!-- Floating Summary Button -->
    <div
      class="fab-summary"
      :style="{ left: fabPos.x + 'px', top: fabPos.y + 'px' }"
      @mousedown="onFabMouseDown"
      @click="onClickFab"
    >
      <el-icon :size="18"><MagicStick /></el-icon>
      <span class="fab-label">{{ $t("_courseChat.summary") }}</span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  height: 100%;
  margin: -10px -12px;
  overflow: hidden;
}

// ===== Left Sidebar =====
.chat-sidebar {
  width: 240px;
  min-width: 240px;
  background: var(--tk-surface-bg-color-box);
  border-right: 1px solid var(--tk-surface-border-color);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.sidebar-top {
  padding: 16px;
}
.sidebar-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--tk-gray-color-400);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0 16px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.skill-section {
  padding: 4px 0;
}
.skill-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 8px;
}
.skill-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 13px;
  color: var(--tk-gray-color-600);
  position: relative;
  &:hover {
    background: var(--tk-gray-color-100);
    color: var(--tk-gray-color-800);
  }
  &.active {
    background: color-mix(in srgb, var(--tk-color-primary) 10%, transparent);
    color: var(--tk-color-primary);
    font-weight: 600;
    &::before {
      content: "";
      position: absolute;
      left: -8px;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 20px;
      border-radius: 0 3px 3px 0;
      background: var(--tk-color-primary);
    }
  }
}
.skill-name {
  font-weight: inherit;
}
.session-section {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
.session-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 8px;
}
.session-item {
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  &:hover {
    background: var(--tk-gray-color-100);
  }
  &.active {
    background: color-mix(in srgb, var(--tk-color-primary) 8%, transparent);
  }
}
.session-title {
  display: block;
  font-size: 13px;
  color: var(--tk-gray-color-800);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}
.session-date {
  font-size: 11px;
  color: var(--tk-gray-color-400);
}

.chat-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 10px 20px;
}
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 20px;
  color: var(--tk-gray-color-700);
  background: var(--tk-surface-bg-color-box);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  &:hover {
    color: var(--tk-color-primary);
    border-color: var(--tk-color-primary);
    background: var(--tk-bg-primary);
    transform: translateY(-1px);
  }
  &:active {
    transform: scale(0.96);
  }
}

// ===== Main Chat =====
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--tk-surface-bg-color-page);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 32px 0;
  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-thumb {
    background: var(--tk-gray-color-300);
    border-radius: 3px;
  }
}

.msg-inner {
  display: flex;
  gap: 14px;
  max-width: 768px;
  margin: 0 auto;
  padding: 0 24px;
}
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
}
.empty-illustration {
  position: relative;
  width: 80px;
  height: 80px;
  margin-bottom: 12px;
  .empty-circle {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    border: 3px dashed var(--tk-gray-color-200);
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
  }
  .empty-dots {
    position: absolute;
    bottom: 4px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 6px;
    span {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--tk-gray-color-300);
      animation: dotPulse 1.4s ease-in-out infinite;
      &:nth-child(2) {
        animation-delay: 0.2s;
      }
      &:nth-child(3) {
        animation-delay: 0.4s;
      }
    }
  }
}
@keyframes dotPulse {
  0%,
  80%,
  100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}
.empty-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--tk-gray-color-500);
  margin: 0;
}
.empty-sub {
  font-size: 13px;
  color: var(--tk-gray-color-400);
  margin: 0;
}

// ═══════ Thinking Panel ═══════
.thinking-panel {
  margin-bottom: 10px;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--tk-color-warning) 35%, transparent);
  background: color-mix(in srgb, var(--tk-color-warning) 8%, var(--tk-surface-bg-color-box));
  overflow: hidden;
  transition: all 0.3s ease;

  &.collapsed {
    opacity: 0.7;
  }
}
.thinking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
  &:hover {
    background: color-mix(in srgb, var(--tk-color-warning) 10%, transparent);
  }
}
.thinking-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.thinking-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--tk-color-warning);
  &.active {
    background: #f59e0b;
    animation: dotPulse 1.4s ease-in-out infinite;
  }
}
.thinking-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--tk-gray-color-800);
}
.thinking-model {
  font-size: 11px;
  color: var(--tk-gray-color-700);
  background: color-mix(in srgb, var(--tk-color-warning) 14%, transparent);
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--tk-color-warning) 30%, transparent);
}
.thinking-chevron {
  color: var(--tk-gray-color-600);
  transition: transform 0.25s ease;
  &.rotated {
    transform: rotate(180deg);
  }
}
.thinking-body {
  padding: 0 14px 12px;
}

.thinking-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  font-size: 12px;
  color: var(--tk-gray-color-600);
  &.phase-searching {
    color: #6366f1;
  }
  &.phase-found {
    color: #059669;
  }
  &.phase-analyzing {
    color: #7c3aed;
  }
  &.phase-generating {
    color: #d97706;
  }
  &.phase-no_docs {
    color: #dc2626;
  }
  &.phase-memory {
    color: #16a34a;
  }
  &.phase-memory_updated {
    color: #16a34a;
  }
}
.step-indicator {
  flex-shrink: 0;
  font-size: 14px;
}
.step-message {
  line-height: 1.5;
}

.retrievals-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 8px 0 8px 22px;
}
.retrieval-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 8px;
  padding: 10px 12px;
  transition: border-color 0.2s;
  &:hover {
    border-color: var(--tk-color-warning);
  }
}
.retrieval-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.retrieval-source {
  font-size: 12px;
  font-weight: 600;
  color: var(--tk-gray-color-800);
  flex: 1;
}
.retrieval-relevance {
  font-size: 11px;
  color: var(--tk-color-success);
  background: var(--tk-bg-success);
  padding: 1px 6px;
  border-radius: 8px;
}
.retrieval-preview {
  font-size: 11px;
  color: var(--tk-gray-color-600);
  line-height: 1.5;
}

.system-prompt-preview {
  margin-top: 6px;
  padding: 8px 10px;
  background: var(--tk-surface-bg-color-page);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  &:hover {
    border-color: var(--tk-gray-color-300);
  }
}
.sp-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--tk-gray-color-500);
}
.sp-toggle {
  font-size: 11px;
  color: var(--tk-color-primary);
  float: right;
}
.sp-content {
  margin-top: 6px;
  font-size: 11px;
  color: var(--tk-gray-color-500);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  &--truncated {
    max-height: none;
    color: var(--tk-gray-color-400);
  }
}

// ── Memory Section ──
.memory-section {
  margin-top: 8px;
  padding: 10px 12px;
  background: var(--tk-bg-success);
  border: 1px solid color-mix(in srgb, var(--tk-color-success) 30%, transparent);
  border-radius: 8px;
}
.memory-summary-text {
  font-size: 12px;
  color: var(--tk-gray-color-800);
  margin-bottom: 6px;
}
.memory-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.memory-bar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.memory-topic {
  width: 80px;
  flex-shrink: 0;
  color: var(--tk-gray-color-800);
  font-weight: 500;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.memory-bar-track {
  flex: 1;
  height: 6px;
  background: var(--tk-gray-color-200);
  border-radius: 3px;
  overflow: hidden;
}
.memory-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
  &.low {
    background: #ef4444;
  }
  &.mid {
    background: #f59e0b;
  }
  &.high {
    background: #22c55e;
  }
}
.memory-pct {
  width: 32px;
  flex-shrink: 0;
  color: var(--tk-gray-color-600);
  font-variant-numeric: tabular-nums;
}

// ═══════ Messages ═══════
.message-item {
  margin-bottom: 28px;
  animation: messageIn 0.3s ease;
  &.user {
    .msg-inner {
      flex-direction: row-reverse;
    }
    .message-avatar {
      background: var(--tk-gray-color-300);
      color: var(--tk-gray-color-500);
      font-weight: 700;
    }
    .message-body {
      align-items: flex-end;
    }
    .message-bubble {
      background: var(--tk-surface-bg-color-box);
      color: var(--tk-gray-color-800);
      border-radius: 16px 4px 16px 16px;
      padding: 10px 16px;
      font-size: 14px;
      :deep(strong) {
        color: var(--tk-gray-color-800);
      }
      :deep(.inline-code) {
        background: var(--tk-gray-color-100);
        color: var(--tk-color-primary);
      }
      :deep(.md-heading) {
        color: var(--tk-gray-color-800);
      }
    }
    .message-meta {
      flex-direction: row-reverse;
    }
  }
  &.assistant {
    .message-avatar {
      background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
      color: #fff;
      font-weight: 700;
    }
    // ★ AI 答案：无底色框，仅内边距 + 深色文字
    .message-bubble {
      background: transparent;
      border: none;
      border-radius: 0;
      box-shadow: none;
      color: var(--tk-gray-color-900);
      padding: 4px 0;
      font-size: 15px;
      &.is-streaming {
        border: none;
      }
      :deep(strong) {
        color: var(--tk-gray-color-900);
      }
      :deep(.inline-code) {
        background: var(--tk-gray-color-100);
        color: var(--tk-color-primary);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.9em;
        font-family: "JetBrains Mono", monospace;
      }
      :deep(.code-block-wrap) {
        margin: 8px 0;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #2a2a3e;
        .code-block-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 6px 12px;
          background: #16162a;
          font-size: 11px;
          .code-lang {
            color: #8b949e;
            font-weight: 600;
            text-transform: uppercase;
          }
          .code-actions {
            display: flex;
            gap: 4px;
          }
          .code-btn {
            cursor: pointer;
            color: #8b949e;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            user-select: none;
            &:hover {
              background: #21213d;
              color: #e6edf3;
            }
          }
        }
        .code-block {
          background: #1e1e2e;
          color: #cdd6f4;
          padding: 14px 16px;
          overflow-x: auto;
          font-size: 0.85em;
          line-height: 1.6;
          display: block;
          margin: 0;
        }
      }
      :deep(.latex-block) {
        display: block;
        text-align: center;
        padding: 16px 12px;
        margin: 12px 0;
        overflow-x: auto;
        font-size: 1.1em;
        background: color-mix(in srgb, var(--tk-color-primary) 4%, transparent);
        border-radius: 8px;
        border: 1px solid color-mix(in srgb, var(--tk-color-primary) 12%, transparent);
        .katex-display {
          margin: 0;
        }
        .katex {
          font-size: 1.1em;
        }
      }
      :deep(.latex-inline) {
        display: inline;
        font-size: 1em;
        padding: 0 2px;
        .katex {
          font-size: 1em;
        }
      }
      :deep(.latex-error) {
        color: var(--tk-color-danger);
        font-family: "JetBrains Mono", monospace;
        font-size: 0.9em;
      }
      :deep(.md-heading) {
        margin: 12px 0 6px;
        font-weight: 700;
        color: var(--tk-gray-color-900);
        &:first-child {
          margin-top: 0;
        }
      }
      :deep(.md-list) {
        margin: 8px 0;
        padding-left: 24px;
        li {
          margin: 4px 0;
          line-height: 1.6;
          color: var(--tk-gray-color-800);
        }
      }
    }
    .message-bubble--empty {
      background: transparent;
      border: none;
      box-shadow: none;
      padding: 4px 0;
    }
  }
}
@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  min-width: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
  span {
    line-height: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 32px;
  }
}
.message-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  max-width: 80%;
}
.message-bubble {
  padding: 14px 18px;
  font-size: 14px;
  line-height: 1.75;
  word-break: break-word;
}

.thinking-dots {
  font-size: 14px;
  color: var(--tk-gray-color-400);
  .dot-anim span {
    animation: dotFade 1.4s infinite;
    &:nth-child(2) {
      animation-delay: 0.2s;
    }
    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}
@keyframes dotFade {
  0%,
  80%,
  100% {
    opacity: 0.2;
  }
  40% {
    opacity: 1;
  }
}

// ── Error Detail ──
.error-detail-section {
  margin-top: 4px;
}
.error-detail-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--tk-color-primary);
  cursor: pointer;
  user-select: none;
  &:hover {
    text-decoration: underline;
  }
}
.error-detail-content {
  margin-top: 6px;
  padding: 8px 10px;
  font-size: 11px;
  font-family: "JetBrains Mono", monospace;
  color: var(--tk-gray-color-600);
  background: var(--tk-gray-color-100);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
  max-height: 160px;
  overflow-y: auto;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  font-size: 12px;
}
.msg-actions {
  display: flex;
  gap: 12px;
  margin-top: 6px;
}
.msg-btn {
  font-size: 12px;
  color: var(--tk-gray-color-400);
  cursor: pointer;
  user-select: none;
  transition: color 0.15s;
  &:hover {
    color: var(--tk-gray-color-700);
  }
  &.active {
    color: var(--tk-color-primary);
    font-weight: 600;
  }
}
.message-source {
  color: var(--tk-color-primary);
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}
.message-time {
  color: var(--tk-gray-color-300);
}

// ===== Input (DeepSeek-style centered pill) =====
.composer {
  max-width: 768px;
  margin: 0 auto 20px;
  padding: 0 24px;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: transparent;
  border-radius: 0;
  box-shadow: none;
}
.composer-input {
  flex: 1;
  min-width: 0;
  :deep(.el-textarea) {
    .el-textarea__inner {
      border: 1px solid var(--tk-surface-border-color);
      border-radius: 20px;
      background: var(--tk-surface-bg-color-box);
      box-shadow: none;
      font-size: 14px;
      line-height: 1.6;
      padding: 10px 16px;
      min-height: 40px;
      max-height: 180px;
      resize: none;
      color: var(--tk-gray-color-900);
      &::placeholder {
        color: var(--tk-gray-color-400);
      }
      &:focus {
        border-color: var(--tk-color-primary);
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.12);
      }
    }
  }
}
.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  min-width: 38px;
  color: #fff;
  background: var(--tk-color-primary);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
  margin-bottom: 2px;
  &:hover {
    background: rgba(99, 102, 241, 0.85);
    transform: scale(1.05);
  }
  &:active {
    transform: scale(0.95);
  }
  &.loading {
    background: var(--tk-gray-color-400);
    cursor: default;
    pointer-events: none;
  }
}

.fab-summary {
  position: fixed;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  background: rgba(30, 30, 50, 0.88);
  backdrop-filter: blur(12px);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 24px;
  cursor: grab;
  user-select: none;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.18);
  transition:
    box-shadow 0.2s,
    transform 0.15s;
  white-space: nowrap;
  &:active {
    cursor: grabbing;
    transform: scale(0.97);
  }
  &:hover {
    box-shadow: 0 6px 32px rgba(0, 0, 0, 0.25);
  }
  .fab-label {
    font-size: 13px;
    font-weight: 500;
  }
}

@media (max-width: 768px) {
  .chat-sidebar {
    display: none;
  }
  .chat-messages {
    padding: 16px;
  }
  .message-body {
    max-width: 90%;
  }
  .composer {
    margin: 0 10px 10px;
  }
}
</style>
