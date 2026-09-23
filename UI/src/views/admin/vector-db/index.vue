<script setup lang="ts">
import type { FormInstance } from "element-plus";
import { ref, computed, reactive, useTemplateRef, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Refresh, Plus, Delete, Upload } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "AdminVectorDB" });

// Backend fields: id, name, course (object), embedding_model, document_count, chunk_count,
// vector_count, dimension, status, description, last_indexed_at, created_at
interface VectorCollection {
  id: number;
  name: string;
  course: { id: number; name: string } | null;
  embedding_model: string;
  document_count: number;
  chunk_count: number;
  vector_count: number;
  dimension: number;
  status: "active" | "indexing" | "error";
  last_indexed_at: string;
  description: string;
  created_at: string;
}

const collections = ref<VectorCollection[]>([]);
const total = ref(0);
const loading = ref(false);

const searchKeyword = ref("");
const statusFilter = ref("");
const currentPage = ref(1);
const pageSize = ref(8);

// Dialog
const dialogVisible = ref(false);
const dialogTitle = ref(t("_adminVectorDB.createCollection"));
const dialogMode = ref<"create" | "edit">("create");
const editingId = ref<number | null>(null);
const formRef = useTemplateRef<FormInstance>("formRef");
const form = reactive({
  name: "",
  course_id: null as number | null,
  embeddingModel: "text-embedding-3-large",
  description: "",
});

const courseOptions = ref<{ id: number; name: string }[]>([]);
const modelOptions = [
  { label: "text-embedding-3-large (3072维)", value: "text-embedding-3-large" },
  { label: "text-embedding-3-small (1536维)", value: "text-embedding-3-small" },
  { label: "bge-large-zh-v1.5 (1024维)", value: "bge-large-zh-v1.5" },
];

// Fetch courses for dropdown
const fetchCourseOptions = async () => {
  try {
    const res = await http.get<httpNs.Response<{ list: { id: number; name: string }[]; total: number }>>(
      "/admin/courses",
      { params: { page: 1, pageSize: 100 } }
    );
    if (res.data) {
      courseOptions.value = res.data.list || [];
    }
  } catch {
    courseOptions.value = [];
  }
};

// Fetch collections from API
const fetchCollections = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      pageSize: pageSize.value,
    };
    if (searchKeyword.value) params.search = searchKeyword.value;
    if (statusFilter.value) params.status = statusFilter.value;

    const res = await http.get<httpNs.Response<{ list: VectorCollection[]; total: number }>>(
      "/admin/vector-db/collections",
      { params }
    );
    if (res.data) {
      collections.value = res.data.list || [];
      total.value = res.data.total || 0;
    }
  } catch {
    collections.value = [];
    total.value = 0;
  }
  loading.value = false;
};

onMounted(() => {
  fetchCourseOptions();
  fetchCollections();
});

const handlePageChange = (page: number) => {
  currentPage.value = page;
  fetchCollections();
};

const handlePageSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  fetchCollections();
};

const handleSearch = () => {
  currentPage.value = 1;
  fetchCollections();
};

const handleRefresh = () => {
  searchKeyword.value = "";
  statusFilter.value = "";
  currentPage.value = 1;
  fetchCollections();
};

const handleStatusFilterChange = () => {
  currentPage.value = 1;
  fetchCollections();
};

// Stat computed values
const totalCollections = computed(() => total.value);
const activeCollections = computed(() => collections.value.filter(c => c.status === "active").length);
const totalDocs = computed(() => collections.value.reduce((s, c) => s + c.document_count, 0));
const totalVectors = computed(() => collections.value.reduce((s, c) => s + c.vector_count, 0));

const getStatusTag = (status: string) => {
  const map: Record<string, string> = { active: "success", indexing: "warning", error: "danger" };
  return map[status] || "info";
};

const getStatusText = (status: string) => t(`_adminVectorDB.${status}`);

