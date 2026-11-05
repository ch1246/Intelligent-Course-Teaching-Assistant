<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { School, Notebook, Check, Star, Clock, User, Search } from "@element-plus/icons-vue";
import { storeToRefs } from "pinia";
import { useUserStore } from "@/pinia";
import { http } from "@/common/http";
import { t } from "@/common/languages";

defineOptions({ name: "CourseEnroll" });

const userStore = useUserStore();
const { userInfo } = storeToRefs(userStore);

// ── Types ──────────────────────────────────────────
interface CatalogCourse {
  id: number;
  name: string;
  description: string;
  teacher: string;
  schedule: string;
  maxStudents: number;
  enrolledCount: number;
  coverGradient: string;
  icon: any;
  tags: string[];
  college: string;
  major: string;
  grade: string;
  semester: string;
}

// ── State ──────────────────────────────────────────
const loading = ref(true);
const error = ref("");
const catalogCourses = ref<CatalogCourse[]>([]);
const enrolledIds = ref<Set<number>>(new Set());
const enrolling = ref<Set<number>>(new Set());
const currentPage = ref(1);
const pageSize = ref(6);

// ── Filter options (derived from data) ─────────────
const colleges = computed(() => [...new Set(catalogCourses.value.map(c => c.college).filter(Boolean))]);
const majors = computed(() => [...new Set(catalogCourses.value.map(c => c.major).filter(Boolean))]);
const grades = computed(() => [...new Set(catalogCourses.value.map(c => c.grade).filter(Boolean))]);
const semesters = computed(() => [...new Set(catalogCourses.value.map(c => c.semester).filter(Boolean))]);

// ── User-aware defaults ────────────────────────────
const userCollege = computed(() => userInfo.value.dept || "");
const userMajor = computed(() => userInfo.value.major || "");
const userRoles = computed(() => userInfo.value.roles || []);

const isStudent = computed(
  () =>
    userRoles.value.includes("student") || (!userRoles.value.includes("admin") && !userRoles.value.includes("teacher"))
);
const userCollegeExists = computed(() => (userCollege.value ? colleges.value.includes(userCollege.value) : false));
const shouldDefaultFilter = computed(() => isStudent.value && userCollegeExists.value);

const searchKeyword = ref("");
const filterCollege = ref(""); // set after load
const filterMajor = ref("");
const filterGrade = ref("");
const filterSemester = ref("");

const filteredMajors = computed(() => {
  if (!filterCollege.value) return majors.value;
  const coursesInCollege = catalogCourses.value.filter(c => c.college === filterCollege.value);
  return [...new Set(coursesInCollege.map(c => c.major))];
});

const filteredCourses = computed(() => {
  let list = catalogCourses.value;

  if (filterCollege.value) list = list.filter(c => c.college === filterCollege.value);
  if (filterMajor.value) list = list.filter(c => c.major === filterMajor.value);
  if (filterGrade.value) list = list.filter(c => c.grade === filterGrade.value);
  if (filterSemester.value) list = list.filter(c => c.semester === filterSemester.value);
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase();
    list = list.filter(
      c =>
        c.name.toLowerCase().includes(kw) ||
        c.description.toLowerCase().includes(kw) ||
        c.teacher.toLowerCase().includes(kw) ||
        c.college.toLowerCase().includes(kw)
    );
  }

  // Sort hot courses first when no filter active
  if (
    !filterCollege.value &&
    !filterMajor.value &&
    !filterGrade.value &&
    !filterSemester.value &&
    !searchKeyword.value
  ) {
    list = [...list].sort((a, b) => {
      const aHot = a.tags.includes("hot") ? -1 : 0;
      const bHot = b.tags.includes("hot") ? -1 : 0;
      return aHot - bHot;
    });
  }

  return list;
});

const paginatedCourses = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredCourses.value.slice(start, start + pageSize.value);
});

const clearFilters = () => {
  searchKeyword.value = "";
  filterCollege.value = "";
  filterMajor.value = "";
  filterGrade.value = "";
  filterSemester.value = "";
};

watch([searchKeyword, filterCollege, filterMajor, filterGrade, filterSemester], () => {
  currentPage.value = 1;
});

const isEnrolled = (courseId: number) => enrolledIds.value.has(courseId);
const isFull = (course: CatalogCourse) => course.enrolledCount >= course.maxStudents;

const getTagType = (tag: string): string => {
  const map: Record<string, string> = {
    required: "danger",
    elective: "primary",
    hot: "warning",
    full: "danger",
    projectPractice: "success",
    cuttingEdge: "",
    new: "info",
  };
  return map[tag] ?? "info";
};

