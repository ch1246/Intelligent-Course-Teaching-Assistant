<script setup lang="ts">
import type { FormInstance } from "element-plus";
import { ref, computed, reactive, useTemplateRef, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Refresh, Plus, Edit, Delete, Upload, School } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "AdminCourses" });

const router = useRouter();

// Backend Course fields: id, name, description, teacher (object), chapters, is_active, created_at
interface ManagedCourse {
  id: number;
  name: string;
  teacher: { id: number; username: string } | null;
  description: string;
  chapters: number;
  is_active: boolean;
  created_at: string;
  student_count?: number;
  max_students?: number;
  files_count?: number;
  total_messages?: number;
}

const courses = ref<ManagedCourse[]>([]);
const total = ref(0);
const loading = ref(false);

const searchKeyword = ref("");
const statusFilter = ref("");
const currentPage = ref(1);
const pageSize = ref(8);

// Dialog
const dialogVisible = ref(false);
const dialogTitle = ref(t("_course.createCourse"));
const dialogMode = ref<"create" | "edit">("create");
const editingCourseId = ref<number | null>(null);
const courseFormRef = useTemplateRef<FormInstance>("courseFormRef");
const courseForm = reactive({
  name: "",
  description: "",
  chapters: 8,
  is_active: true,
  teacher_id: null as number | null,
  cover_gradient: "",
  icon: "Notebook",
  semester: "fall",
  year: new Date().getFullYear(),
});

// Teacher list for dropdown
const teachers = ref<{ id: number; username: string }[]>([]);

// Fetch teachers for dropdown
const fetchTeachers = async () => {
  try {
    const res = await http.get<httpNs.Response<{ id: number; username: string }[]>>("/admin/courses/teachers");
    teachers.value = res.data || (res as any).data || [];
  } catch {
    teachers.value = [];
  }
};

// Fetch courses from API
const fetchCourses = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      pageSize: pageSize.value,
    };
    if (searchKeyword.value) params.search = searchKeyword.value;
    if (statusFilter.value) params.status = statusFilter.value;

    const res = await http.get<httpNs.Response<{ list: ManagedCourse[]; total: number }>>("/admin/courses", {
      params,
    });
    if (res.data) {
      courses.value = res.data.list || [];
      total.value = res.data.total || 0;
    }
  } catch {
    courses.value = [];
    total.value = 0;
  }
  loading.value = false;
};

onMounted(() => {
  fetchTeachers();
  fetchCourses();
});

const handlePageChange = (page: number) => {
  currentPage.value = page;
  fetchCourses();
};

const handlePageSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  fetchCourses();
};

const handleSearch = () => {
  currentPage.value = 1;
  fetchCourses();
};

const handleRefresh = () => {
  searchKeyword.value = "";
  statusFilter.value = "";
  currentPage.value = 1;
  fetchCourses();
};

const handleStatusFilterChange = () => {
  currentPage.value = 1;
  fetchCourses();
};

// Stat computed values (from server-side totals and current page)
const totalCourses = computed(() => total.value);
const activeCourses = computed(() => courses.value.filter(c => c.is_active).length);
const totalStudents = computed(() => courses.value.reduce((s, c) => s + (c.enrolled_count || 0), 0));
const totalMessages = computed(() => courses.value.reduce((s, c) => s + (c.total_messages || 0), 0));

const getStatusTag = (isActive: boolean) => (isActive ? "success" : "info");

const toggleStatus = async (course: ManagedCourse) => {
  const actionKey = course.is_active ? "archive" : "activate";
  const actionText = t(`_course.${actionKey}`);
  await ElMessageBox.confirm(
    t("_course.confirmToggle", { action: actionText, name: course.name }),
    t("_headerBar.logout.confirmTitle"),
    { type: "warning" }
  );
  try {
    await http.put(`/admin/courses/${course.id}`, {
      name: course.name,
      description: course.description,
      teacher: course.teacher,
      chapters: course.chapters,
      is_active: !course.is_active,
    });
    course.is_active = !course.is_active;
    ElMessage.success(t("_course.toggled", { action: actionText, name: course.name }));
  } catch {
    ElMessage.error(t("_course.toggleFailed"));
  }
};

