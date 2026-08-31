<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Upload, Delete, Lock } from "@element-plus/icons-vue";
import { useUserStore } from "@/pinia";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "FileManagement" });

const userStore = useUserStore();
const isAdmin = computed(() => userStore.roles.includes("admin"));

interface UploadedFile {
  id: number;
  fileName: string;
  fileType: string;
  fileSize: string;
  courseName: string;
  status: "ready" | "parsing" | "failed";
  chunkCount: number;
  uploadTime: string;
}

const files = ref<UploadedFile[]>([]);
const uploading = ref(false);
const loading = ref(true);

const formatFileSize = (bytes: number): string => {
  if (bytes >= 1024 * 1024 * 1024) return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
  if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / 1024).toFixed(1) + " KB";
};

const loadFiles = async () => {
  loading.value = true;
  try {
    const res = await http.get<httpNs.Response<any>>("/files");
    const list = res.data?.list || res.data || [];
    files.value = list.map((f: any) => ({
      id: f.id,
      fileName: f.original_name || "",
      fileType: (f.original_name || "").split(".").pop() || "",
      fileSize: formatFileSize(f.file_size || 0),
      courseName: f.course_name || "-",
      status: f.is_vectorized ? "ready" : "parsing",
      chunkCount: 0,
      uploadTime: (f.created_at || "").split("T")[0],
    }));
  } catch {
    /* keep empty */
  } finally {
    loading.value = false;
  }
};

onMounted(loadFiles);

// Stat summary
const totalFiles = computed(() => files.value.length);

const readyFilesCount = computed(() => files.value.filter(f => f.status === "ready").length);

const parseFileSizeToBytes = (sizeStr: string): number => {
  const match = sizeStr.match(/^([\d.]+)\s*(KB|MB|GB)$/i);
  if (!match) return 0;
  const num = parseFloat(match[1]);
  const unit = match[2].toUpperCase();
  if (unit === "KB") return num * 1024;
  if (unit === "MB") return num * 1024 * 1024;
  if (unit === "GB") return num * 1024 * 1024 * 1024;
  return 0;
};

const totalSize = computed(() => {
  const bytes = files.value.reduce((acc, f) => acc + parseFileSizeToBytes(f.fileSize), 0);
  if (bytes >= 1024 * 1024 * 1024) return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
  if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / 1024).toFixed(1) + " KB";
});

const handleUpload = async () => {
  // Trigger file input
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".pdf,.txt,.md,.docx,.pptx,.py,.js,.ts";
  input.onchange = async (e: any) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    uploading.value = true;
    try {
      const form = new FormData();
      form.append("file", file);
      await http.post("/files", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      ElMessage.success(t("_settings.fileUploadSuccess"));
      await loadFiles();
    } catch {
      ElMessage.error(t("_settings.uploadFailed"));
    } finally {
      uploading.value = false;
    }
  };
  input.click();
};

const deleteFile = async (file: UploadedFile) => {
  await ElMessageBox.confirm(
    t("_settings.confirmDeleteFile", { fileName: file.fileName }),
    t("_common.confirm") + " " + t("_common.delete"),
    { type: "warning" }
  );
  try {
    await http.delete(`/files/${file.id}`);
    files.value = files.value.filter(f => f.id !== file.id);
    ElMessage.success(t("_settings.fileDeleted"));
  } catch {
    ElMessage.error(t("_settings.deleteFailed"));
  }
};

const getStatusTag = (status: string) => {
  const map: Record<string, { type: string; key: string }> = {
    ready: { type: "success", key: "_settings.ready" },
    parsing: { type: "warning", key: "_settings.parsing" },
    failed: { type: "danger", key: "_settings.failed" },
  };
  return map[status] || { type: "info", key: status };
};

const getFileTypeIcon = (fileType: string) => {
  const map: Record<string, string> = {
    pdf: "ep:document-copy",
    md: "ep:document",
    py: "ep:document",
    docx: "ep:document",
  };
  return map[fileType] || "ep:files";
};

