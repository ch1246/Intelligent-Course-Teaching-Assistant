<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Check, Close, Refresh } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "AdminEnrollReview" });

interface EnrollmentRequest {
  id: number;
  courseId: number;
  courseName: string;
  studentName: string;
  studentDept: string;
  applyTime: string;
  status: "pending" | "approved" | "rejected";
  reason?: string;
}

const requests = ref<EnrollmentRequest[]>([]);
const loading = ref(true);

const loadRequests = async () => {
  loading.value = true;
  try {
    const res = await http.get<httpNs.Response<any>>("/admin/enroll-review", {
      params: { status: statusFilter.value || undefined },
    });
    const list = res.data?.list || res.data || [];
    requests.value = list.map((r: any) => ({
      id: r.id,
      courseId: r.course?.id,
      courseName: r.course?.name || r.course_name || "",
      studentName: r.student?.username || r.student_name || "",
      studentDept: r.student?.dept || "",
      applyTime: r.enrolled_at || "",
      status: r.status || "pending",
      reason: r.review_comment || "",
    }));
  } catch {
    requests.value = [];
  } finally {
    loading.value = false;
  }
};

onMounted(loadRequests);

const searchKeyword = ref("");
const statusFilter = ref("");
const currentPage = ref(1);
const pageSize = ref(10);

// Stat computed values
const pendingCount = computed(() => requests.value.filter(r => r.status === "pending").length);
const approvedCount = computed(() => requests.value.filter(r => r.status === "approved").length);
const rejectedCount = computed(() => requests.value.filter(r => r.status === "rejected").length);
const totalCount = computed(() => requests.value.length);

const getStatusTag = (status: string) => {
  const map: Record<string, string> = { pending: "warning", approved: "success", rejected: "danger" };
  return map[status] || "info";
};

const getStatusText = (status: string) => t(`_adminEnrollReview.${status}`);

const approveRequest = async (req: EnrollmentRequest) => {
  await ElMessageBox.confirm(
    t("_adminEnrollReview.confirmApprove", { student: req.studentName, course: req.courseName }),
    t("_adminEnrollReview.approveDialogTitle"),
    { confirmButtonText: t("_adminEnrollReview.confirmApproveText"), type: "success" }
  );
  try {
    await http.put(`/admin/enroll-review/${req.id}`, { status: "approved" });
    req.status = "approved";
    ElMessage.success(t("_adminEnrollReview.approvedMessage", { student: req.studentName }));
  } catch {
    ElMessage.error(t("_registerApproval.operationFailed"));
  }
};

const rejectRequest = async (req: EnrollmentRequest) => {
  await ElMessageBox.prompt(
    t("_adminEnrollReview.rejectReasonPlaceholder"),
    t("_adminEnrollReview.rejectDialogTitle"),
    {
      confirmButtonText: t("_adminEnrollReview.confirmRejectText"),
      cancelButtonText: t("_common.cancel"),
      type: "warning",
      inputPlaceholder: t("_adminEnrollReview.rejectReasonHint"),
    }
  )
    .then(async ({ value }) => {
      try {
        await http.put(`/admin/enroll-review/${req.id}`, { status: "rejected", review_comment: value || "" });
        req.status = "rejected";
        req.reason = value || undefined;
        ElMessage.info(t("_adminEnrollReview.rejectedMessage", { student: req.studentName }));
      } catch {
        ElMessage.error(t("_registerApproval.operationFailed"));
      }
    })
    .catch(() => {});
};

const batchApprove = async () => {
  const pending = requests.value.filter(r => r.status === "pending");
  if (!pending.length) {
    ElMessage.warning(t("_adminEnrollReview.noPendingRequests"));
    return;
  }
  await ElMessageBox.confirm(
    t("_adminEnrollReview.confirmBatchApprove", { count: pending.length }),
    t("_adminEnrollReview.batchApproveTitle"),
    { type: "success" }
  );
  pending.forEach(r => (r.status = "approved"));
  ElMessage.success(t("_adminEnrollReview.batchApprovedMessage", { count: pending.length }));
};

