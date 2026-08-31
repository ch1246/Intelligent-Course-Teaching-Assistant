<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Clock, TrendCharts, Notebook } from "@element-plus/icons-vue";
import { http } from "@/common/http";
import { ProgressCard } from "@/components/card/progress-card";
import { BarChart } from "@/components/chart/bar-chart";

defineOptions({ name: "CourseLearningTime" });

// ── Types ──────────────────────────────────────────
interface ChapterItem {
  name: string;
  hours: number;
  progress: number;
}

interface TimeDataItem {
  courseId: number | string;
  courseName: string;
  totalHours: number;
  weeklyAvg: string;
  lastStudyTime: string;
  chapters: ChapterItem[];
}

// ── State ──────────────────────────────────────────
const loading = ref(true);
const error = ref("");
const timeData = ref<TimeDataItem[]>([]);

const expandedCourse = ref<string | null>(null);
const toggleExpand = (courseName: string) => {
  expandedCourse.value = expandedCourse.value === courseName ? null : courseName;
};

// ── Derived ────────────────────────────────────────
const totalHours = computed(() => timeData.value.reduce((sum, c) => sum + c.totalHours, 0));
const totalWeeklyAvg = computed(() => timeData.value.reduce((sum, c) => sum + parseFloat(c.weeklyAvg || "0"), 0));

const chartXData = computed(() => timeData.value.map(c => c.courseName));
const chartData = computed(() => timeData.value.map(c => c.totalHours));

const statItems = computed(() => [
  {
    label: "_courseStats.totalHours",
    value: parseFloat(totalHours.value.toFixed(1)),
    icon: "ep:clock",
    colorVar: "color-primary",
  },
  {
    label: "_courseStats.courseCount",
    value: timeData.value.length,
    icon: "ep:notebook",
    colorVar: "color-success",
  },
  {
    label: "_courseStats.weeklyAvg",
    value: parseFloat(totalWeeklyAvg.value.toFixed(1)),
    icon: "ep:trend-charts",
    colorVar: "color-warning",
    description: "h",
  },
]);

const getProgressColor = (progress: number) => {
  if (progress >= 80) return "var(--tk-color-success)";
  if (progress >= 40) return "var(--tk-color-primary)";
  return "var(--tk-color-warning)";
};

// ── Helpers ────────────────────────────────────────
const computeWeeklyAvg = (records: { date: string; duration_minutes: number }[]): string => {
  if (!records || records.length === 0) return "0";
  const total = records.reduce((s, r) => s + (r.duration_minutes || 0), 0);
  // Simple average: total / number of days, then / 60 for hours
  const avgHours = total / records.length / 60;
  return avgHours.toFixed(1);
};

