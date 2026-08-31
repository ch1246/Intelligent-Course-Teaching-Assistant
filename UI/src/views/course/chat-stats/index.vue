<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ChatDotRound, TrendCharts } from "@element-plus/icons-vue";
import { http } from "@/common/http";
import { BarChart } from "@/components/chart/bar-chart";

defineOptions({ name: "CourseChatStats" });

// ── Types ──────────────────────────────────────────
interface ChatStatItem {
  courseId: number | string;
  courseName: string;
  totalMessages: number;
  questions: number;
  avgPerDay: string;
  lastChat: string;
  topTopics: string[];
}

// ── State ──────────────────────────────────────────
const loading = ref(true);
const error = ref("");
const chatData = ref<ChatStatItem[]>([]);

const expandedCourse = ref<string | null>(null);
const toggleExpand = (courseName: string) => {
  expandedCourse.value = expandedCourse.value === courseName ? null : courseName;
};

// ── Derived ────────────────────────────────────────
const totalMessages = computed(() => chatData.value.reduce((s, c) => s + c.totalMessages, 0));
const totalQuestions = computed(() => chatData.value.reduce((s, c) => s + c.questions, 0));
const totalAvgPerDay = computed(() => chatData.value.reduce((s, c) => s + parseFloat(c.avgPerDay || "0"), 0));

const maxMessages = computed(() => Math.max(...chatData.value.map(c => c.totalMessages), 1));

const chartXData = computed(() => chatData.value.map(c => c.courseName));
const chartMessageData = computed(() => chatData.value.map(c => c.totalMessages));
const chartQuestionData = computed(() => chatData.value.map(c => c.questions));

const statItems = computed(() => [
  {
    label: "_courseStats.totalChats",
    value: totalMessages.value,
    icon: "ep:chat-dot-round",
    colorVar: "color-primary",
  },
  {
    label: "_courseStats.totalQuestions",
    value: totalQuestions.value,
    icon: "ep:question-filled",
    colorVar: "color-success",
  },
  {
    label: "_courseStats.dailyAvgChats",
    value: parseFloat(totalAvgPerDay.value.toFixed(1)),
    icon: "ep:trend-charts",
    colorVar: "color-warning",
  },
]);

// ── Helpers ────────────────────────────────────────
const computeAvgPerDay = (dailyStats: { date: string; count: number }[]): string => {
  if (!dailyStats || dailyStats.length === 0) return "0";
  const total = dailyStats.reduce((s, d) => s + (d.count || 0), 0);
  return (total / dailyStats.length).toFixed(1);
};

const getLastChat = (dailyStats: { date: string; count: number }[]): string => {
  if (!dailyStats || dailyStats.length === 0) return "";
  const dates = dailyStats
    .map(d => d.date)
    .filter(Boolean)
    .sort();
  return dates[dates.length - 1] || "";
};