const filteredRequests = computed(() => {
  let list = requests.value;
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase();
    list = list.filter(
      r =>
        r.studentName.toLowerCase().includes(kw) ||
        r.courseName.toLowerCase().includes(kw) ||
        r.studentDept.toLowerCase().includes(kw)
    );
  }
  if (statusFilter.value && statusFilter.value !== "undefined")
    list = list.filter(r => r.status === statusFilter.value);
  return list;
});

const paginatedRequests = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredRequests.value.slice(start, start + pageSize.value);
});
</script>

<template>
  <div class="enroll-review-page">
    <!-- Page Header with gradient accent -->
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t("_adminEnrollReview.title") }}</h2>
        <span class="page-sub">
          {{ $t("_adminEnrollReview.totalRecords", { total: filteredRequests.length }) }}
        </span>
      </div>
      <el-button v-if="pendingCount > 0" type="success" :icon="Check" class="batch-approve-btn" @click="batchApprove">
        {{ $t("_adminEnrollReview.approveAll", { count: pendingCount }) }}
      </el-button>
    </div>

    <!-- Status Distribution Bar -->
    <div class="distribution-bar">
      <div class="dist-segment dist-pending" :style="{ flex: pendingCount || 0.1 }">
        <span v-if="pendingCount" class="dist-label">{{ pendingCount }} {{ $t("_adminEnrollReview.pending") }}</span>
      </div>
      <div class="dist-segment dist-approved" :style="{ flex: approvedCount || 0.1 }">
        <span v-if="approvedCount" class="dist-label">{{ approvedCount }} {{ $t("_adminEnrollReview.approved") }}</span>
      </div>
      <div class="dist-segment dist-rejected" :style="{ flex: rejectedCount || 0.1 }">
        <span v-if="rejectedCount" class="dist-label">{{ rejectedCount }} {{ $t("_adminEnrollReview.rejected") }}</span>
      </div>
    </div>

    <!-- Stats Summary Row -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card border-left-warning">
          <div class="stat-icon" :style="{ '--stat-color': 'var(--tk-color-warning)' }">
            <Icon icon="ep:clock" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ pendingCount }}</span>
            <span class="stat-label">{{ $t("_adminEnrollReview.pending") }}</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card border-left-success">
          <div class="stat-icon" :style="{ '--stat-color': 'var(--tk-color-success)' }">
            <Icon icon="ep:circle-check" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ approvedCount }}</span>
            <span class="stat-label">{{ $t("_adminEnrollReview.approved") }}</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card border-left-danger">
          <div class="stat-icon" :style="{ '--stat-color': 'var(--tk-color-danger)' }">
            <Icon icon="ep:circle-close" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ rejectedCount }}</span>
            <span class="stat-label">{{ $t("_adminEnrollReview.rejected") }}</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card border-left-info">
          <div class="stat-icon" :style="{ '--stat-color': 'var(--tk-gray-color-500)' }">
            <Icon icon="ep:list" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ totalCount }}</span>
            <span class="stat-label">{{ $t("_adminEnrollReview.totalLabel") }}</span>
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
            :placeholder="$t('_adminEnrollReview.searchPlaceholder')"
            :prefix-icon="Search"
            clearable
            style="width: 300px"
          />
          <el-select
            v-model="statusFilter"
            :placeholder="$t('_adminEnrollReview.filterByStatus')"
            clearable
            style="width: 140px"
          >
            <el-option :label="$t('_adminEnrollReview.pending')" value="pending" />
            <el-option :label="$t('_adminEnrollReview.approved')" value="approved" />
            <el-option :label="$t('_adminEnrollReview.rejected')" value="rejected" />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button
            :icon="Refresh"
            text
            @click="
              searchKeyword = '';
              statusFilter = '';
            "
          >
            {{ $t("_common.refresh") }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Table card -->
    <div class="content-card table-card">
      <el-table :data="paginatedRequests" stripe border style="width: 100%">
        <el-table-column :label="$t('_adminEnrollReview.studentName')" min-width="120">
          <template #default="{ row }">
            <span class="student-name">{{ row.studentName }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminEnrollReview.department')" min-width="140">
          <template #default="{ row }">
            <el-tag effect="plain" type="info" size="small">{{ row.studentDept }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminEnrollReview.courseName')" min-width="200">
          <template #default="{ row }">
            <div class="course-cell">
              <Icon icon="ep:school" :size="14" />
              <span>{{ row.courseName }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminEnrollReview.applyTime')" min-width="160" sortable>
          <template #default="{ row }">
            <span class="time-text">{{ row.applyTime }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminEnrollReview.reviewStatus')" width="110" align="center">
          <template #default="{ row }">
            <span class="status-tag" :class="'status-' + row.status">
              <span class="status-dot"></span>
              {{ getStatusText(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminEnrollReview.remark')" min-width="160">
          <template #default="{ row }">
            <span v-if="row.reason" class="reason-text">{{ row.reason }}</span>
            <span v-else class="no-reason">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminEnrollReview.operation')" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button :icon="Check" link type="success" size="small" @click="approveRequest(row)">
                {{ $t("_adminEnrollReview.approve") }}
              </el-button>
              <el-button :icon="Close" link type="danger" size="small" @click="rejectRequest(row)">
                {{ $t("_adminEnrollReview.reject") }}
              </el-button>
            </template>
            <el-tag v-else size="small" effect="plain" :type="getStatusTag(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 30]"
          :total="filteredRequests.length"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.enroll-review-page {
  padding: 4px 0;
}

// Status Distribution Bar
.distribution-bar {
  display: flex;
  height: 36px;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 20px;
  box-shadow: var(--tk-box-shadow-xs);
}

.dist-segment {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  transition: flex 0.4s ease;
}

.dist-pending {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
}

.dist-approved {
  background: linear-gradient(135deg, #10b981, #34d399);
}

.dist-rejected {
  background: linear-gradient(135deg, #ef4444, #f87171);
}

.dist-label {
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 8px;
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
    background: linear-gradient(135deg, var(--tk-color-warning), var(--tk-color-primary));
  }
}

.page-sub {
  font-size: 13px;
  color: var(--tk-gray-color-500);
  margin-left: 14px;
}

// Batch approve button
.batch-approve-btn {
  border: none;
  background: linear-gradient(135deg, var(--tk-color-success), #5ab75a);
  color: #fff;
  font-weight: 500;
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: var(--tk-box-shadow-md);
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
  border-left: 3px solid var(--tk-surface-border-color);
  border-radius: 10px;
  box-shadow: var(--tk-box-shadow-xs);
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--tk-box-shadow-md);
  }

  &.border-left-warning {
    border-left-color: var(--tk-color-warning);
  }
  &.border-left-success {
    border-left-color: var(--tk-color-success);
  }
  &.border-left-danger {
    border-left-color: var(--tk-color-danger);
  }
  &.border-left-info {
    border-left-color: var(--tk-color-primary);
  }
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
  gap: 10px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

// Custom Status Tags
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }
}

.status-pending {
  background: color-mix(in srgb, var(--tk-color-warning) 12%, transparent);
  color: var(--tk-color-warning);

  .status-dot {
    background: var(--tk-color-warning);
  }
}

.status-approved {
  background: color-mix(in srgb, var(--tk-color-success) 12%, transparent);
  color: var(--tk-color-success);

  .status-dot {
    background: var(--tk-color-success);
  }
}

.status-rejected {
  background: color-mix(in srgb, var(--tk-color-danger) 12%, transparent);
  color: var(--tk-color-danger);

  .status-dot {
    background: var(--tk-color-danger);
  }
}

// Course cell
.course-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

// Student name
.student-name {
  font-weight: 500;
}

// Time text
.time-text {
  color: var(--tk-gray-color-600);
  font-size: 13px;
}

// Remark
.reason-text {
  font-size: 12px;
  color: var(--tk-gray-color-600);
}

.no-reason {
  color: var(--tk-gray-color-400);
}

// Pagination
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
