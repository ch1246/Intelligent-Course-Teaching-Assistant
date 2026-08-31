<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Check, Close, Refresh, Upload, Download } from "@element-plus/icons-vue";
import { http } from "@/common/http";
import { t } from "@/common/languages";

defineOptions({ name: "AdminRegisterApproval" });

interface PendingUser {
  id: number;
  username: string;
  student_id: string;
  sex: string;
  dept: string;
  major: string;
  grade: string;
  job: string;
  phone: string;
  email: string;
  date_joined: string;
  is_approved: boolean;
}

const users = ref<PendingUser[]>([]);
const loading = ref(true);
const statusFilter = ref("pending");
const searchKeyword = ref("");
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);
const selectedIds = ref<Set<number>>(new Set());

const loadUsers = async () => {
  loading.value = true;
  try {
    const res = await http.get<httpNs.Response<{ list: PendingUser[]; total: number }>>("/admin/registrations", {
      params: {
        page: currentPage.value,
        pageSize: pageSize.value,
        status: statusFilter.value,
        search: searchKeyword.value || undefined,
      },
    });
    users.value = res.data?.list || [];
    total.value = res.data?.total || 0;
  } catch {
    users.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

onMounted(loadUsers);

const approve = async (id: number) => {
  try {
    await http.post(`/admin/registrations/${id}/approve`);
    ElMessage.success(t("_registerApproval.approveSuccess"));
    loadUsers();
  } catch {
    ElMessage.error(t("_registerApproval.operationFailed"));
  }
};

const reject = async (id: number) => {
  await ElMessageBox.confirm(t("_registerApproval.rejectConfirm"), t("_registerApproval.confirmTitle"), {
    type: "warning",
  });
  try {
    await http.post(`/admin/registrations/${id}/reject`);
    ElMessage.success(t("_registerApproval.rejectSuccess"));
    loadUsers();
  } catch {
    ElMessage.error(t("_registerApproval.operationFailed"));
  }
};

const batchApprove = async () => {
  if (!selectedIds.value.size) {
    ElMessage.warning(t("_registerApproval.selectUsers"));
    return;
  }
  try {
    await http.post("/admin/registrations/batch-approve", { ids: [...selectedIds.value] });
    ElMessage.success(t("_registerApproval.batchApproveSuccess", { n: selectedIds.value.size }));
    selectedIds.value.clear();
    loadUsers();
  } catch {
    ElMessage.error(t("_registerApproval.operationFailed"));
  }
};

// Excel import
const importLoading = ref(false);
const importResult = ref<any>(null);
const fileInput = ref<HTMLInputElement>();

const handleImport = () => {
  fileInput.value?.click();
};

const onFileChange = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  importLoading.value = true;
  importResult.value = null;
  try {
    const form = new FormData();
    form.append("file", file);
    const res = await http.post<httpNs.Response<any>>("/admin/registrations/import", form);
    importResult.value = res.data;
    ElMessage.success(t("_registerApproval.importDone", { created: res.data?.created || 0 }));
    loadUsers();
  } catch {
    ElMessage.error(t("_registerApproval.importFailed"));
  } finally {
    importLoading.value = false;
    (e.target as HTMLInputElement).value = "";
  }
};

const downloadTemplate = () => {
  const csv = t("_registerApproval.csvHeader") + "\n" + t("_registerApproval.csvSample");
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = t("_registerApproval.csvTemplateFileName");
  a.click();
  URL.revokeObjectURL(a.href);
};

const formatTime = (ts: string) => (ts ? ts.split("T")[0] : "");
</script>

<template>
  <div class="register-approval">
    <div class="page-header">
      <h2>{{ $t("_registerApproval.pageTitle") }}</h2>
      <span class="page-sub">{{ $t("_registerApproval.totalRecords", { n: total }) }}</span>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div
        class="stat-card"
        :class="{ active: statusFilter === 'pending' }"
        @click="
          statusFilter = 'pending';
          currentPage = 1;
          loadUsers();
        "
      >
        <span class="stat-num">{{ statusFilter === "pending" ? total : "..." }}</span>
        <span class="stat-label">{{ $t("_registerApproval.pendingReview") }}</span>
      </div>
      <div
        class="stat-card"
        :class="{ active: statusFilter === 'approved' }"
        @click="
          statusFilter = 'approved';
          currentPage = 1;
          loadUsers();
        "
      >
        <span class="stat-num">{{ statusFilter === "approved" ? total : "..." }}</span>
        <span class="stat-label">{{ $t("_registerApproval.approved") }}</span>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchKeyword"
          :placeholder="$t('_registerApproval.searchPlaceholder')"
          :prefix-icon="Search"
          clearable
          style="width: 260px"
          @keyup.enter="loadUsers"
          @clear="loadUsers"
        />
        <el-button :icon="Refresh" @click="loadUsers">{{ $t("_registerApproval.refresh") }}</el-button>
        <el-button
          v-if="statusFilter === 'pending' && selectedIds.size > 0"
          type="success"
          :icon="Check"
          @click="batchApprove"
        >
          {{ $t("_registerApproval.batchApprove", { n: selectedIds.size }) }}
        </el-button>
      </div>
      <div class="toolbar-right">
        <el-button :icon="Download" @click="downloadTemplate">{{ $t("_registerApproval.downloadTemplate") }}</el-button>
        <el-button type="primary" :icon="Upload" :loading="importLoading" @click="handleImport">
          {{ $t("_registerApproval.importExcel") }}
        </el-button>
        <input ref="fileInput" type="file" accept=".xlsx,.xls" style="display: none" @change="onFileChange" />
      </div>
    </div>

    <!-- Import result -->
    <el-alert
      v-if="importResult"
      type="success"
      :title="
        $t('_registerApproval.importDone', { created: importResult.created }) +
        (importResult.skipped ? $t('_registerApproval.importSkipped', { skipped: importResult.skipped }) : '')
      "
      show-icon
      closable
      style="margin-bottom: 12px"
      @close="importResult = null"
    />

    <!-- Table -->
    <el-table
      v-loading="loading"
      :data="users"
      stripe
      border
      style="width: 100%"
      @selection-change="
        (rows: any) => {
          selectedIds.clear();
          rows.forEach((r: any) => selectedIds.add(r.id));
        }
      "
    >
      <el-table-column type="selection" width="45" v-if="statusFilter === 'pending'" />
      <el-table-column prop="username" :label="$t('_registerApproval.username')" width="120" />
      <el-table-column prop="student_id" :label="$t('_registerApproval.studentId')" width="120" />
      <el-table-column :label="$t('_registerApproval.gender')" width="60" prop="sex" />
      <el-table-column prop="dept" :label="$t('_registerApproval.dept')" min-width="180" show-overflow-tooltip />
      <el-table-column :label="$t('_registerApproval.majorGrade')" width="150">
        <template #default="{ row }">{{ [row.major, row.grade].filter(Boolean).join(" / ") || "-" }}</template>
      </el-table-column>
      <el-table-column prop="phone" :label="$t('_registerApproval.phone')" width="120" />
      <el-table-column :label="$t('_registerApproval.registerTime')" width="110">
        <template #default="{ row }">{{ formatTime(row.date_joined) }}</template>
      </el-table-column>
      <el-table-column :label="$t('_registerApproval.status')" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_approved ? 'success' : 'warning'" size="small">
            {{ row.is_approved ? $t("_registerApproval.approved") : $t("_registerApproval.pendingReview") }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        v-if="statusFilter === 'pending'"
        :label="$t('_registerApproval.actions')"
        width="140"
        align="center"
        fixed="right"
      >
        <template #default="{ row }">
          <el-button :icon="Check" link type="success" size="small" @click="approve(row.id)">
            {{ $t("_registerApproval.approve") }}
          </el-button>
          <el-button :icon="Close" link type="danger" size="small" @click="reject(row.id)">
            {{ $t("_registerApproval.reject") }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="loadUsers"
        @size-change="
          (size: number) => {
            pageSize = size;
            currentPage = 1;
            loadUsers();
          }
        "
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.register-approval {
  padding: 4px 0;
}
.page-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
}
.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--tk-surface-gray-color);
  margin: 0;
}
.page-sub {
  font-size: 13px;
  color: var(--tk-gray-color-500);
}

.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  flex: 1;
  padding: 16px 20px;
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  &:hover {
    border-color: var(--tk-color-primary);
  }
  &.active {
    border-color: var(--tk-color-primary);
    background: color-mix(in srgb, var(--tk-color-primary) 6%, var(--tk-surface-bg-color-box));
  }
}
.stat-num {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--tk-color-primary);
}
.stat-label {
  font-size: 13px;
  color: var(--tk-gray-color-500);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar-left,
.toolbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