const getCapacityColor = (course: CatalogCourse): string => {
  const ratio = course.enrolledCount / course.maxStudents;
  if (ratio >= 1) return "var(--tk-color-danger)";
  if (ratio >= 0.85) return "var(--tk-color-warning)";
  return "var(--tk-color-success)";
};

const handleEnroll = async (course: CatalogCourse) => {
  if (isEnrolled(course.id)) {
    ElMessage.warning(t("_courseEnroll.alreadyEnrolled"));
    return;
  }
  if (isFull(course)) {
    ElMessage.warning(t("_courseEnroll.courseFull"));
    return;
  }

  enrolling.value.add(course.id);
  try {
    await http.post("/course/enroll", { course_id: course.id });
    enrolledIds.value.add(course.id);
    ElMessage.success(t("_courseEnroll.applySuccess", { name: course.name }));
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.message || t("_common.error"));
  } finally {
    enrolling.value.delete(course.id);
  }
};

// ── Map raw API course → UI shape ──────────────────
const mapCatalogCourse = (c: any): CatalogCourse => ({
  id: c.id,
  name: c.name,
  description: c.description || "",
  teacher: c.teacher_name || "",
  scheduleSlots: (c.schedule_slots || []).map((s: any) => ({
    weekday: s.weekday,
    weekday_label: s.weekday_label || s.label || "",
    start_time: (s.start_time || "").substring(0, 5),
    end_time: (s.end_time || "").substring(0, 5),
    week_start: s.week_start || 1,
    week_end: s.week_end || 18,
    location: s.location || "",
  })),
  maxStudents: c.max_students ?? c.capacity ?? 0,
  enrolledCount: c.enrolled_count ?? c.enrolledCount ?? 0,
  schedule:
    (c.schedule_slots || [])
      .map((s: any) =>
        `${s.weekday_label || ""} ${(s.start_time || "").substring(0, 5)}-${(s.end_time || "").substring(0, 5)} ${s.location || ""}`.trim()
      )
      .filter(Boolean)
      .join("；") || "",
  coverGradient: c.cover_gradient || `linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)`,
  icon: Notebook,
  tags: [],
  college: c.college || "",
  major: c.major || "",
  grade: c.grade || "",
  semester: c.semester || "",
});

