<script setup lang="ts">
import type { FormInstance } from "element-plus";
import { ref, computed, reactive, useTemplateRef, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Refresh, Upload, Download, Edit, Delete, Plus } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "AdminUsers" });

// Backend User fields: id, username, email, phone, role, sex, age, dept, major, grade, is_active, date_joined
interface SystemUser {
  id: number;
  username: string;
  email: string;
  phone: string;
  role: string;
  dept: string;
  major: string;
  grade: string;
  is_active: boolean;
  date_joined: string;
  last_login?: string;
  course_count?: number;
}

const users = ref<SystemUser[]>([]);
const total = ref(0);
const loading = ref(false);

const searchKeyword = ref("");
const roleFilter = ref("");
const statusFilter = ref("");
const selectedUsers = ref<number[]>([]);
const currentPage = ref(1);
const pageSize = ref(8);

// Dialog
const dialogVisible = ref(false);
const dialogTitle = ref(t("_user.addUser"));
const dialogMode = ref<"add" | "edit">("add");
const editingUserId = ref<number | null>(null);
const userFormRef = useTemplateRef<FormInstance>("userFormRef");
const userForm = reactive({
  username: "",
  role: "student",
  email: "",
  phone: "",
  dept: "",
  major: "",
  grade: "",
  is_active: true,
});

const roleOptions = ["admin", "teacher", "student"];

// Fetch users from API
const fetchUsers = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      pageSize: pageSize.value,
    };
    if (searchKeyword.value) params.search = searchKeyword.value;
    if (roleFilter.value) params.role = roleFilter.value;
    if (statusFilter.value) params.status = statusFilter.value;

    const res = await http.get<httpNs.Response<{ list: SystemUser[]; total: number; page: number; pageSize: number }>>(
      "/admin/users",
      { params }
    );
    if (res.data) {
      users.value = res.data.list || [];
      total.value = res.data.total || 0;
    }
  } catch {
    users.value = [];
    total.value = 0;
  }
  loading.value = false;
};

onMounted(() => {
  fetchUsers();
});

// Re-fetch when pagination changes
const handlePageChange = (page: number) => {
  currentPage.value = page;
  fetchUsers();
};

const handlePageSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  fetchUsers();
};

// Search (debounced via manual trigger)
const handleSearch = () => {
  currentPage.value = 1;
  fetchUsers();
};

const handleRefresh = () => {
  searchKeyword.value = "";
  roleFilter.value = "";
  statusFilter.value = "";
  currentPage.value = 1;
  fetchUsers();
};

// Stat computed from total (server-side)
const totalUsers = computed(() => total.value);
const activeUsers = computed(() => users.value.filter(u => u.is_active).length);
const teacherUsers = computed(() => users.value.filter(u => u.role === "teacher").length);
const studentUsers = computed(() => users.value.filter(u => u.role === "student").length);

const getRoleTag = (role: string) => {
  const map: Record<string, string> = { admin: "danger", teacher: "warning", student: "info" };
  return map[role] || "info";
};

const getStatusTag = (isActive: boolean) => (isActive ? "success" : "danger");

const getInitials = (name: string) => name.slice(0, 1);

const toggleStatus = async (user: SystemUser) => {
  const actionKey = user.is_active ? "disable" : "enable";
  const actionText = t(`_user.${actionKey}`);
  await ElMessageBox.confirm(
    t("_user.confirmToggle", { action: actionText, name: user.username }),
    t("_headerBar.logout.confirmTitle"),
    { type: "warning" }
  );
  try {
    await http.put(`/admin/users/${user.id}`, {
      username: user.username,
      email: user.email,
      phone: user.phone,
      role: user.role,
      dept: user.dept,
      is_active: !user.is_active,
    });
    user.is_active = !user.is_active;
    ElMessage.success(t("_user.toggled", { action: actionText, name: user.username }));
  } catch {
    ElMessage.error(t("_user.toggleFailed"));
  }
};

