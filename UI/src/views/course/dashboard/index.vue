<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ArrowRight, Notebook } from "@element-plus/icons-vue";
import { useRouter } from "vue-router";
import { http } from "@/common/http";
import { ProgressCard } from "@/components/card/progress-card";
import { BannerCard } from "@/components/card/banner-card";
import { DataListCard } from "@/components/card/data-list-card";
import { t } from "@/common/languages";

defineOptions({ name: "CourseDashboard" });

const router = useRouter();

// ── State ──────────────────────────────────────────
const loading = ref(true);
const error = ref("");
const courses = ref<any[]>([]);

// Dashboard aggregate stats per course
interface DashboardStat {
  course_name: string;
  student_count: number;
  session_count: number;
  message_count: number;
  file_count: number;
  today_minutes: number;
  total_minutes: number;
  progress: number;
  last_study_time: string;
}
const dashboardStats = ref<DashboardStat[]>([]);

// ── Derived stats ──────────────────────────────────
const stats = computed(() => {
  const enrolledCourses = courses.value.length;
  const totalMinutes = dashboardStats.value.reduce((s, d) => s + (d.total_minutes || 0), 0);
  const learningHours = (totalMinutes / 60).toFixed(1);
  const chatCount = dashboardStats.value.reduce((s, d) => s + (d.message_count || 0), 0);
  const knowledgeFiles = dashboardStats.value.reduce((s, d) => s + (d.file_count || 0), 0);

  return [
    {
      label: t("_courseDashboard.enrolledCourses"),
      value: enrolledCourses,
      icon: "ep:school",
      colorVar: "color-primary",
      route: "/course/enroll",
    },
    {
      label: t("_courseDashboard.learningHours"),
      value: learningHours,
      icon: "ep:clock",
      colorVar: "color-success",
      route: "/course/learning-time",
    },
    {
      label: t("_courseDashboard.chatCount"),
      value: chatCount,
      icon: "ep:chat-dot-round",
      colorVar: "color-warning",
      route: "/course/chat-stats",
    },
    {
      label: t("_courseDashboard.knowledgeFiles"),
      value: knowledgeFiles,
      icon: "ep:folder",
      colorVar: "color-secondary",
      route: "/file-management",
    },
  ];
});

// ── Sidebar data ──
const weakPoints = ref<string[]>([]);
const suggestionList = ref<any[]>([]);
const paperList = ref<any[]>([]);

const loadSidebar = async () => {
  try {
    const res = await http.get<
      httpNs.Response<{
        weak_points: string[];
        suggestions: any[];
        papers: any[];
      }>
    >("/course/my-sidebar");
    if (res.data) {
      weakPoints.value = res.data.weak_points || [];
      suggestionList.value = res.data.suggestions || [];
      paperList.value = res.data.papers || [];
    }
  } catch {
    // sidebar data is non-critical, fail silently
  }
};

// ── Helpers ────────────────────────────────────────
const goToStat = (route: string | null) => {
  if (route) router.push(route);
};

const goToChat = (course: { id: number; name: string }) => {
  router.push({ name: "CourseChat", params: { courseId: course.id }, query: { name: course.name } });
};

const getProgressColor = (progress: number) => {
  if (progress >= 80) return "var(--tk-color-success)";
  if (progress >= 50) return "var(--tk-color-primary)";
  return "var(--tk-color-warning)";
};

const getButtonColor = (coverColor: string) => {
  return coverColor.replace("--tk-bg-", "--tk-color-");
};

// ── Map raw API course → UI shape ──────────────────
const mapCourse = (c: any) => ({
  id: c.id,
  name: c.name,
  description: c.description || "",
  coverColor: c.cover_color || "var(--tk-bg-primary)",
  coverGradient: c.cover_gradient || "",
  chapters: c.chapters ?? 0,
  progress: c.progress ?? 0,
  lastStudyTime: c.last_study_time || "",
  icon: c.icon || Notebook,
});