const deleteCourse = async (course: ManagedCourse) => {
  await ElMessageBox.confirm(t("_course.confirmDelete", { name: course.name }), t("_headerBar.logout.confirmTitle"), {
    type: "error",
  });
  try {
    await http.delete(`/admin/courses/${course.id}`);
    courses.value = courses.value.filter(c => c.id !== course.id);
    total.value = Math.max(0, total.value - 1);
    ElMessage.success(t("_course.deleted"));
  } catch {
    ElMessage.error(t("_course.deleteFailed"));
  }
};

const openCreateDialog = () => {
  dialogTitle.value = t("_course.createCourse");
  dialogMode.value = "create";
  editingCourseId.value = null;
  courseForm.name = "";
  courseForm.description = "";
  courseForm.chapters = 8;
  courseForm.is_active = true;
  courseForm.teacher_id = null;
  courseForm.cover_gradient = "";
  courseForm.icon = "Notebook";
  courseForm.semester = "fall";
  courseForm.year = new Date().getFullYear();
  dialogVisible.value = true;
};

const openEditDialog = (course: ManagedCourse) => {
  dialogTitle.value = t("_course.editCourse");
  dialogMode.value = "edit";
  editingCourseId.value = course.id;
  courseForm.name = course.name;
  courseForm.description = course.description;
  courseForm.chapters = course.chapters;
  courseForm.is_active = course.is_active;
  courseForm.teacher_id = course.teacher || null;
  courseForm.cover_gradient = (course as any).cover_gradient || "";
  courseForm.icon = (course as any).icon || "Notebook";
  courseForm.semester = (course as any).semester || "fall";
  courseForm.year = (course as any).year || new Date().getFullYear();
  dialogVisible.value = true;
};

const submitting = ref(false);

const submitCourse = async () => {
  if (!courseFormRef.value) return;
  await courseFormRef.value.validate(async valid => {
    if (!valid) return;
    submitting.value = true;
    try {
      if (dialogMode.value === "create") {
        await http.post("/admin/courses", {
          name: courseForm.name,
          description: courseForm.description,
          teacher: courseForm.teacher_id,
          chapters: courseForm.chapters,
          is_active: courseForm.is_active,
          cover_gradient: courseForm.cover_gradient,
          icon: courseForm.icon,
          semester: courseForm.semester,
          year: courseForm.year,
        });
        ElMessage.success(t("_course.createSuccess"));
      } else {
        await http.put(`/admin/courses/${editingCourseId.value}`, {
          name: courseForm.name,
          description: courseForm.description,
          teacher: courseForm.teacher_id,
          chapters: courseForm.chapters,
          is_active: courseForm.is_active,
          cover_gradient: courseForm.cover_gradient,
          icon: courseForm.icon,
          semester: courseForm.semester,
          year: courseForm.year,
        });
        ElMessage.success(t("_course.updateSuccess"));
      }
      dialogVisible.value = false;
      fetchCourses();
    } catch {
      ElMessage.error(t("_course.submitFailed"));
    }
    submitting.value = false;
  });
};

const formRules = {
  name: [{ required: true, message: t("_course.nameRequired"), trigger: "blur" }],
  description: [{ required: true, message: t("_course.descRequired"), trigger: "blur" }],
};

const goToEnrollReview = () => {
  router.push("/admin/enroll-review");
};

const importRoster = () => ElMessage.info(t("_user.importTip"));
</script>