const deleteUser = async (user: SystemUser) => {
  await ElMessageBox.confirm(t("_user.confirmDelete", { name: user.username }), t("_headerBar.logout.confirmTitle"), {
    type: "error",
  });
  try {
    await http.delete(`/admin/users/${user.id}`);
    users.value = users.value.filter(u => u.id !== user.id);
    total.value = Math.max(0, total.value - 1);
    ElMessage.success(t("_user.deleted"));
  } catch {
    ElMessage.error(t("_user.deleteFailed"));
  }
};

const batchDelete = async () => {
  if (!selectedUsers.value.length) {
    ElMessage.warning(t("_user.selectFirst"));
    return;
  }
  await ElMessageBox.confirm(
    t("_user.batchDeleteConfirm", { count: selectedUsers.value.length }),
    t("_user.batchDelete"),
    { type: "error" }
  );
  try {
    const deletePromises = selectedUsers.value.map(id => http.delete(`/admin/users/${id}`));
    await Promise.all(deletePromises);
    users.value = users.value.filter(u => !selectedUsers.value.includes(u.id));
    total.value = Math.max(0, total.value - selectedUsers.value.length);
    selectedUsers.value = [];
    ElMessage.success(t("_user.batchDeleted"));
  } catch {
    ElMessage.error(t("_user.batchDeleteFailed"));
  }
};

const handleSelectionChange = (selection: SystemUser[]) => {
  selectedUsers.value = selection.map(u => u.id);
};

// Dialog actions
const openAddDialog = () => {
  dialogTitle.value = t("_user.addUser");
  dialogMode.value = "add";
  editingUserId.value = null;
  userForm.username = "";
  userForm.role = "student";
  userForm.email = "";
  userForm.phone = "";
  userForm.dept = "";
  userForm.major = "";
  userForm.grade = "";
  userForm.is_active = true;
  dialogVisible.value = true;
};

const openEditDialog = (user: SystemUser) => {
  dialogTitle.value = t("_user.editUser");
  dialogMode.value = "edit";
  editingUserId.value = user.id;
  userForm.username = user.username;
  userForm.role = user.role;
  userForm.email = user.email;
  userForm.phone = user.phone;
  userForm.dept = user.dept;
  userForm.major = user.major || "";
  userForm.grade = user.grade || "";
  userForm.is_active = user.is_active;
  dialogVisible.value = true;
};

const submitting = ref(false);

const submitUser = async () => {
  if (!userFormRef.value) return;
  await userFormRef.value.validate(async valid => {
    if (!valid) return;
    submitting.value = true;
    try {
      if (dialogMode.value === "add") {
        await http.post("/admin/users", {
          username: userForm.username,
          password: "123456",
          email: userForm.email,
          role: userForm.role,
          phone: userForm.phone,
          dept: userForm.dept,
          major: userForm.major,
          grade: userForm.grade,
        });
        ElMessage.success(t("_user.addSuccess"));
      } else {
        await http.put(`/admin/users/${editingUserId.value}`, {
          username: userForm.username,
          email: userForm.email,
          role: userForm.role,
          phone: userForm.phone,
          dept: userForm.dept,
          major: userForm.major,
          grade: userForm.grade,
          is_active: userForm.is_active,
        });
        ElMessage.success(t("_user.updateSuccess"));
      }
      dialogVisible.value = false;
      fetchUsers();
    } catch {
      ElMessage.error(t("_user.submitFailed"));
    }
    submitting.value = false;
  });
};

