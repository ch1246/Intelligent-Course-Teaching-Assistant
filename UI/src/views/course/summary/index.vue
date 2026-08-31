<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import {
  ArrowLeft,
  MagicStick,
  Clock,
  Download,
  Reading,
  CircleCheck,
  WarningFilled,
  Collection,
} from "@element-plus/icons-vue";
import { http } from "@/common/http";
import { t } from "@/common/languages";

defineOptions({ name: "CourseSummary" });

const route = useRoute();
const router = useRouter();

// ── Route params ───────────────────────────────────
const courseId = computed(() => {
  return ((route.params.courseId || route.query.courseId) as string) || (route.query.courseId as string) || "";
});
const courseName = computed(() => (route.query.name as string) || t("_courseChat.courseChat"));

// ── State ──────────────────────────────────────────
const loading = ref(true);
const error = ref("");
const summarizing = ref(false);
const summaryReady = ref(false);

interface SummarySection {
  title: string;
  content: string;
}

const summary = ref<SummarySection[]>([
  { title: t("_courseChat.topicSummary"), content: "" },
  { title: t("_courseChat.resolvedQuestions"), content: "" },
  { title: t("_courseChat.unresolvedQuestions"), content: "" },
  { title: t("_courseChat.knowledgePoints"), content: "" },
]);

// API response fields for stats
const apiStats = ref({
  total_learning_minutes: 0,
  total_chat_sessions: 0,
  total_chat_messages: 0,
});

const recentSessions = ref<any[]>([]);

// ── Section config ─────────────────────────────────
const sectionIcons = [Reading, CircleCheck, WarningFilled, Collection];
const sectionColors = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6"];
const sectionBorders = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6"];

// ── Helpers ────────────────────────────────────────
const parseSummaryContent = (data: any): SummarySection[] => {
  // Structured response from backend: data.sections
  const sections = data?.sections;
  if (sections) {
    const toLines = (arr: any[] | undefined): string => (Array.isArray(arr) && arr.length ? arr.join("\n") : "");
    const toTags = (arr: any[] | undefined): string => (Array.isArray(arr) && arr.length ? arr.join(" · ") : "");
    return [
      { title: t("_courseChat.topicSummary"), content: sections.topic_summary || "" },
      { title: t("_courseChat.resolvedQuestions"), content: toLines(sections.resolved_questions) },
      { title: t("_courseChat.unresolvedQuestions"), content: toLines(sections.unresolved_questions) },
      { title: t("_courseChat.knowledgePoints"), content: toTags(sections.knowledge_points) },
    ];
  }

  // Backward-compatible: plain string summary
  const raw = typeof data === "string" ? data : data?.summary || "";
  return [
    { title: t("_courseChat.topicSummary"), content: raw || t("_courseChat.noSummaryContent") },
    { title: t("_courseChat.resolvedQuestions"), content: "" },
    { title: t("_courseChat.unresolvedQuestions"), content: "" },
    { title: t("_courseChat.knowledgePoints"), content: "" },
  ];
};

const generateSummary = async () => {
  if (!courseId.value) {
    ElMessage.error(t("_courseChat.noCourseId"));
    return;
  }

  summarizing.value = true;
  summaryReady.value = false;
  error.value = "";

  try {
    const res = await http.post<httpNs.Response<any>>(`/course/${courseId.value}/summary`);
    const data = res.data || {};

    apiStats.value = {
      total_learning_minutes: data.total_learning_minutes || 0,
      total_chat_sessions: data.total_chat_sessions || 0,
      total_chat_messages: data.total_chat_messages || 0,
    };

    summary.value = parseSummaryContent(data);
    recentSessions.value = data.recent_sessions || [];

    summaryReady.value = true;
    ElMessage.success(t("_courseChat.summaryGenerated"));
  } catch (e: any) {
    error.value = e?.response?.data?.message || e?.message || t("_common.error");
    ElMessage.error(error.value);
  } finally {
    summarizing.value = false;
  }
};