// ── Init ───────────────────────────────────────────
onMounted(async () => {
  loading.value = true;
  error.value = "";
  try {
    // 1. Load my courses
    const coursesRes = await http.get<httpNs.Response<any[]>>("/course/my-courses");
    const courses: any[] = coursesRes.data || [];

    if (courses.length === 0) {
      chatData.value = [];
      return;
    }

    // 2. Load chat-stats for each course
    const statsResults = await Promise.allSettled(
      courses.map(c => http.get<httpNs.Response<any>>(`/course/${c.id}/chat-stats`))
    );

    chatData.value = courses
      .map((course, idx) => {
        const result = statsResults[idx];
        const stats = result.status === "fulfilled" ? result.value?.data || {} : {};
        const dailyStats: any[] = stats.daily_stats || [];
        const skillStats: any[] = stats.skill_stats || [];

        return {
          courseId: course.id,
          courseName: course.name,
          totalMessages: stats.total_messages || 0,
          questions: stats.total_questions || 0,
          avgPerDay: computeAvgPerDay(dailyStats),
          lastChat: getLastChat(dailyStats),
          topTopics: skillStats
            .slice(0, 3)
            .map((s: any) => s.label || s.name || "")
            .filter(Boolean),
        } as ChatStatItem;
      })
      .filter(c => c.totalMessages > 0 || c.courseName); // keep all courses
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="chat-stats-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t("_courseStats.chatStats") }}</h2>
        <span class="page-sub">{{ $t("_courseStats.chatStatsDesc") }}</span>
      </div>
    </div>

    <!-- Error -->
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      show-icon
      closable
      style="margin-bottom: 16px"
      @close="error = ''"
    />

    <!-- Loading -->
    <template v-if="loading">
      <el-row :gutter="20" class="summary-row">
        <el-col v-for="i in 3" :key="i" :xs="8" :sm="8">
          <div class="stat-card skeleton-line" style="height: 88px" />
        </el-col>
      </el-row>
      <div class="panel chart-panel skeleton-line" style="height: 340px" />
    </template>

    <template v-else>
      <!-- Summary Cards -->
      <el-row :gutter="20" class="summary-row">
        <el-col v-for="item in statItems" :key="item.label" :xs="8" :sm="8">
          <div class="stat-card">
            <div class="stat-icon" :style="{ '--stat-color': `var(--tk-${item.colorVar})` }">
              <Icon :icon="item.icon" :size="22" />
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ item.value }}</span>
              <span class="stat-label">{{ $t(item.label) }}</span>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- Bar Chart: Messages & Questions per Course -->
      <div v-if="chatData.length" class="panel chart-panel">
        <div class="panel-title">
          <el-icon :size="18"><TrendCharts /></el-icon>
          <span>{{ $t("_courseStats.chatComparison") }}</span>
        </div>
        <BarChart
          :data="[
            { name: $t('_courseStats.chatCountSeries'), data: chartMessageData },
            { name: $t('_courseStats.questionCountSeries'), data: chartQuestionData },
          ]"
          :x-axis-data="chartXData"
          height="300px"
          :show-axis-label="true"
          :show-axis-line="true"
          :show-split-line="true"
          :show-legend="true"
          bar-width="35%"
          :border-radius="[6, 6, 0, 0]"
        />
      </div>

      <!-- Chat Breakdown -->
      <div v-if="chatData.length" class="section-title">
        <el-icon :size="18"><ChatDotRound /></el-icon>
        <span>{{ $t("_courseStats.courseDetailTitle") }}</span>
      </div>

      <div v-if="chatData.length" class="chat-list">
        <div
          v-for="item in chatData"
          :key="item.courseName"
          class="chat-card"
          :class="{ 'is-expanded': expandedCourse === item.courseName }"
        >
          <div class="chat-card-header" @click="toggleExpand(item.courseName)">
            <div class="chat-card-left">
              <span class="chat-course-name">{{ item.courseName }}</span>
              <div class="chat-bar-wrap">
                <div class="chat-bar" :style="{ width: (item.totalMessages / maxMessages) * 100 + '%' }" />
              </div>
            </div>
            <div class="chat-card-right">
              <span class="chat-count">{{ $t("_courseStats.timesCount", { count: item.totalMessages }) }}</span>
              <el-icon :class="{ expanded: expandedCourse === item.courseName }">
                <TrendCharts />
              </el-icon>
            </div>
          </div>

          <div v-if="expandedCourse === item.courseName" class="chat-detail">
            <div class="chat-detail-grid">
              <div class="detail-item">
                <span class="detail-label">{{ $t("_courseStats.questions") }}</span>
                <span class="detail-value">{{ $t("_courseStats.itemsCount", { count: item.questions }) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">{{ $t("_courseStats.dailyAvg") }}</span>
                <span class="detail-value">{{ $t("_courseStats.timesCount", { count: item.avgPerDay }) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">{{ $t("_courseStats.lastChat") }}</span>
                <span class="detail-value">{{ item.lastChat || $t("_common.noData") }}</span>
              </div>
            </div>
            <div v-if="item.topTopics.length" class="top-topics">
              <span class="topics-label">{{ $t("_courseStats.hotTopics") }}</span>
              <el-tag v-for="topic in item.topTopics" :key="topic" size="small" type="info" effect="light" round>
                {{ topic }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty -->
      <div v-if="!chatData.length" class="empty-state">
        <el-icon :size="48" color="var(--tk-gray-color-300)"><ChatDotRound /></el-icon>
        <p>{{ $t("_common.noData") }}</p>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.chat-stats-page {
  padding: 4px 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 4px;
}

.page-sub {
  font-size: 13px;
  color: var(--tk-gray-color-500);
}

.summary-row {
  margin-bottom: 24px;
}

// Skeleton
.skeleton-line {
  background: linear-gradient(
    90deg,
    var(--tk-surface-bg-color-box) 25%,
    var(--tk-gray-color-100) 50%,
    var(--tk-surface-bg-color-box) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 12px;
}
@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

// Inline stat cards
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--tk-box-shadow-md);
  }
}

.stat-icon {
  --stat-color: var(--tk-color-primary);
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--stat-color) 12%, transparent);
  color: var(--stat-color);
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--tk-gray-color-900);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--tk-gray-color-500);
  white-space: nowrap;
}

// Chart Panel
.chart-panel {
  margin-bottom: 28px;
}

.panel {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 24px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin-bottom: 16px;
}

// Section
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin-bottom: 16px;
}

// Empty
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--tk-gray-color-400);
  p {
    margin-top: 12px;
    font-size: 14px;
  }
}

// Chat Cards
.chat-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: var(--tk-box-shadow-sm);
  }

  &.is-expanded {
    box-shadow: var(--tk-box-shadow-md);
  }
}

.chat-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  transition: background-color 0.15s;

  &:hover {
    background: color-mix(in srgb, var(--tk-color-primary) 4%, transparent);
  }
}

.chat-card-left {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-width: 0;
  margin-right: 16px;
}

.chat-course-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--tk-gray-color-900);
}

.chat-bar-wrap {
  height: 6px;
  background: var(--tk-gray-color-100);
  border-radius: 3px;
  overflow: hidden;
}

.chat-bar {
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--tk-color-primary),
    color-mix(in srgb, var(--tk-color-primary) 60%, transparent)
  );
  border-radius: 3px;
  transition: width 0.3s;
}

.chat-card-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.chat-count {
  font-size: 18px;
  font-weight: 700;
  color: var(--tk-color-primary);
}

.expanded {
  transform: rotate(180deg);
  transition: transform 0.2s;
}

.chat-detail {
  padding: 0 20px 16px;
  border-top: 1px solid var(--tk-surface-border-color);
  border-left: 3px solid var(--tk-color-primary);
  margin-left: 0;
}

.chat-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  padding: 14px 0;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-label {
  font-size: 12px;
  color: var(--tk-gray-color-500);
}

.detail-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--tk-gray-color-800);
}

.top-topics {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 4px;
}

.topics-label {
  font-size: 12px;
  color: var(--tk-gray-color-500);
}
</style>