<template>
  <div class="admin-courses-page">
    <!-- Page Header with gradient accent -->
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t("_route.AdminCourses") }}</h2>
        <span class="page-sub">{{ $t("_course.totalCourses", { count: total }) }}</span>
      </div>
      <el-button type="primary" :icon="School" class="enroll-review-btn" @click="goToEnrollReview">
        {{ $t("_course.enrollReview") }}
      </el-button>
    </div>

    <!-- Stats Summary Row -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card card-accent-purple">
          <div class="stat-accent-bar" />
          <div class="stat-icon" :style="{ '--stat-color': '#7c3aed' }">
            <Icon icon="ep:notebook" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ totalCourses }}</span>
            <span class="stat-label">{{ $t("_course.totalCoursesLabel") }}</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card card-accent-green">
          <div class="stat-accent-bar" />
          <div class="stat-icon" :style="{ '--stat-color': 'var(--tk-color-success)' }">
            <Icon icon="ep:circle-check" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ activeCourses }}</span>
            <span class="stat-label">{{ $t("_course.activeCoursesLabel") }}</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card card-accent-amber">
          <div class="stat-accent-bar" />
          <div class="stat-icon" :style="{ '--stat-color': 'var(--tk-color-warning)' }">
            <Icon icon="ep:user" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ totalStudents }}</span>
            <span class="stat-label">{{ $t("_course.totalStudentsLabel") }}</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card card-accent-slate">
          <div class="stat-accent-bar" />
          <div class="stat-icon" :style="{ '--stat-color': '#64748b' }">
            <Icon icon="ep:chat-dot-round" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ totalMessages.toLocaleString() }}</span>
            <span class="stat-label">{{ $t("_course.totalMessagesLabel") }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Toolbar card -->
    <div class="content-card toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchKeyword"
            :placeholder="$t('_course.searchPlaceholder')"
            :prefix-icon="Search"
            clearable
            style="width: 280px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
          <el-select
            v-model="statusFilter"
            :placeholder="$t('_course.filterByStatus')"
            clearable
            style="width: 120px"
            @change="handleStatusFilterChange"
          >
            <el-option :label="$t('_course.active')" value="active" />
            <el-option :label="$t('_course.archived')" value="archived" />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button :icon="Refresh" text @click="handleRefresh">
            {{ $t("_course.refresh") }}
          </el-button>
          <el-button :icon="Upload" @click="importRoster">{{ $t("_course.importRoster") }}</el-button>
          <el-button :icon="Plus" type="primary" @click="openCreateDialog">
            {{ $t("_course.createCourse") }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Table card -->
    <div class="content-card table-card" v-loading="loading">
      <el-table :data="courses" stripe border style="width: 100%">
        <el-table-column prop="name" :label="$t('_course.courseName')" min-width="180">
          <template #default="{ row }">
            <div class="course-name-cell">
              <Icon icon="ep:school" :size="16" class="course-icon" />
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_course.teacher')" width="100">
          <template #default="{ row }">
            {{ row.teacher_name || "-" }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('_course.studentCount')" width="100" align="center">
          <template #default="{ row }">
            <span
              :style="{
                color: (row.enrolled_count || 0) >= (row.max_students || 999) ? 'var(--tk-color-danger)' : '',
                fontWeight: (row.enrolled_count || 0) >= (row.max_students || 999) ? '600' : '',
              }"
            >
              {{ row.enrolled_count || 0 }}/{{ row.max_students || "-" }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="chapters" :label="$t('_course.chapters')" width="75" align="center" />
        <el-table-column :label="$t('_course.filesCount')" width="70" align="center">
          <template #default="{ row }">
            {{ row.files_count ?? 0 }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('_course.messagesCount')" width="90" align="center" sortable>
          <template #default="{ row }">
            {{ (row.total_messages || 0).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('_course.status')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.is_active)" size="small" effect="light">
              {{ row.is_active ? $t("_course.active") : $t("_course.archived") }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="$t('_course.createTime')" width="110" />
        <el-table-column :label="$t('_course.actions')" width="230" align="center" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button :icon="Edit" text type="primary" size="small" @click="openEditDialog(row)">
                {{ $t("_course.edit") }}
              </el-button>
              <el-button text :type="row.is_active ? 'warning' : 'success'" size="small" @click="toggleStatus(row)">
                {{ row.is_active ? $t("_course.archive") : $t("_course.activate") }}
              </el-button>
              <el-button :icon="Delete" text type="danger" size="small" @click="deleteCourse(row)">
                {{ $t("_course.delete") }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[8, 15, 25]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form ref="courseFormRef" :model="courseForm" :rules="formRules" label-width="80px">
        <el-form-item :label="$t('_course.courseName')" prop="name">
          <el-input v-model="courseForm.name" :placeholder="$t('_course.nameRequired')" />
        </el-form-item>
        <el-form-item :label="$t('_course.teacher')">
          <el-select
            v-model="courseForm.teacher_id"
            :placeholder="$t('_course.teacherRequired')"
            style="width: 100%"
            clearable
          >
            <el-option v-for="t in teachers" :key="t.id" :label="t.username" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('_course.description')" prop="description">
          <el-input
            v-model="courseForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('_course.descRequired')"
          />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="$t('_course.chapterCount')">
              <el-input-number v-model="courseForm.chapters" :min="1" :max="30" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="$t('_course.semester')">
              <el-select v-model="courseForm.semester" style="width: 100%">
                <el-option :label="$t('_course.fallSemester')" value="fall" />
                <el-option :label="$t('_course.springSemester')" value="spring" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="$t('_course.schoolYear')">
              <el-input-number v-model="courseForm.year" :min="2020" :max="2035" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item :label="$t('_common.coverGradient')">
          <el-input
            v-model="courseForm.cover_gradient"
            placeholder="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
          />
        </el-form-item>
        <el-form-item :label="$t('_common.cardIcon')">
          <el-select v-model="courseForm.icon" :placeholder="$t('_course.selectIcon')" style="width: 100%">
            <el-option label="📓 Notebook" value="Notebook" />
            <el-option label="🏫 School" value="School" />
            <el-option label="✨ MagicStick" value="MagicStick" />
            <el-option label="💻 Monitor" value="Monitor" />
            <el-option label="🔗 Connection" value="Connection" />
            <el-option label="💬 ChatDotRound" value="ChatDotRound" />
            <el-option label="🖼 Picture" value="Picture" />
            <el-option label="📊 DataAnalysis" value="DataAnalysis" />
            <el-option label="🧭 Compass" value="Compass" />
            <el-option label="🖥 Platform" value="Platform" />
            <el-option label="📖 Reading" value="Reading" />
            <el-option label="⚙️ Cpu" value="Cpu" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t("_course.cancel") }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCourse">{{ $t("_course.confirm") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.admin-courses-page {
  padding: 4px 0;
}

// Page Header
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
  padding-left: 14px;
  position: relative;

  &::before {
    content: "";
    position: absolute;
    left: 0;
    top: 3px;
    bottom: 3px;
    width: 4px;
    border-radius: 2px;
    background: linear-gradient(135deg, var(--tk-color-primary), var(--tk-color-success));
  }
}

.page-sub {
  font-size: 13px;
  color: var(--tk-gray-color-500);
  margin-left: 14px;
}

// Gradient enroll review button
.enroll-review-btn {
  border: none;
  background: linear-gradient(135deg, var(--tk-color-warning), #f0a020);
  color: #fff;
  font-weight: 500;
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: var(--tk-box-shadow-md);
    background: linear-gradient(135deg, var(--tk-color-warning), #f0a020);
    opacity: 0.92;
  }
}

// Stats Row
.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  box-shadow: var(--tk-box-shadow-xs);
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--tk-box-shadow-md);
  }
}

.stat-accent-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.card-accent-purple .stat-accent-bar {
  background: linear-gradient(90deg, #7c3aed, #a78bfa);
}

.card-accent-green .stat-accent-bar {
  background: linear-gradient(90deg, #16a34a, #4ade80);
}

.card-accent-amber .stat-accent-bar {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

.card-accent-slate .stat-accent-bar {
  background: linear-gradient(90deg, #475569, #94a3b8);
}

.stat-icon {
  --stat-color: var(--tk-color-primary);
  width: 46px;
  height: 46px;
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
  font-size: 22px;
  font-weight: 700;
  color: var(--tk-gray-color-900);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--tk-gray-color-500);
  white-space: nowrap;
}

// Content Cards
.content-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  box-shadow: var(--tk-box-shadow-xs);
  padding: 20px;
}

.toolbar-card {
  margin-bottom: 16px;
}

.table-card {
  padding: 16px 20px 20px;
}

// Toolbar
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

// Course name cell
.course-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.course-icon {
  color: var(--tk-color-primary);
  flex-shrink: 0;
}

// Action Buttons
.action-btns {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

// Pagination
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