const exportSummary = () => {
  let md = `# ${courseName.value} - ${t("_courseChat.summary")}\n\n`;
  summary.value.forEach(s => {
    md += `## ${s.title}\n\n${s.content.replace(/\n/g, "\n\n")}\n\n`;
  });
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${courseName.value}-${t("_courseChat.summary")}.md`;
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success(t("_courseChat.exportSuccess"));
};

const goBack = () => router.push({ name: "CourseDashboard" });

// ── Init ───────────────────────────────────────────
onMounted(async () => {
  loading.value = false; // UI ready immediately, summary generated on demand or auto
  if (courseId.value) {
    await generateSummary();
  }
});
</script>

<template>
  <div class="summary-page">
    <div class="summary-header">
      <el-button :icon="ArrowLeft" text style="color: #fff" @click="goBack">
        {{ $t("_courseChat.back") }}
      </el-button>
      <div class="header-center">
        <div class="magic-icon">
          <el-icon :size="20"><MagicStick /></el-icon>
        </div>
        <h2 class="header-title">{{ $t("_courseChat.summary") }}</h2>
      </div>
      <div class="header-right">
        <el-tag effect="light" round class="course-tag">{{ courseName }}</el-tag>
        <button v-if="summaryReady" class="header-export-btn" @click="exportSummary">
          <el-icon :size="14"><Download /></el-icon>
          <span>{{ $t("_courseChat.exportChat") }}</span>
        </button>
      </div>
    </div>

    <div class="summary-body">
      <div class="summary-main">
        <!-- Error -->
        <div v-if="error && !summarizing" class="summary-error">
          <el-icon :size="40" color="var(--tk-color-danger)"><WarningFilled /></el-icon>
          <p>{{ error }}</p>
          <el-button type="primary" @click="generateSummary">{{ $t("_courseChat.regenerateSummary") }}</el-button>
        </div>

        <!-- Loading / Generating -->
        <div v-else-if="summarizing" class="summary-loading">
          <div class="loading-spinner">
            <div class="magic-icon-lg">
              <el-icon :size="40" class="is-loading"><MagicStick /></el-icon>
            </div>
          </div>
          <p class="loading-text">{{ $t("_courseChat.generatingSummary") }}</p>
          <p class="loading-hint">{{ $t("_courseChat.extractingKeywords") }}</p>
        </div>

        <!-- Summary Content -->
        <div v-else-if="summaryReady" class="summary-content">
          <!-- API stats row -->
          <div class="stat-row">
            <div class="stat-card">
              <div class="stat-icon" style="--color: #3b82f6">
                <el-icon :size="20"><Clock /></el-icon>
              </div>
              <div class="stat-info">
                <span class="stat-num">{{ apiStats.total_learning_minutes }}</span>
                <span class="stat-label">{{ $t("_courseChat.learningMinutes") }}</span>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon" style="--color: #22c55e">
                <el-icon :size="20"><Reading /></el-icon>
              </div>
              <div class="stat-info">
                <span class="stat-num">{{ apiStats.total_chat_sessions }}</span>
                <span class="stat-label">{{ $t("_courseChat.totalSessions") }}</span>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon" style="--color: #8b5cf6">
                <el-icon :size="20"><Collection /></el-icon>
              </div>
              <div class="stat-info">
                <span class="stat-num">{{ apiStats.total_chat_messages }}</span>
                <span class="stat-label">{{ $t("_courseChat.totalMessages") }}</span>
              </div>
            </div>
          </div>

          <!-- Summary sections -->
          <div v-for="(section, idx) in summary" :key="section.title" class="section-card">
            <div class="section-header">
              <div class="section-icon" :style="{ '--color': sectionColors[idx] }">
                <el-icon :size="18"><component :is="sectionIcons[idx]" /></el-icon>
              </div>
              <h3 class="section-title">{{ section.title }}</h3>
            </div>
            <div v-if="section.content" class="section-body" :style="{ borderLeftColor: sectionBorders[idx] }">
              <template v-if="idx === 3">
                <span v-for="kp in section.content.split(' · ').filter(Boolean)" :key="kp" class="kp-tag">
                  {{ kp.trim() }}
                </span>
              </template>
              <template v-else>
                <div v-for="(line, i) in section.content.split('\n').filter(Boolean)" :key="i" class="section-line">
                  <span class="line-num">{{ i + 1 }}</span>
                  <span>{{ line.replace(/^\d+\.\s*/, "") }}</span>
                </div>
              </template>
            </div>
            <div v-else class="section-body section-empty" :style="{ borderLeftColor: sectionBorders[idx] }">
              <span class="no-data-hint">{{ $t("_common.noData") }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="summary-sidebar">
        <div class="sidebar-card">
          <div class="sidebar-title">
            <el-icon :size="16"><Clock /></el-icon>
            <span>{{ $t("_courseChat.recentSessions") }}</span>
          </div>
          <div class="session-list">
            <template v-if="recentSessions.length">
              <div v-for="session in recentSessions" :key="session.id" class="session-item">
                <div class="session-dot" />
                <div class="session-info">
                  <span class="session-name">{{ session.title }}</span>
                  <div class="session-meta">
                    <span>{{ session.date }}</span>
                    <span class="session-msgs">{{ $t("_courseChat.messagesCount", { count: session.messages }) }}</span>
                  </div>
                </div>
              </div>
            </template>
            <span v-else class="no-data-hint">{{ $t("_common.noData") }}</span>
          </div>
        </div>

        <div class="sidebar-card">
          <div class="sidebar-title">
            <el-icon :size="16"><MagicStick /></el-icon>
            <span>{{ $t("_common.operation") }}</span>
          </div>
          <div class="sidebar-ops">
            <el-button type="primary" :loading="summarizing" style="width: 100%" @click="generateSummary">
              {{ summarizing ? $t("_courseChat.generating") : $t("_courseChat.regenerateSummary") }}
            </el-button>
            <el-button v-if="summaryReady" style="width: 100%" @click="exportSummary">
              <el-icon :size="14"><Download /></el-icon>
              <span>{{ $t("_courseChat.exportChat") }}</span>
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.summary-page {
  height: calc(100vh - 160px);
  min-height: 500px;
  background: var(--tk-surface-bg-color-page);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: linear-gradient(
    135deg,
    var(--tk-color-primary) 0%,
    color-mix(in srgb, var(--tk-color-primary) 70%, #7c3aed) 100%
  );
  border-radius: 12px 12px 0 0;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 10px;
}

.magic-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.25) 0%, rgba(255, 255, 255, 0.1) 100%);
  color: #fff;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.course-tag {
  background: rgba(255, 255, 255, 0.18) !important;
  color: #fff !important;
  border-color: rgba(255, 255, 255, 0.25) !important;
  backdrop-filter: blur(8px);
}

.header-export-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(8px);
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.5);
  }
}

// Body
.summary-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  background: var(--tk-surface-bg-color-page);
}

.summary-main {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

// Loading
.summary-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.loading-spinner {
  margin-bottom: 20px;
}

.magic-icon-lg {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--tk-color-primary) 10%, transparent);
  color: var(--tk-color-primary);
}

.loading-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--tk-gray-color-700);
  margin: 0 0 6px;
}

.loading-hint {
  font-size: 13px;
  color: var(--tk-gray-color-400);
  margin: 0;
}

// Error
.summary-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  p {
    margin: 0;
    color: var(--tk-gray-color-600);
  }
}

// Stat Cards
.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 10px;
  transition: all 0.25s cubic-bezier(0.22, 0.61, 0.36, 1);

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--tk-box-shadow-sm);
  }
}

.stat-icon {
  width: 42px;
  height: 42px;
  min-width: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--color) 12%, transparent);
  color: var(--color);
}

.stat-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: var(--tk-gray-color-900);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--tk-gray-color-500);
  margin-top: 2px;
}

// Section Cards
.section-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 14px;
  transition: box-shadow 0.25s cubic-bezier(0.22, 0.61, 0.36, 1);

  &:hover {
    box-shadow: var(--tk-box-shadow-sm);
  }
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.section-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--color) 12%, transparent);
  color: var(--color);
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0;
}

.section-body {
  font-size: 14px;
  line-height: 1.8;
  color: var(--tk-gray-color-700);
  padding-left: 16px;
  border-left: 3px solid var(--tk-surface-border-color);
}

.section-empty {
  color: var(--tk-gray-color-400);
  font-style: italic;
}

.no-data-hint {
  font-size: 13px;
  color: var(--tk-gray-color-400);
}

.section-line {
  display: flex;
  gap: 8px;
  padding: 4px 0;

  .line-num {
    min-width: 20px;
    font-weight: 600;
    color: var(--tk-gray-color-400);
    font-size: 12px;
    text-align: right;
    padding-top: 2px;
  }
}

.kp-tag {
  display: inline-block;
  padding: 4px 12px;
  margin: 3px 6px 3px 0;
  font-size: 13px;
  color: var(--tk-gray-color-700);
  background: color-mix(in srgb, var(--tk-color-primary) 6%, transparent);
  border-radius: 14px;
  transition: all 0.2s ease;

  &:hover {
    background: color-mix(in srgb, var(--tk-color-primary) 12%, transparent);
    color: var(--tk-color-primary);
  }
}

// Sidebar
.summary-sidebar {
  width: 250px;
  min-width: 250px;
  border-left: 1px solid var(--tk-surface-border-color);
  padding: 20px 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  background: var(--tk-surface-bg-color-box);
}

.sidebar-card {
  background: var(--tk-surface-bg-color-page);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 10px;
  padding: 16px;
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--tk-gray-color-800);
  margin-bottom: 12px;
}

.sidebar-ops {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

// Session List
.session-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;

  &:hover {
    background: var(--tk-gray-color-100);
  }
}

.session-dot {
  width: 8px;
  height: 8px;
  min-width: 8px;
  border-radius: 50%;
  background: var(--tk-color-primary);
  margin-top: 5px;
  opacity: 0.5;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-name {
  font-size: 13px;
  color: var(--tk-gray-color-700);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: var(--tk-gray-color-400);
  margin-top: 2px;
}

// Responsive
@media (max-width: 900px) {
  .stat-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .summary-sidebar {
    display: none;
  }
}

@media (max-width: 600px) {
  .stat-row {
    grid-template-columns: 1fr;
  }

  .summary-main {
    padding: 16px;
  }

  .summary-header {
    padding: 12px 16px;
  }

  .header-export-btn span {
    display: none;
  }
}
</style>
