<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { http } from "@/common/http";
import { BannerCard } from "@/components/card/banner-card";
import { ProgressCard } from "@/components/card/progress-card";
import { TimelineListCard } from "@/components/card/timeline-list-card";
import { DataListCard } from "@/components/card/data-list-card";
import { t } from "@/common/languages";

defineOptions({ name: "AdminDashboard" });

const router = useRouter();
const loading = ref(true);

// Dashboard aggregate data from API
interface DashboardData {
  user_count: number;
  teacher_count: number;
  student_count: number;
  course_count: number;
  active_course_count: number;
  file_count: number;
  today_chats: number;
  total_messages: number;
  pending_enrollments: number;
  system_days: number;
}

const dashboard = ref<DashboardData>({
  user_count: 0,
  teacher_count: 0,
  student_count: 0,
  course_count: 0,
  active_course_count: 0,
  file_count: 0,
  today_chats: 0,
  total_messages: 0,
  pending_enrollments: 0,
  system_days: 0,
});

// Course progress from courses list API
interface CourseInfo {
  id: number;
  name: string;
  teacher: { id: number; username: string } | null;
  description: string;
  chapters: number;
  is_active: boolean;
  created_at: string;
  student_count?: number;
  max_students?: number;
}

const courseStats = ref<{ name: string; teacher: string; students: number; maxStudents: number; progress: number }[]>(
  []
);

const stats = ref([
  {
    labelKey: "_route.AdminSystemUsers",
    value: 0,
    icon: "ep:user",
    colorVar: "color-primary",
    route: "/admin/users",
  },
  {
    labelKey: "_route.AdminActiveCourses",
    value: 0,
    icon: "ep:school",
    colorVar: "color-success",
    route: "/admin/courses",
  },
  {
    labelKey: "_route.AdminVectorFiles",
    value: 0,
    icon: "ep:folder",
    colorVar: "color-warning",
    route: "/admin/vector-db",
  },
  {
    labelKey: "_route.AdminTodayChats",
    value: 0,
    icon: "ep:chat-dot-round",
    colorVar: "color-secondary",
    route: "/course/chat-stats",
  },
]);

const quickStats = ref([
  { labelKey: "_route.AdminTeacherCount", value: "0" },
  { labelKey: "_route.AdminStudentCount", value: "0" },
  { labelKey: "_route.AdminTotalMessages", value: "0" },
  { labelKey: "_route.AdminNewUsersMonth", value: "0" },
  { labelKey: "_route.AdminSystemDays", value: "0" },
]);

const activityList = ref<{ time: string; status: string; content: string; code: string }[]>([]);

const pendingTaskList = ref<{ title: string; status: string; time: string; class: string; icon: string }[]>([]);

const updateStats = (data: DashboardData) => {
  // Top stat cards
  stats.value[0].value = data.user_count;
  stats.value[1].value = data.active_course_count;
  stats.value[2].value = data.file_count;
  stats.value[3].value = data.today_chats;
  stats.value = [...stats.value];

  // Quick stats
  quickStats.value[0].value = String(data.teacher_count);
  quickStats.value[1].value = String(data.student_count);
  quickStats.value[2].value = data.total_messages.toLocaleString();
  quickStats.value[3].value = String(data.pending_enrollments);
  quickStats.value[4].value = String(data.system_days);
  quickStats.value = [...quickStats.value];

  // Pending tasks
  pendingTaskList.value = [
    {
      title: t("_route.AdminEnrollPending"),
      status: t("_route.AdminEnrollPendingDesc", { n: data.pending_enrollments }),
      time: "",
      class: "task-warning",
      icon: "ep:warning",
    },
  ];

  // Activity list (synthesized from dashboard stats)
  const nowStr = t("_common.justNow");
  activityList.value = [
    {
      time: nowStr,
      status: "var(--tk-color-primary)",
      content: t("_route.AdminActivityUsers", { n: data.user_count }),
      code: "stats",
    },
    {
      time: nowStr,
      status: "var(--tk-color-success)",
      content: t("_route.AdminActivityCourses", { n: data.active_course_count }),
      code: "stats",
    },
    {
      time: nowStr,
      status: "var(--tk-color-warning)",
      content: t("_route.AdminActivityFiles", { n: data.file_count }),
      code: "stats",
    },
    {
      time: nowStr,
      status: "var(--tk-color-primary)",
      content: t("_route.AdminActivityTodayChats", { n: data.today_chats }),
      code: "stats",
    },
    {
      time: nowStr,
      status: "var(--tk-color-secondary)",
      content: t("_route.AdminActivityTotalMsgs", { n: data.total_messages.toLocaleString() }),
      code: "stats",
    },
    {
      time: nowStr,
      status: "var(--tk-color-warning)",
      content: t("_route.AdminActivityEnrolls", { n: data.pending_enrollments }),
      code: "stats",
    },
    {
      time: nowStr,
      status: "var(--tk-color-success)",
      content: t("_route.AdminActivityDays", { n: data.system_days }),
      code: "stats",
    },
    {
      time: nowStr,
      status: "var(--tk-color-primary)",
      content: t("_route.AdminActivityAllCourses", { n: data.course_count }),
      code: "stats",
    },
  ];
};

const loadCourses = async () => {
  try {
    const res = await http.get<httpNs.Response<{ list: CourseInfo[]; total: number }>>("/admin/courses", {
      params: { page: 1, pageSize: 100 },
    });
    const list = res.data?.list || [];
    courseStats.value = list.map(c => ({
      name: c.name,
      teacher: c.teacher_name || t("_common.unknown"),
      students: c.enrolled_count || 0,
      maxStudents: c.max_students || 30,
      progress: c.max_students ? Math.round(((c.enrolled_count || 0) / (c.max_students || 1)) * 100) : 0,
    }));
  } catch {
    courseStats.value = [];
  }
};