const reindex = async (col: VectorCollection) => {
  await ElMessageBox.confirm(
    t("_adminVectorDB.confirmRebuildIndex", { name: col.name }),
    t("_adminVectorDB.rebuildIndexTitle"),
    { type: "warning" }
  );
  try {
    await http.post(`/admin/vector-db/collections/${col.id}/reindex`);
    col.status = "indexing";
    ElMessage.success(t("_adminVectorDB.rebuildIndexSuccess", { name: col.name }));
  } catch {
    ElMessage.error(t("_adminVectorDB.rebuildIndexFailed"));
  }
};

const deleteCollection = async (col: VectorCollection) => {
  await ElMessageBox.confirm(t("_adminVectorDB.confirmDelete", { name: col.name }), t("_adminVectorDB.deleteWarning"), {
    type: "error",
  });
  try {
    await http.delete(`/admin/vector-db/collections/${col.id}`);
    collections.value = collections.value.filter(c => c.id !== col.id);
    total.value = Math.max(0, total.value - 1);
    ElMessage.success(t("_adminVectorDB.deleted"));
  } catch {
    ElMessage.error(t("_adminVectorDB.deleteFailed"));
  }
};

const openCreateDialog = () => {
  dialogTitle.value = t("_adminVectorDB.createCollection");
  dialogMode.value = "create";
  editingId.value = null;
  form.name = "";
  form.course_id = null;
  form.embeddingModel = "text-embedding-3-large";
  form.description = "";
  dialogVisible.value = true;
};

const openEditDialog = (col: VectorCollection) => {
  dialogTitle.value = t("_adminVectorDB.editCollection");
  dialogMode.value = "edit";
  editingId.value = col.id;
  form.name = col.name;
  form.course_id = col.course || null;
  form.embeddingModel = col.embedding_model;
  form.description = col.description;
  dialogVisible.value = true;
};

const submitting = ref(false);

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async valid => {
    if (!valid) return;
    submitting.value = true;
    try {
      if (dialogMode.value === "create") {
        await http.post("/admin/vector-db/collections", {
          name: form.name,
          course: form.course_id,
          embedding_model: form.embeddingModel,
          description: form.description,
        });
        ElMessage.success(t("_adminVectorDB.createdSuccess"));
      } else {
        await http.put(`/admin/vector-db/collections/${editingId.value}`, {
          name: form.name,
          course: form.course_id,
          embedding_model: form.embeddingModel,
          description: form.description,
        });
        ElMessage.success(t("_adminVectorDB.updatedSuccess"));
      }
      dialogVisible.value = false;
      fetchCollections();
    } catch {
      ElMessage.error(t("_adminVectorDB.submitFailed"));
    }
    submitting.value = false;
  });
};

const formRules = {
  name: [{ required: true, message: t("_adminVectorDB.nameRequired"), trigger: "blur" }],
  course_id: [{ required: true, message: t("_adminVectorDB.courseRequired"), trigger: "change" }],
  embeddingModel: [{ required: true, message: t("_adminVectorDB.modelRequired"), trigger: "change" }],
};

// Format date string for display
const formatDate = (dateStr: string) => {
  if (!dateStr) return "-";
  return dateStr;
};

// Upload document
const uploading = ref(false);
const uploadDialogVisible = ref(false);
const uploadSelectedCollectionId = ref<number | null>(null);
let pendingFile: File | null = null;

const openUploadDialog = () => {
  uploadSelectedCollectionId.value = collections.value.length > 0 ? collections.value[0].id : null;
  uploadDialogVisible.value = true;
};

const handleUpload = (col?: VectorCollection) => {
  if (col) {
    // Direct upload from table row
    uploadSelectedCollectionId.value = col.id;
    triggerFileSelect();
  } else {
    // Open dialog to select collection first
    openUploadDialog();
  }
};