// ── Init ───────────────────────────────────────────
onMounted(async () => {
  loading.value = true;
  error.value = "";
  try {
    // 1. Load enrolled courses
    const coursesRes = await http.get<httpNs.Response<any[]>>("/course/my-courses");
    const rawCourses: any[] = coursesRes.data || [];
    courses.value = rawCourses.map(mapCourse);

    // 2. Load per-course dashboard (for stats + course card data)
    if (courses.value.length > 0) {
      const dashboardResults = await Promise.allSettled(
        courses.value.map(c => http.get<httpNs.Response<DashboardStat>>(`/course/${c.id}/dashboard`))
      );
      dashboardResults.forEach((r, idx) => {
        if (r.status === "fulfilled" && r.value?.data) {
          dashboardStats.value.push(r.value.data as DashboardStat);
          // Patch progress & lastStudyTime into the course card
          const ds = r.value.data as DashboardStat;
          courses.value[idx].progress = ds.progress ?? 0;
          courses.value[idx].lastStudyTime = ds.last_study_time || "";
        }
      });
    }

    // 3. Load sidebar data (weak points, suggestions, papers)
    loadSidebar();
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="course-dashboard">
    <!-- Error banner -->
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      show-icon
      closable
      style="margin-bottom: 16px"
      @close="error = ''"
    />

    <!-- Loading skeleton -->
    <template v-if="loading">
      <div
        style="height: 10rem; background: var(--tk-surface-bg-color-box); border-radius: 14px; margin-bottom: 24px"
      />
      <el-row :gutter="20" class="stats-row">
        <el-col v-for="i in 4" :key="i" :xs="12" :sm="6">
          <div class="stat-card skeleton-line" style="height: 88px" />
        </el-col>
      </el-row>
    </template>

    <template v-else>
      <!-- Welcome Banner -->
      <BannerCard
        :title="$t('_courseDashboard.myCourses')"
        :subtitle="$t('_courseDashboard.welcomeSubtitle')"
        :button-config="{
          show: true,
          text: $t('_courseDashboard.applyCourse'),
          color: '#ffffff',
          textColor: 'var(--tk-color-primary)',
          radius: '8px',
        }"
        background-color="var(--tk-color-primary)"
        height="10rem"
        @button-click="router.push({ name: 'CourseEnroll' })"
      />

      <!-- Stats Row -->
      <el-row :gutter="20" class="stats-row">
        <el-col v-for="item in stats" :key="item.label" :xs="12" :sm="6">
          <div class="stat-card" @click="goToStat(item.route)">
            <div class="stat-icon" :style="{ '--stat-color': `var(--tk-${item.colorVar})` }">
              <Icon :icon="item.icon" :size="22" />
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ item.value }}</span>
              <span class="stat-label">{{ item.label }}</span>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- Main Content -->
      <el-row :gutter="24" class="main-row">
        <!-- Course Cards Grid -->
        <el-col :xl="16" :lg="15" :xs="24">
          <div class="section-header">
            <h2 class="section-title">{{ $t("_courseDashboard.myCourses") }}</h2>
            <span class="section-sub">{{ $t("_courseDashboard.courseCount", { count: courses.length }) }}</span>
          </div>
          <div v-if="courses.length === 0" class="empty-state">
            <p>{{ $t("_courseDashboard.noCourses") }}</p>
          </div>
          <div v-else class="course-grid">
            <div v-for="course in courses" :key="course.id" class="course-card" @click="goToChat(course)">
              <div
                class="course-cover"
                :style="{
                  background:
                    course.coverGradient ||
                    `linear-gradient(135deg, ${course.coverColor} 0%, color-mix(in srgb, ${course.coverColor} 60%, #1a1a2e) 100%)`,
                }"
              >
                <div class="cover-pattern" />
                <el-icon :size="40" class="cover-icon">
                  <component :is="course.icon" />
                </el-icon>
              </div>
              <div class="course-body">
                <h3 class="course-name">{{ course.name }}</h3>
                <p class="course-desc">{{ course.description }}</p>
                <div class="course-meta">
                  <span class="meta-item">
                    <el-icon :size="14"><Notebook /></el-icon>
                    {{ $t("_courseDashboard.chapters", { count: course.chapters }) }}
                  </span>
                  <span class="meta-item">{{ $t("_courseDashboard.lastStudy", { time: course.lastStudyTime }) }}</span>
                </div>
                <div class="course-footer">
                  <div class="progress-wrap">
                    <ProgressCard
                      :percentage="course.progress"
                      :color="getProgressColor(course.progress)"
                      :stroke-width="6"
                      style="flex: 1"
                    />
                    <span class="progress-text" :style="{ color: getProgressColor(course.progress) }">
                      {{ course.progress }}%
                    </span>
                  </div>
                  <el-button
                    :icon="ArrowRight"
                    text
                    size="small"
                    class="enter-btn"
                    :style="{
                      color: getButtonColor(course.coverColor),
                      '--enter-color': getButtonColor(course.coverColor),
                    }"
                    @click.stop="goToChat(course)"
                  >
                    {{ $t("_courseDashboard.enterChat") }}
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </el-col>

        <!-- Learning Recommendations Sidebar -->
        <el-col :xl="8" :lg="9" :xs="24">
          <div class="sidebar-cards">
            <!-- 学情分析 -->
            <div class="panel">
              <div class="panel-header">
                <div class="panel-title">
                  <Icon icon="ep:trend-charts" :size="18" />
                  <span>{{ $t("_courseDashboard.learningAnalysis") }}</span>
                </div>
              </div>
              <span class="weak-label">{{ $t("_courseDashboard.weakKnowledgePoints") }}</span>
              <div class="weak-tags">
                <template v-if="weakPoints.length">
                  <el-tag v-for="point in weakPoints" :key="point" size="small" type="warning" effect="light" round>
                    {{ point }}
                  </el-tag>
                </template>
                <span v-else class="no-data-hint">{{ $t("_common.noData") }}</span>
              </div>
            </div>

            <!-- 学习建议 -->
            <DataListCard :title="$t('_courseDashboard.studySuggestions')" :list="suggestionList" :max-count="3" />

            <!-- 推荐论文 -->
            <DataListCard :title="$t('_courseDashboard.recommendedPapers')" :list="paperList" :max-count="3" />
          </div>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.course-dashboard {
  padding: 4px 0;
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
  border-radius: 10px;
}
@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