const loadDashboard = async () => {
  loading.value = true;
  try {
    const res = await http.get<httpNs.Response<DashboardData>>("/admin/dashboard");
    if (res.data) {
      dashboard.value = res.data;
      updateStats(res.data);
    }
  } catch {
    // Keep defaults on error
  }
  await loadCourses();
  loading.value = false;
};

onMounted(() => {
  loadDashboard();
});

const goToStat = (route: string) => router.push(route);

const getProgressColor = (progress: number) => {
  if (progress >= 80) return "var(--tk-color-success)";
  if (progress >= 50) return "var(--tk-color-primary)";
  return "var(--tk-color-warning)";
};

const goToCourses = () => router.push("/admin/courses");
</script>

<template>
  <div class="admin-dashboard" v-loading="loading">
    <!-- Welcome Banner -->
    <BannerCard
      :title="$t('_route.AdminCenter')"
      :subtitle="$t('_route.AdminWelcome')"
      :button-config="{
        show: true,
        text: $t('_route.AdminManageCourses'),
        color: '#ffffff',
        textColor: 'var(--tk-color-primary)',
        radius: '8px',
      }"
      background-color="var(--tk-color-primary)"
      height="10rem"
      @button-click="goToCourses"
    />

    <!-- Stats Row -->
    <el-row :gutter="20" class="stats-row">
      <el-col v-for="item in stats" :key="item.labelKey" :xs="12" :sm="6">
        <div class="stat-card" @click="goToStat(item.route)">
          <div class="stat-icon" :style="{ '--stat-color': `var(--tk-${item.colorVar})` }">
            <Icon :icon="item.icon" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ item.value.toLocaleString() }}</span>
            <span class="stat-label">{{ $t(item.labelKey) }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="24">
      <!-- Left Column: Main Content -->
      <el-col :xl="16" :lg="15" :xs="24">
        <!-- Course Progress Panel -->
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">
              <Icon icon="ep:trend-charts" :size="18" />
              <span>{{ $t("_route.AdminCourseProgress") }}</span>
            </div>
            <el-button text type="primary" size="small" @click="goToCourses">
              {{ $t("_route.AdminViewAllCourses") }}
            </el-button>
          </div>
          <div class="course-progress-grid" v-if="courseStats.length">
            <div v-for="course in courseStats" :key="course.name" class="course-progress-card">
              <div class="cpc-header">
                <div class="cpc-name">
                  <Icon icon="ep:notebook" :size="14" />
                  <span>{{ course.name }}</span>
                </div>
                <el-tag size="small" effect="plain" type="info">{{ course.teacher }}</el-tag>
              </div>
              <div class="cpc-progress">
                <ProgressCard
                  :percentage="course.progress"
                  :color="getProgressColor(course.progress)"
                  :stroke-width="6"
                  style="flex: 1"
                />
                <span class="cpc-percent">{{ course.progress }}%</span>
              </div>
              <div class="cpc-footer">
                <span>{{ course.students }}/{{ course.maxStudents }} {{ $t("_route.AdminStudents") }}</span>
                <span v-if="course.students >= course.maxStudents" class="full-badge">
                  {{ $t("_route.AdminFull") }}
                </span>
              </div>
            </div>
          </div>
          <div v-else class="empty-hint">
            {{ $t("_route.AdminNoCourseData") }}
          </div>
        </div>

        <!-- Activity Timeline -->
        <TimelineListCard
          :title="$t('_route.AdminSystemActivity')"
          :list="activityList"
          :max-count="5"
          style="margin-top: 24px"
        />
      </el-col>

      <!-- Right Column: Sidebar -->
      <el-col :xl="8" :lg="9" :xs="24">
        <!-- Pending Tasks -->
        <DataListCard :title="$t('_route.AdminPendingTasks')" :list="pendingTaskList" :max-count="3" />

        <!-- Quick Stats -->
        <div class="panel" style="margin-top: 24px">
          <div class="panel-header">
            <div class="panel-title">
              <Icon icon="ep:data-analysis" :size="18" />
              <span>{{ $t("_route.AdminDataOverview") }}</span>
            </div>
          </div>
          <div class="quick-stats">
            <div v-for="item in quickStats" :key="item.labelKey" class="quick-stat-item">
              <span class="qs-label">{{ $t(item.labelKey) }}</span>
              <span class="qs-value">{{ item.value }}</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style lang="scss" scoped>
.admin-dashboard {
  padding: 4px 0;
}

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

// Panel
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
  margin-bottom: 20px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
}

// Course Progress Grid
.course-progress-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.course-progress-card {
  padding: 16px;
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 8px;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;

  &:hover {
    border-color: var(--tk-color-primary);
    box-shadow: var(--tk-box-shadow-sm);
  }
}

.cpc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.cpc-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 500;
  color: var(--tk-gray-color-800);
}

.cpc-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.cpc-percent {
  font-size: 13px;
  font-weight: 600;
  color: var(--tk-gray-color-700);
  min-width: 34px;
}

.cpc-footer {
  font-size: 12px;
  color: var(--tk-gray-color-500);
  display: flex;
  justify-content: space-between;
}

.full-badge {
  color: var(--tk-color-danger);
  font-size: 12px;
}

// Quick Stats
.quick-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.quick-stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.qs-label {
  font-size: 12px;
  color: var(--tk-gray-color-500);
}

.qs-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
}

.empty-hint {
  text-align: center;
  color: var(--tk-gray-color-500);
  padding: 40px 0;
  font-size: 14px;
}

@media (max-width: 768px) {
  .course-progress-grid {
    grid-template-columns: 1fr;
  }
}
</style>