const statCards = computed(() => [
  {
    label: t("_settings.totalFiles"),
    value: totalFiles.value,
    icon: "ep:files",
    color: "#4f46e5",
    bg: "color-mix(in srgb, #4f46e5 10%, transparent)",
  },
  {
    label: t("_settings.totalSize"),
    value: totalSize.value,
    icon: "ep:coin",
    color: "#059669",
    bg: "color-mix(in srgb, #059669 10%, transparent)",
  },
  {
    label: t("_settings.readyFiles"),
    value: readyFilesCount.value,
    icon: "ep:circle-check",
    color: "#d97706",
    bg: "color-mix(in srgb, #d97706 10%, transparent)",
  },
]);
</script>

<template>
  <div class="file-management-page">
    <h2 class="page-title">{{ $t("_settings.fileManagement") }}</h2>

    <!-- Stat summary cards -->
    <div class="stat-cards">
      <div v-for="card in statCards" :key="card.label" class="stat-card">
        <div class="stat-icon" :style="{ color: card.color, background: card.bg }">
          <Icon :icon="card.icon" :size="22" />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ card.value }}</span>
          <span class="stat-label">{{ card.label }}</span>
        </div>
      </div>
    </div>

    <div v-if="!isAdmin" class="admin-only-banner card-wrapper">
      <el-icon :size="16"><Lock /></el-icon>
      <span>{{ $t("_settings.onlyAdminCanManageFiles") }}</span>
    </div>

    <div class="card-wrapper">
      <div class="file-actions">
        <el-button
          :icon="Upload"
          type="primary"
          size="large"
          :loading="uploading"
          :disabled="!isAdmin"
          class="upload-btn"
          @click="handleUpload"
        >
          {{ $t("_settings.uploadFile") }}
        </el-button>
        <span class="file-hint">{{ $t("_settings.uploadFileHint") }}</span>
      </div>

      <el-table :data="files" style="width: 100%; margin-top: 20px" class="file-table" stripe>
        <el-table-column prop="fileName" :label="$t('_settings.fileName')" min-width="200">
          <template #default="{ row }">
            <div class="file-name-cell">
              <Icon :icon="getFileTypeIcon(row.fileType)" :size="16" />
              <span>{{ row.fileName }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="fileType" :label="$t('_settings.fileType')" width="80" align="center" />
        <el-table-column prop="fileSize" :label="$t('_settings.fileSize')" width="100" align="center" />
        <el-table-column prop="courseName" :label="$t('_settings.course')" width="160" />
        <el-table-column prop="status" :label="$t('_settings.fileStatus')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status).type" size="small" effect="light">
              {{ $t(getStatusTag(row.status).key) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploadTime" :label="$t('_settings.uploadTime')" width="120" />
        <el-table-column :label="$t('_common.operation')" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button :icon="Delete" text type="danger" size="small" :disabled="!isAdmin" @click="deleteFile(row)">
              {{ $t("_common.delete") }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.file-management-page {
  padding: 4px 0;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 24px;
  padding-bottom: 12px;
  border-bottom: 3px solid transparent;
  border-image: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) 1;
}

// Stat cards
.stat-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  box-shadow: var(--tk-box-shadow-sm);
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--tk-box-shadow-md);
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--tk-gray-color-900);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--tk-gray-color-500);
}

.card-wrapper {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 20px;
  box-shadow: var(--tk-box-shadow-sm);
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.upload-btn {
  font-weight: 500;
  padding: 10px 24px;
  border-radius: 8px;
}

.file-hint {
  font-size: 12px;
  color: var(--tk-gray-color-500);
}

.admin-only-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: color-mix(in srgb, var(--tk-color-warning) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--tk-color-warning) 18%, transparent);
  border-radius: 6px;
  font-size: 13px;
  color: var(--tk-color-warning);
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

// Table hover
.file-table {
  :deep(.el-table__body tr) {
    transition: background 0.2s ease;
  }

  :deep(.el-table__body tr:hover > td) {
    background: color-mix(in srgb, var(--tk-color-primary) 3%, transparent) !important;
  }
}

@media (max-width: 768px) {
  .stat-cards {
    flex-direction: column;
  }
}
</style>