const formRules = {
  username: [{ required: true, message: t("_user.username") + t("_user.cannotBeEmpty"), trigger: "blur" }],
  email: [
    { required: true, message: t("_user.email") + t("_user.cannotBeEmpty"), trigger: "blur" },
    { type: "email", message: t("_user.invalidEmail"), trigger: "blur" },
  ],
  phone: [{ required: true, message: t("_user.phone") + t("_user.cannotBeEmpty"), trigger: "blur" }],
  dept: [{ required: true, message: t("_user.dept") + t("_user.cannotBeEmpty"), trigger: "change" }],
  major: [{ required: true, message: t("_user.major") + t("_user.cannotBeEmpty"), trigger: "change" }],
  grade: [{ required: true, message: t("_user.grade") + t("_user.cannotBeEmpty"), trigger: "change" }],
};

// Server-side filtering via roleFilter/statusFilter - refetch
const handleRoleFilterChange = () => {
  currentPage.value = 1;
  fetchUsers();
};
const handleStatusFilterChange = () => {
  currentPage.value = 1;
  fetchUsers();
};

// CSV Import
const importFileRef = ref<HTMLInputElement | null>(null);
const importLoading = ref(false);

const triggerImport = () => {
  importFileRef.value?.click();
};

const handleFileImport = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  const ext = file.name.split(".").pop()?.toLowerCase();
  if (ext !== "csv" && ext !== "xlsx") {
    ElMessage.error(t("_user.invalidFileType"));
    target.value = "";
    return;
  }

  importLoading.value = true;
  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await http.post<httpNs.Response<{ created: number; skipped: number; errors: string[] }>>(
      "/admin/registrations/import",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    const d = res.data || { created: 0, skipped: 0, errors: [] };
    ElMessage.success(t("_user.importSuccess", { created: d.created, skipped: d.skipped }));
    if (d.errors?.length) {
      ElMessage.warning(t("_user.importErrors", { count: d.errors.length }));
    }
    fetchUsers();
  } catch {
    ElMessage.error(t("_user.importFailed"));
  }
  importLoading.value = false;
  target.value = "";
};

// CSV Export
const exportCSV = async () => {
  try {
    const params: Record<string, any> = { pageSize: 10000 };
    if (searchKeyword.value) params.search = searchKeyword.value;
    if (roleFilter.value) params.role = roleFilter.value;
    if (statusFilter.value) params.status = statusFilter.value;

    const res = await http.get<httpNs.Response<{ list: SystemUser[]; total: number }>>("/admin/users", { params });
    const users = res.data?.list || [];
    if (!users.length) {
      ElMessage.warning(t("_user.noDataToExport"));
      return;
    }

    const header = `${t("_registerApproval.username")},${t("_common.email")},${t("_common.role")},${t("_registerApproval.dept")},${t("_registerApproval.phone")},${t("_registerApproval.status")},${t("_registerApproval.registerTime")}\n`;
    const csv =
      header +
      users
        .map(u =>
          [
            u.username,
            u.email,
            u.role,
            u.dept,
            u.phone,
            u.is_active ? t("_common.active") : t("_common.inactive"),
            u.date_joined,
          ].join(",")
        )
        .join("\n");

    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = t("_user.exportFileName", { date: new Date().toISOString().slice(0, 10) });
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success(t("_user.exportSuccess"));
  } catch {
    ElMessage.error(t("_user.exportFailed"));
  }
};
</script>