// ── Init ───────────────────────────────────────────
onMounted(async () => {
  loading.value = true;
  error.value = "";
  try {
    // Load available courses（学生可见的课程目录）
    const coursesRes = await http.get<httpNs.Response<any>>("/course/catalog");
    const rawCourses: any[] = coursesRes.data || [];
    catalogCourses.value = rawCourses.map(mapCatalogCourse);

    // Load my enrollments
    const enrollRes = await http.get<httpNs.Response<any[]>>("/course/enroll");
    const enrollList: any[] = enrollRes.data || [];
    enrolledIds.value = new Set(enrollList.map((e: any) => e.course));

    // Set default filter after data is loaded
    if (shouldDefaultFilter.value) {
      filterCollege.value = userCollege.value;
      if (userMajor.value && majors.value.includes(userMajor.value)) {
        filterMajor.value = userMajor.value;
      }
    }
  } catch (e: any) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="course-enroll">
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

    <!-- Header -->
    <div class="enroll-hero">
      <div class="hero-bg" />
      <div class="hero-content">
        <div class="hero-text">
          <h1 class="hero-title">{{ $t("_courseEnroll.title") }}</h1>
          <p class="hero-sub">{{ $t("_courseEnroll.subtitle") }}</p>
        </div>
        <div class="hero-stats">
          <div class="hero-stat">
            <span class="hero-stat-num">{{ filteredCourses.length }}</span>
            <span class="hero-stat-label">{{ $t("_courseEnroll.totalCourses") }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="filter-row">
        <el-input
          v-model="searchKeyword"
          :placeholder="$t('_courseEnroll.searchPlaceholder')"
          :prefix-icon="Search"
          clearable
          class="filter-search"
        />
        <el-select
          v-model="filterCollege"
          :placeholder="$t('_courseEnroll.filterCollege')"
          clearable
          class="filter-select"
        >
          <el-option v-for="college in colleges" :key="college" :label="college" :value="college" />
        </el-select>
        <el-select v-model="filterMajor" :placeholder="$t('_courseEnroll.filterMajor')" clearable class="filter-select">
          <el-option v-for="major in filteredMajors" :key="major" :label="major" :value="major" />
        </el-select>
        <el-select v-model="filterGrade" :placeholder="$t('_courseEnroll.filterGrade')" clearable class="filter-select">
          <el-option v-for="grade in grades" :key="grade" :label="grade" :value="grade" />
        </el-select>
        <el-select
          v-model="filterSemester"
          :placeholder="$t('_courseEnroll.filterSemester')"
          clearable
          class="filter-select"
        >
          <el-option v-for="sem in semesters" :key="sem" :label="sem" :value="sem" />
        </el-select>
        <el-button text type="primary" @click="clearFilters">
          {{ $t("_common.reset") }}
        </el-button>
      </div>

      <!-- Active filter tags -->
      <div v-if="filterCollege || filterMajor || filterGrade || filterSemester" class="filter-tags">
        <el-tag v-if="filterCollege" closable size="small" @close="filterCollege = ''">
          {{ filterCollege }}
        </el-tag>
        <el-tag v-if="filterMajor" closable size="small" @close="filterMajor = ''">
          {{ filterMajor }}
        </el-tag>
        <el-tag v-if="filterGrade" closable size="small" @close="filterGrade = ''">
          {{ filterGrade }}
        </el-tag>
        <el-tag v-if="filterSemester" closable size="small" @close="filterSemester = ''">
          {{ filterSemester }}
        </el-tag>
      </div>

      <div class="filter-result">
        <span class="result-count">
          {{ $t("_courseEnroll.foundCourses", { count: filteredCourses.length }) }}
        </span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="32"><Search /></el-icon>
      <p>{{ $t("_common.loading") }}</p>
    </div>

    <!-- Course Grid -->
    <div v-else-if="paginatedCourses.length" class="course-grid">
      <div
        v-for="course in paginatedCourses"
        :key="course.id"
        class="course-card"
        :class="{ 'card-full': isFull(course) && !isEnrolled(course.id), 'card-enrolled': isEnrolled(course.id) }"
      >
        <!-- Left accent bar -->
        <div class="card-accent" :style="{ background: course.coverGradient }" />

        <div class="card-main">
          <!-- Top: icon + name + tags -->
          <div class="card-top">
            <div class="card-icon" :style="{ background: course.coverGradient }">
              <el-icon :size="22" color="#fff">
                <component :is="course.icon" />
              </el-icon>
            </div>
            <div class="card-title-row">
              <h3 class="card-name">{{ course.name }}</h3>
              <div class="card-tags">
                <el-tag v-for="tag in course.tags" :key="tag" size="small" :type="getTagType(tag)" effect="light" round>
                  {{ $t("_courseEnroll." + tag) }}
                </el-tag>
              </div>
            </div>
          </div>

          <!-- Description -->
          <p class="card-desc">{{ course.description }}</p>

          <!-- Meta chips: college / major / grade / semester -->
          <div class="card-meta">
            <span class="meta-chip">{{ course.college }}</span>
            <span class="meta-divider">|</span>
            <span class="meta-chip">{{ course.major }}</span>
            <span class="meta-divider">|</span>
            <span class="meta-chip">{{ course.grade }}</span>
            <span class="meta-divider">|</span>
            <span class="meta-chip">{{ course.semester }}</span>
          </div>

          <!-- Info rows -->
          <div class="card-info">
            <div class="info-item">
              <el-icon :size="15"><User /></el-icon>
              <span class="info-label">{{ $t("_courseEnroll.teacher") }}</span>
              <span class="info-value">{{ course.teacher }}</span>
            </div>
            <div class="info-item">
              <el-icon :size="15"><Clock /></el-icon>
              <span class="info-label">{{ $t("_courseEnroll.schedule") }}</span>
              <span class="info-value">{{ course.schedule }}</span>
            </div>
            <div class="info-item">
              <el-icon :size="15"><Star /></el-icon>
              <span class="info-label">{{ $t("_courseEnroll.capacity") }}</span>
              <span class="info-value" :style="{ color: getCapacityColor(course) }">
                {{ course.enrolledCount }} / {{ course.maxStudents }}
              </span>
              <span v-if="isFull(course) && !isEnrolled(course.id)" class="full-tag">
                {{ $t("_courseEnroll.full") }}
              </span>
            </div>
          </div>

          <!-- Progress + Action -->
          <div class="card-footer">
            <div class="progress-wrap">
              <el-progress
                :percentage="Math.round((course.enrolledCount / course.maxStudents) * 100)"
                :stroke-width="6"
                :show-text="false"
                :color="isFull(course) && !isEnrolled(course.id) ? 'var(--tk-color-danger)' : 'var(--tk-color-primary)'"
              />
            </div>
            <el-button
              v-if="isEnrolled(course.id)"
              type="success"
              disabled
              :icon="Check"
              round
              size="small"
              class="action-btn"
            >
              {{ $t("_courseEnroll.enrolled") }}
            </el-button>
            <el-button v-else-if="isFull(course)" type="danger" disabled round size="small" class="action-btn">
              {{ $t("_courseEnroll.fullCapacity") }}
            </el-button>
            <el-button
              v-else
              type="primary"
              :loading="enrolling.has(course.id)"
              :icon="School"
              round
              size="small"
              class="action-btn"
              @click="handleEnroll(course)"
            >
              {{ $t("_courseEnroll.applyToJoin") }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="!loading && filteredCourses.length > pageSize" class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[6, 12, 18]"
        :total="filteredCourses.length"
        layout="total, sizes, prev, pager, next, jumper"
        background
      />
    </div>

    <!-- Empty -->
    <div v-else-if="!loading && !filteredCourses.length" class="empty-state">
      <el-icon :size="48" color="var(--tk-gray-color-300)"><Search /></el-icon>
      <p>{{ $t("_courseEnroll.noCourseFound") }}</p>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.course-enroll {
  padding: 4px 0;
}

// Loading
.loading-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--tk-gray-color-400);
  p {
    margin-top: 12px;
    font-size: 14px;
  }
}

// Hero Banner
.enroll-hero {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 20px;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #a855f7 100%);
  z-index: 0;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 32px;
}

.hero-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hero-title {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.hero-sub {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  margin: 0;
}

.hero-stats {
  display: flex;
  gap: 24px;
}

.hero-stat {
  text-align: center;
  padding: 10px 18px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  backdrop-filter: blur(8px);
}

.hero-stat-num {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  line-height: 1.1;
}

.hero-stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
}

// Filter Bar
.filter-bar {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-search {
  width: 220px;
}

.filter-select {
  width: 140px;
}

.filter-tags {
  display: flex;
  gap: 6px;
  margin-top: 12px;
}

.filter-result {
  margin-top: 12px;
}

.result-count {
  font-size: 13px;
  color: var(--tk-gray-color-500);
}

// Course Grid
.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

// Course Card
.course-card {
  display: flex;
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
  }

  &.card-full {
    opacity: 0.72;
  }
}

.card-accent {
  width: 5px;
  flex-shrink: 0;
}

.card-main {
  flex: 1;
  padding: 20px 22px;
  min-width: 0;
}

.card-top {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 10px;
}

.card-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-title-row {
  flex: 1;
  min-width: 0;
}

.card-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 6px;
  line-height: 1.2;
}

.card-tags {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.card-desc {
  font-size: 13px;
  color: var(--tk-gray-color-500);
  line-height: 1.5;
  margin: 0 0 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

// Meta chips (college / major / grade / semester)
.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.meta-chip {
  font-size: 11px;
  color: var(--tk-color-primary);
  background: color-mix(in srgb, var(--tk-color-primary) 8%, transparent);
  padding: 2px 8px;
  border-radius: 4px;
}

.meta-divider {
  font-size: 11px;
  color: var(--tk-gray-color-300);
}

// Info
.card-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 14px;
  padding: 10px 14px;
  background: var(--tk-surface-bg-color-page);
  border-radius: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--tk-gray-color-600);

  .el-icon {
    color: var(--tk-gray-color-400);
    flex-shrink: 0;
  }
}

.info-label {
  color: var(--tk-gray-color-400);
  flex-shrink: 0;

  &::after {
    content: "：";
  }
}

.info-value {
  color: var(--tk-gray-color-700);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.full-tag {
  margin-left: auto;
  font-size: 11px;
  color: #fff;
  background: var(--tk-color-danger);
  padding: 1px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}

// Footer
.card-footer {
  display: flex;
  align-items: center;
  gap: 14px;
}

.progress-wrap {
  flex: 1;
}

.action-btn {
  flex-shrink: 0;
}

// Pagination
.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

// Empty state
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--tk-gray-color-400);
  font-size: 14px;

  p {
    margin-top: 12px;
  }
}

@media (max-width: 768px) {
  .hero-content {
    flex-direction: column;
    gap: 16px;
  }

  .filter-row {
    flex-direction: column;

    .filter-search,
    .filter-select {
      width: 100%;
    }
  }

  .course-grid {
    grid-template-columns: 1fr;
  }
}
.schedule-item {
  align-items: flex-start !important;
}
.schedule-slots {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}
.schedule-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  flex-wrap: wrap;
}
.slot-time {
  color: var(--tk-gray-color-700);
  font-weight: 500;
  white-space: nowrap;
}
.slot-weeks {
  color: var(--tk-color-primary);
  background: color-mix(in srgb, var(--tk-color-primary) 8%, transparent);
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
}
.slot-location {
  color: var(--tk-gray-color-500);
  white-space: nowrap;
}
</style>