const triggerFileSelect = () => {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".pdf,.txt,.md,.docx,.pptx";
  input.onchange = async (e: any) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    const targetId = uploadSelectedCollectionId.value;
    if (!targetId) {
      ElMessage.warning("请先选择目标集合");
      return;
    }
    uploadDialogVisible.value = false;
    uploading.value = true;
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("collection_id", String(targetId));
      await http.post("/admin/vector-db/documents/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      ElMessage.success(`文件 ${file.name} 上传成功，正在重建索引...`);
      // Auto reindex after upload
      try {
        await http.post(`/admin/vector-db/collections/${targetId}/reindex`);
        ElMessage.success("索引重建已触发");
      } catch {
        ElMessage.warning("文件上传成功，但索引重建失败，请手动重建");
      }
      await fetchCollections();
    } catch {
      ElMessage.error("文件上传失败");
    } finally {
      uploading.value = false;
    }
  };
  input.click();
};

const confirmUploadCollection = () => {
  if (!uploadSelectedCollectionId.value) {
    ElMessage.warning("请选择目标集合");
    return;
  }
  triggerFileSelect();
};
</script>

<template>
  <div class="admin-vector-db-page">
    <!-- Page Header with gradient accent -->
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t("_adminVectorDB.title") }}</h2>
        <span class="page-sub">{{ $t("_adminVectorDB.totalCollections", { count: total }) }}</span>
      </div>
    </div>

    <!-- Stats Summary Row -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon" :style="{ '--stat-color': '#6366f1' }">
            <Icon icon="ep:coin" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value mono">{{ totalCollections }}</span>
            <span class="stat-label">{{ $t("_adminVectorDB.totalCollectionsLabel") }}</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon" :style="{ '--stat-color': 'var(--tk-color-success)' }">
            <Icon icon="ep:circle-check" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value mono">{{ activeCollections }}</span>
            <span class="stat-label">{{ $t("_adminVectorDB.activeCollectionsLabel") }}</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon" :style="{ '--stat-color': 'var(--tk-color-warning)' }">
            <Icon icon="ep:document" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value mono">{{ totalDocs }}</span>
            <span class="stat-label">{{ $t("_adminVectorDB.totalDocuments") }}</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon" :style="{ '--stat-color': '#8b5cf6' }">
            <Icon icon="ep:data-line" :size="22" />
          </div>
          <div class="stat-info">
            <span class="stat-value mono">{{ totalVectors.toLocaleString() }}</span>
            <span class="stat-label">{{ $t("_adminVectorDB.totalVectors") }}</span>
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
            :placeholder="$t('_adminVectorDB.searchPlaceholder')"
            :prefix-icon="Search"
            clearable
            style="width: 300px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
          <el-select
            v-model="statusFilter"
            :placeholder="$t('_adminVectorDB.filterByStatus')"
            clearable
            style="width: 130px"
            @change="handleStatusFilterChange"
          >
            <el-option :label="$t('_adminVectorDB.active')" value="active" />
            <el-option :label="$t('_adminVectorDB.indexing')" value="indexing" />
            <el-option :label="$t('_adminVectorDB.error')" value="error" />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button :icon="Refresh" text @click="handleRefresh">
            {{ $t("_common.refresh") }}
          </el-button>
          <el-button :icon="Upload" type="success" :loading="uploading" @click="handleUpload()">
            上传文档
          </el-button>
          <el-button :icon="Plus" type="primary" @click="openCreateDialog">
            {{ $t("_adminVectorDB.createCollection") }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Table card -->
    <div class="content-card table-card" v-loading="loading">
      <el-table :data="collections" stripe border style="width: 100%">
        <el-table-column :label="$t('_adminVectorDB.collectionName')" min-width="140">
          <template #default="{ row }">
            <div class="name-cell">
              <Icon icon="ep:coin" :size="14" />
              <span class="col-name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminVectorDB.course')" min-width="140">
          <template #default="{ row }">
            <el-tag effect="plain" type="info" size="small">{{ row.course_name || "-" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminVectorDB.embeddingModel')" min-width="200">
          <template #default="{ row }">
            <span class="model-text">{{ row.embedding_model }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminVectorDB.dimension')" width="100" align="center">
          <template #default="{ row }">
            <span class="dimension-badge">{{ row.dimension }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="document_count"
          :label="$t('_adminVectorDB.documentCount')"
          width="90"
          align="center"
          sortable
        />
        <el-table-column prop="chunk_count" :label="$t('_adminVectorDB.chunkCount')" width="90" align="center" />
        <el-table-column :label="$t('_adminVectorDB.vectorCount')" width="100" align="center">
          <template #default="{ row }">
            <span class="count-num">{{ row.vector_count.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminVectorDB.status')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)" size="small" effect="light">
              <Icon v-if="row.status === 'indexing'" icon="ep:refresh" :size="12" style="margin-right: 4px" />
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminVectorDB.lastIndexed')" min-width="150">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.last_indexed_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_adminVectorDB.operation')" width="250" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" :icon="Plus" @click="openEditDialog(row)">
              {{ $t("_common.edit") }}
            </el-button>
            <el-button link type="success" size="small" :icon="Upload" @click="handleUpload(row)">
              上传
            </el-button>
            <el-button link type="warning" size="small" :loading="row.status === 'indexing'" @click="reindex(row)">
              {{ $t("_adminVectorDB.rebuildIndex") }}
            </el-button>
            <el-button link type="danger" size="small" :icon="Delete" @click="deleteCollection(row)" />
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
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-form-item :label="$t('_adminVectorDB.collectionName')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('_adminVectorDB.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('_adminVectorDB.course')" prop="course_id">
          <el-select v-model="form.course_id" :placeholder="$t('_adminVectorDB.coursePlaceholder')" style="width: 100%">
            <el-option v-for="c in courseOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('_adminVectorDB.embeddingModel')" prop="embeddingModel">
          <el-select
            v-model="form.embeddingModel"
            :placeholder="$t('_adminVectorDB.modelPlaceholder')"
            style="width: 100%"
          >
            <el-option v-for="m in modelOptions" :key="m.value" :label="m.label" :value="m.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('_common.description')">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('_adminVectorDB.descriptionPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t("_common.cancel") }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">{{ $t("_common.confirm") }}</el-button>
      </template>
    </el-dialog>

    <!-- Upload Document Dialog -->
    <el-dialog v-model="uploadDialogVisible" title="上传文档到向量集合" width="460px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="目标集合">
          <el-select v-model="uploadSelectedCollectionId" placeholder="选择向量集合" style="width: 100%">
            <el-option
              v-for="col in collections"
              :key="col.id"
              :label="`${col.name} (${col.course_name || '-'})`"
              :value="col.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="文件格式">
          <span style="color: var(--tk-gray-color-500); font-size: 13px;">支持 PDF、Word、PPT、Markdown、TXT</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="uploading" @click="confirmUploadCollection">
          选择文件并上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.admin-vector-db-page {
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
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
  }
}

.page-sub {
  font-size: 13px;
  color: var(--tk-gray-color-500);
  margin-left: 14px;
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
  border-radius: 10px;
  box-shadow: var(--tk-box-shadow-xs);
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 14px color-mix(in srgb, var(--stat-color, var(--tk-color-primary)) 15%, transparent);
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

  &.mono {
    font-family: "Geist Mono", "SF Mono", "JetBrains Mono", "Cascadia Code", monospace;
    font-weight: 600;
    letter-spacing: -0.02em;
  }
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

// Table cell styles
.name-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.col-name {
  font-weight: 500;
  font-family: monospace;
}

.model-text {
  font-size: 12px;
  font-family: monospace;
  color: var(--tk-gray-color-600);
}

.dimension-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  background: var(--tk-gray-color-100);
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
  color: var(--tk-color-primary);
}

.count-num {
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.time-text {
  color: var(--tk-gray-color-600);
  font-size: 13px;
}

// Pagination
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