// Stats Row
.stats-row {
  margin-top: 24px;
  margin-bottom: 28px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 10px;
  cursor: pointer;
  transition:
    transform 0.2s,
    box-shadow 0.2s;

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

.main-row {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0;
}

.section-sub {
  font-size: 14px;
  color: var(--tk-gray-color-600);
}

.empty-state {
  text-align: center;
  padding: 48px 20px;
  color: var(--tk-gray-color-400);
}
.no-data-hint {
  font-size: 13px;
  color: var(--tk-gray-color-400);
}

// Course Grid
.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.course-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition:
    transform 0.25s cubic-bezier(0.22, 0.61, 0.36, 1),
    box-shadow 0.25s cubic-bezier(0.22, 0.61, 0.36, 1);

  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--tk-box-shadow-lg);

    .cover-icon {
      transform: scale(1.1);
    }

    .enter-btn {
      opacity: 1;
      transform: translateX(0);
    }
  }
}

.course-cover {
  position: relative;
  height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.cover-pattern {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 50%, rgb(255 255 255 / 10%) 0%, transparent 50%),
    radial-gradient(circle at 80% 50%, rgb(255 255 255 / 5%) 0%, transparent 50%);
}

.cover-icon {
  position: relative;
  z-index: 1;
  color: rgb(255 255 255 / 90%);
  filter: drop-shadow(0 2px 4px rgb(0 0 0 / 20%));
  transition: transform 0.3s cubic-bezier(0.22, 0.61, 0.36, 1);
}

.course-body {
  padding: 18px 20px 20px;
}

.course-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 6px;
}

.course-desc {
  font-size: 13px;
  color: var(--tk-gray-color-600);
  line-height: 1.5;
  margin: 0 0 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.course-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--tk-gray-color-500);
  margin-bottom: 14px;

  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.course-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.progress-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-text {
  font-size: 13px;
  font-weight: 600;
  min-width: 34px;
}

.enter-btn {
  opacity: 0.85;
  transform: translateX(-4px);
  transition:
    opacity 0.25s,
    transform 0.25s,
    background 0.25s;

  &:hover {
    opacity: 1;
    background: color-mix(in srgb, var(--enter-color) 8%, transparent) !important;
  }
}

// Sidebar
.sidebar-cards {
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: sticky;
  top: 24px;
}

.panel {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 10px;
  padding: 24px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
}

.weak-label {
  font-size: 13px;
  color: var(--tk-gray-color-600);
  display: block;
  margin-bottom: 10px;
}

.weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

// DataListCard icon backgrounds
.sidebar-cards {
  :deep(.sg-review) {
    background: color-mix(in srgb, var(--tk-color-primary) 12%, transparent);
    color: var(--tk-color-primary);
  }

  :deep(.sg-preview) {
    background: color-mix(in srgb, var(--tk-color-success) 12%, transparent);
    color: var(--tk-color-success);
  }

  :deep(.sg-practice) {
    background: color-mix(in srgb, var(--tk-color-warning) 12%, transparent);
    color: var(--tk-color-warning);
  }

  :deep(.pp-main) {
    background: color-mix(in srgb, var(--tk-color-secondary) 12%, transparent);
    color: var(--tk-color-secondary);
  }
}

// Responsive
@media (max-width: 768px) {
  .course-grid {
    grid-template-columns: 1fr;
  }

  .stat-card {
    padding: 14px;
    gap: 12px;
  }

  .stat-icon {
    width: 40px;
    height: 40px;
  }

  .stat-value {
    font-size: 20px;
  }
}
</style>