const getLastStudyTime = (records: { date: string; duration_minutes: number }[]): string => {
  if (!records || records.length === 0) return "";
  const dates = records
    .map(r => r.date)
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
      timeData.value = [];
      return;
    }

    // 2. Load learning-time for each course
    const statsResults = await Promise.allSettled(
      courses.map(c => http.get<httpNs.Response<any>>(`/course/${c.id}/learning-time`))
    );

    timeData.value = courses.map((course, idx) => {
      const result = statsResults[idx];
      const data = result.status === "fulfilled" ? result.value?.data || {} : {};
      const records: any[] = data.records || [];
      const totalMinutes = data.total_minutes || 0;

      return {
        courseId: course.id,
        courseName: course.name,
        totalHours: totalMinutes / 60,
        weeklyAvg: computeWeeklyAvg(records),
        lastStudyTime: getLastStudyTime(records),
        chapters: [] as ChapterItem[], // chapter breakdown not in this API
      } as TimeDataItem;
    });
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="learning-time-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t("_courseStats.learningTimeTitle") }}</h2>
        <span class="page-sub">{{ $t("_courseStats.learningTimeDesc") }}</span>
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
        <el-col v-for="i in 3" :key="i" :xs="12" :sm="8">
          <div class="stat-card skeleton-line" style="height: 88px" />
        </el-col>
      </el-row>
      <div class="panel chart-panel skeleton-line" style="height: 320px" />
    </template>

    <template v-else>
      <!-- Summary Cards -->
      <el-row :gutter="20" class="summary-row">
        <el-col v-for="item in statItems" :key="item.label" :xs="12" :sm="8">
          <div class="stat-card">
            <div class="stat-icon" :style="{ '--stat-color': `var(--tk-${item.colorVar})` }">
              <Icon :icon="item.icon" :size="22" />
            </div>
            <div class="stat-info">
              <span class="stat-value">
                {{ item.value }}
                <span v-if="item.description" class="stat-unit">{{ item.description }}</span>
              </span>
              <span class="stat-label">{{ $t(item.label) }}</span>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- Bar Chart: Course Hours -->
      <div v-if="timeData.length" class="panel chart-panel">
        <div class="panel-title">
          <el-icon :size="18"><TrendCharts /></el-icon>
          <span>{{ $t("_courseStats.hoursDistribution") }}</span>
        </div>
        <BarChart
          :data="chartData"
          :x-axis-data="chartXData"
          height="280px"
          :show-axis-label="true"
          :show-axis-line="true"
          :show-split-line="true"
          bar-width="40%"
          :border-radius="[6, 6, 0, 0]"
        />
      </div>

      <!-- Course Time Breakdown -->
      <div v-if="timeData.length" class="section-title">
        <el-icon :size="18"><Clock /></el-icon>
        <span>{{ $t("_courseStats.chapterDetails") }}</span>
      </div>
      <div v-if="timeData.length" class="course-time-list">
        <div v-for="item in timeData" :key="item.courseName" class="course-time-card">
          <div class="ctc-header" @click="toggleExpand(item.courseName)">
            <div class="ctc-header-left">
              <div
                class="ctc-bar"
                :style="{ width: totalHours > 0 ? (item.totalHours / totalHours) * 100 + '%' : '0%' }"
              />
              <span class="ctc-name">{{ item.courseName }}</span>
            </div>
            <div class="ctc-header-right">
              <span class="ctc-hours">{{ item.totalHours.toFixed(1) }}h</span>
              <el-icon :class="{ expanded: expandedCourse === item.courseName }">
                <TrendCharts />
              </el-icon>
            </div>
          </div>

          <div v-if="expandedCourse === item.courseName" class="ctc-detail">
            <div class="ctc-meta">
              <span>{{ $t("_courseStats.weeklyAvgValue", { hours: item.weeklyAvg + "h" }) }}</span>
              <span v-if="item.lastStudyTime">{{ $t("_courseStats.lastStudy", { time: item.lastStudyTime }) }}</span>
            </div>
            <div v-if="item.chapters.length" class="ctc-chapters">
              <div v-for="ch in item.chapters" :key="ch.name" class="chapter-item">
                <div class="chapter-info">
                  <el-icon :size="14"><Notebook /></el-icon>
                  <span class="chapter-name">{{ ch.name }}</span>
                </div>
                <div class="chapter-progress">
                  <ProgressCard
                    :percentage="ch.progress"
                    :color="getProgressColor(ch.progress)"
                    :stroke-width="6"
                    style="flex: 1"
                  />
                  <span class="chapter-hours">{{ $t("_courseStats.hours", { hours: ch.hours }) }}</span>
                  <span class="chapter-pct">{{ $t("_courseStats.progress", { progress: ch.progress }) }}</span>
                </div>
              </div>
            </div>
            <div v-else class="ctc-no-chapters">
              <span class="no-data-hint">{{ $t("_courseStats.autoRecordHint") }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty -->
      <div v-if="!timeData.length" class="empty-state">
        <el-icon :size="48" color="var(--tk-gray-color-300)"><Clock /></el-icon>
        <p>{{ $t("_courseStats.autoRecordHint") }}</p>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.learning-time-page {
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

.stat-unit {
  font-size: 14px;
  font-weight: 400;
  color: var(--tk-gray-color-500);
  margin-left: 2px;
}

.stat-label {
  font-size: 13px;
  color: var(--tk-gray-color-500);
  white-space: nowrap;
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
.no-data-hint {
  font-size: 13px;
  color: var(--tk-gray-color-400);
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

// Course Time Cards
.course-time-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.course-time-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: var(--tk-box-shadow-sm);
  }
}

.ctc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  transition: background-color 0.15s;
  position: relative;

  &:hover {
    background: color-mix(in srgb, var(--tk-color-primary) 4%, transparent);
  }
}

.ctc-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 0;
}

.ctc-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--tk-color-primary) 10%, transparent),
    color-mix(in srgb, var(--tk-color-primary) 4%, transparent)
  );
  border-radius: 12px 0 0 12px;
  transition: width 0.3s;
  z-index: 0;
}

.ctc-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--tk-gray-color-900);
  position: relative;
  z-index: 1;
}

.ctc-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.ctc-hours {
  font-size: 20px;
  font-weight: 700;
  color: var(--tk-color-primary);
}

.expanded {
  transform: rotate(180deg);
  transition: transform 0.2s;
}

.ctc-detail {
  padding: 0 20px 16px;
  border-top: 1px solid var(--tk-surface-border-color);
}

.ctc-meta {
  display: flex;
  gap: 20px;
  padding: 12px 0;
  font-size: 13px;
  color: var(--tk-gray-color-600);
}

.ctc-no-chapters {
  padding: 12px 0;
}

.ctc-record {
  padding-top: 8px;
}

.ctc-chapters {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chapter-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  background: var(--tk-bg-color);
  border-radius: 8px;
}

.chapter-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--tk-gray-color-700);
}

.chapter-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chapter-hours {
  font-size: 12px;
  font-weight: 600;
  color: var(--tk-gray-color-700);
  min-width: 32px;
}

.chapter-pct {
  font-size: 12px;
  color: var(--tk-gray-color-500);
  min-width: 34px;
  text-align: right;
}

@media (max-width: 768px) {
  .ctc-meta {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