<template>
  <div class="admin-users-page">
    <!-- Page Header with gradient accent -->
    <div class="page-header">
      <h2 class="page-title">{{ $t("_route.AdminUsers") }}</h2>
      <span class="page-sub">{{ $t("_user.totalUsers", { count: total }) }}</span>
    </div>

    <!-- Stats Summary Row -->
    <div class="stats-bar">
      <div class="stat-item">
        <div class="stat-icon-box" style="--sc: var(--tk-color-primary)">
          <Icon icon="ep:user" :size="18" />
        </div>
        <div class="stat-text">
          <span class="stat-num">{{ totalUsers }}</span>
          <span class="stat-lbl">{{ $t("_user.totalUsersLabel") }}</span>
        </div>
      </div>
      <div class="stat-divider" />
      <div class="stat-item">
        <div class="stat-icon-box" style="--sc: var(--tk-color-success)">
          <Icon icon="ep:select" :size="18" />
        </div>
        <div class="stat-text">
          <span class="stat-num">{{ activeUsers }}</span>
          <span class="stat-lbl">{{ $t("_user.activeUsersLabel") }}</span>
        </div>
      </div>
      <div class="stat-divider" />
      <div class="stat-item">
        <div class="stat-icon-box" style="--sc: var(--tk-color-warning)">
          <Icon icon="ep:avatar" :size="18" />
        </div>
        <div class="stat-text">
          <span class="stat-num">{{ teacherUsers }}</span>
          <span class="stat-lbl">{{ $t("_user.teachersLabel") }}</span>
        </div>
      </div>
      <div class="stat-divider" />
      <div class="stat-item">
        <div class="stat-icon-box" style="--sc: var(--tk-gray-color-500)">
          <Icon icon="ep:user-filled" :size="18" />
        </div>
        <div class="stat-text">
          <span class="stat-num">{{ studentUsers }}</span>
          <span class="stat-lbl">{{ $t("_user.studentsLabel") }}</span>
        </div>
      </div>
    </div>

    <!-- Toolbar card -->
    <div class="content-card toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchKeyword"
            :placeholder="$t('_user.searchPlaceholder')"
            :prefix-icon="Search"
            clearable
            style="width: 280px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
          <el-select
            v-model="roleFilter"
            :placeholder="$t('_user.filterByRole')"
            clearable
            style="width: 120px"
            @change="handleRoleFilterChange"
          >
            <el-option v-for="r in roleOptions" :key="r" :label="$t('_user.' + r)" :value="r" />
          </el-select>
          <el-select
            v-model="statusFilter"
            :placeholder="$t('_user.filterByStatus')"
            clearable
            style="width: 120px"
            @change="handleStatusFilterChange"
          >
            <el-option :label="$t('_user.active')" value="active" />
            <el-option :label="$t('_user.disabled')" value="disabled" />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button :icon="Refresh" text @click="handleRefresh">
            {{ $t("_user.refresh") }}
          </el-button>
          <el-button :icon="Upload" :loading="importLoading" @click="triggerImport">{{ $t("_user.import") }}</el-button>
          <el-button :icon="Download" @click="exportCSV">{{ $t("_user.export") }}</el-button>
          <el-button v-if="selectedUsers.length" :icon="Delete" type="danger" @click="batchDelete">
            {{ $t("_user.batchDelete") }} ({{ selectedUsers.length }})
          </el-button>
          <el-button :icon="Plus" type="primary" @click="openAddDialog">{{ $t("_user.addUser") }}</el-button>
        </div>
      </div>
    </div>
    <input ref="importFileRef" type="file" accept=".csv,.xlsx" style="display: none" @change="handleFileImport" />

    <!-- Table card -->
    <div class="content-card table-card" v-loading="loading">
      <el-table :data="users" stripe border style="width: 100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="45" align="center" />
        <el-table-column prop="username" :label="$t('_user.username')" min-width="160" sortable>
          <template #default="{ row }">
            <div class="user-cell">
              <div class="user-avatar" :class="'avatar-' + row.role">{{ getInitials(row.username) }}</div>
              <div class="user-meta">
                <span class="user-name">{{ row.username }}</span>
                <span class="user-email-sm">{{ row.email }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="role" :label="$t('_user.role')" min-width="90">
          <template #default="{ row }">
            <el-tag :type="getRoleTag(row.role)" size="small" effect="light">{{ $t("_user." + row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" :label="$t('_user.email')" min-width="200" />
        <el-table-column prop="phone" :label="$t('_user.phone')" min-width="130" />
        <el-table-column prop="dept" :label="$t('_user.dept')" min-width="130" />
        <el-table-column prop="course_count" :label="$t('_user.courseCount')" width="80" align="center">
          <template #default="{ row }">
            {{ row.course_count ?? 0 }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('_user.status')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.is_active)" size="small" effect="light">
              {{ row.is_active ? $t("_user.active") : $t("_user.disabled") }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" :label="$t('_user.lastLogin')" min-width="150" sortable>
          <template #default="{ row }">
            {{ row.last_login || "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="date_joined" :label="$t('_user.registerTime')" min-width="110" />
        <el-table-column :label="$t('_user.actions')" width="230" align="center" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button :icon="Edit" text type="primary" size="small" @click="openEditDialog(row)">
                {{ $t("_user.edit") }}
              </el-button>
              <el-button text :type="row.is_active ? 'warning' : 'success'" size="small" @click="toggleStatus(row)">
                {{ row.is_active ? $t("_user.disable") : $t("_user.enable") }}
              </el-button>
              <el-button :icon="Delete" text type="danger" size="small" @click="deleteUser(row)">
                {{ $t("_user.deleteUser") }}
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

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form ref="userFormRef" :model="userForm" :rules="formRules" label-width="80px">
        <el-form-item :label="$t('_user.username')" prop="username">
          <el-input v-model="userForm.username" :placeholder="$t('_user.username')" />
        </el-form-item>
        <el-form-item :label="$t('_user.role')" prop="role">
          <el-radio-group v-model="userForm.role">
            <el-radio v-for="r in roleOptions" :key="r" :value="r">{{ $t("_user." + r) }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('_user.email')" prop="email">
          <el-input v-model="userForm.email" :placeholder="$t('_user.email')" />
        </el-form-item>
        <el-form-item :label="$t('_user.phone')" prop="phone">
          <el-input v-model="userForm.phone" :placeholder="$t('_user.phone')" />
        </el-form-item>
        <el-form-item :label="$t('_user.dept')" prop="dept">
          <el-input v-model="userForm.dept" :placeholder="$t('_user.dept')" />
        </el-form-item>
        <el-form-item v-if="userForm.role === 'student'" :label="$t('_user.major')" prop="major">
          <el-input v-model="userForm.major" :placeholder="$t('_user.major')" />
        </el-form-item>
        <el-form-item v-if="userForm.role === 'student'" :label="$t('_user.grade')" prop="grade">
          <el-input v-model="userForm.grade" :placeholder="$t('_user.grade')" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'edit'" :label="$t('_user.status')">
          <el-switch
            v-model="userForm.is_active"
            :active-text="$t('_user.active')"
            :inactive-text="$t('_user.disabled')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t("_user.cancel") }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submitUser">{{ $t("_user.confirm") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.admin-users-page {
  padding: 4px 0;
}

// Page Header
.page-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0;
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
}

// Stats Bar
.stats-bar {
  display: flex;
  align-items: center;
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 12px 8px;
  margin-bottom: 20px;
  box-shadow: var(--tk-box-shadow-xs);
  overflow-x: auto;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 20px;
  flex: 1;
  min-width: 0;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: var(--tk-surface-border-color);
  flex-shrink: 0;
}

.stat-icon-box {
  --sc: var(--tk-color-primary);
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--sc) 12%, transparent);
  color: var(--sc);
  flex-shrink: 0;
}

.stat-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.stat-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--tk-gray-color-900);
  line-height: 1.2;
}

.stat-lbl {
  font-size: 12px;
  color: var(--tk-gray-color-500);
  white-space: nowrap;
}

// User cell
.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;

  &.avatar-admin {
    background: linear-gradient(135deg, #f56c6c, #e06060);
  }

  &.avatar-teacher {
    background: linear-gradient(135deg, #e6a23c, #f0b840);
  }

  &.avatar-student {
    background: linear-gradient(135deg, #409eff, #5cadff);
  }
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
}

.user-email-sm {
  font-size: 12px;
  color: var(--tk-gray-color-500);
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
