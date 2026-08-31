<script setup lang="ts">
import type { FormInstance } from "element-plus";
import { ref, reactive, useTemplateRef, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Lock, Cpu, Upload, Delete, Files } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { useUserStore } from "@/pinia";
import { http } from "@/common/http";

defineOptions({ name: "Settings" });

const userStore = useUserStore();
const isAdmin = computed(() => userStore.roles.includes("admin"));

const activeTab = ref("password");

// Password form
const passwordFormRef = useTemplateRef<FormInstance>("passwordFormRef");
const passwordLoading = ref(false);
const passwordForm = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const validateNewPassword = (_: any, value: string, callback: (e?: Error) => void) => {
  if (!value) callback(new Error(t("_settings.passwordRequired")));
  else if (value.length < 8) callback(new Error(t("_settings.passwordMinLength")));
  else if (!/[a-zA-Z]/.test(value) || !/\d/.test(value))
    callback(new Error(t("_settings.passwordMustContainLettersAndNumbers")));
  else callback();
};

const validateConfirmPassword = (_: any, value: string, callback: (e?: Error) => void) => {
  if (!value) callback(new Error(t("_settings.passwordConfirmRequired")));
  else if (passwordForm.newPassword !== value) callback(new Error(t("_settings.passwordMismatch")));
  else callback();
};

const passwordRules = {
  oldPassword: [{ required: true, message: t("_settings.currentPasswordRequired"), trigger: "blur" }],
  newPassword: [{ validator: validateNewPassword, trigger: "blur" }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: "blur" }],
};

const changePassword = async () => {
  if (!passwordFormRef.value) return;
  await passwordFormRef.value.validate(async valid => {
    if (!valid) return;
    passwordLoading.value = true;
    try {
      await http.post("/auth/change-password", {
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword,
      });
      ElMessage.success(t("_settings.passwordChanged"));
      passwordForm.oldPassword = "";
      passwordForm.newPassword = "";
      passwordForm.confirmPassword = "";
    } catch {
      ElMessage.error(t("_settings.modifyFailed"));
    }
    passwordLoading.value = false;
  });
};

// Model selection
interface ModelOption {
  key: string;
  displayName: string;
  provider: string;
  description: string;
}

const models = ref<ModelOption[]>([]);
const selectedModel = ref("");
const modelLoading = ref(false);
const modelError = ref("");

const fetchModels = async () => {
  modelLoading.value = true;
  modelError.value = "";
  try {
    const res = await http.get("/admin/agent-api-configs");
    const list = res.data || [];
    if (list.length > 0) {
      const config = list[0];
      const rawModels = config.model_list || [];
      models.value = rawModels.map((m: string) => {
        const name: string = typeof m === "string" ? m : (m as any).key || (m as any).id || String(m);
        return {
          key: name,
          displayName: name,
          provider: "",
          description: "",
        };
      });
      selectedModel.value = config.default_model || "";
      if (!selectedModel.value && models.value.length > 0) {
        selectedModel.value = models.value[0].key;
      }
    }
    if (models.value.length === 0) {
      modelError.value = t("_settings.noModelsHint");
    }
  } catch {
    modelError.value = t("_settings.fetchModelsFailed");
  }
  modelLoading.value = false;
};

const saveModel = async () => {
  if (!selectedModel.value) return;
  modelLoading.value = true;
  try {
    const res = await http.get("/admin/agent-api-configs");
    const list = res.data || [];
    if (list.length > 0) {
      const id = list[0].id;
      await http.put(`/admin/agent-api-configs/${id}`, { default_model: selectedModel.value });
      ElMessage.success(t("_settings.modelSetSuccess"));
    }
  } catch {
    ElMessage.error(t("_settings.saveFailed"));
  }
  modelLoading.value = false;
};

onMounted(() => {
  if (isAdmin.value) fetchModels();
  loadFiles();
});

// File management
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
const filesLoading = ref(true);

const loadFiles = async () => {
  filesLoading.value = true;
  try {
    const res = await http.get<httpNs.Response<any>>("/files");
    const list = res.data?.list || res.data || [];
    files.value = list.map((f: any) => ({
      id: f.id,
      fileName: f.original_name || "",
      fileType: (f.original_name || "").split(".").pop() || "",
      fileSize: f.file_size
        ? f.file_size >= 1024 * 1024
          ? (f.file_size / (1024 * 1024)).toFixed(1) + " MB"
          : (f.file_size / 1024).toFixed(1) + " KB"
        : "-",
      courseName: f.course_name || "-",
      status: (f.is_vectorized ? "ready" : "parsing") as "ready" | "parsing" | "failed",
      chunkCount: 0,
      uploadTime: (f.created_at || "").split("T")[0],
    }));
  } catch {
    files.value = [];
  } finally {
    filesLoading.value = false;
  }
};

const uploading = ref(false);
const fileInputRef = ref<HTMLInputElement>();

const handleUpload = () => {
  fileInputRef.value?.click();
};

const onFileSelected = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  uploading.value = true;
  try {
    const form = new FormData();
    form.append("file", file);
    await http.post("/files", form);
    ElMessage.success(t("_settings.fileUploadSuccess"));
    loadFiles();
  } catch {
    ElMessage.error(t("_settings.fileUploadFailed"));
  } finally {
    uploading.value = false;
    (e.target as HTMLInputElement).value = "";
  }
};

const deleteFile = async (file: UploadedFile) => {
  await ElMessageBox.confirm(t("_settings.confirmDeleteFile", { fileName: file.fileName }), t("_common.tip"), {
    type: "warning",
  });
  try {
    await http.delete(`/files/${file.id}`);
    files.value = files.value.filter(f => f.id !== file.id);
    ElMessage.success(t("_settings.fileDeleted"));
  } catch {
    ElMessage.error(t("_settings.fileDeleteFailed"));
  }
};

const getStatusTag = (status: string) => {
  const map: Record<string, { type: string; text: string }> = {
    ready: { type: "success", text: t("_settings.ready") },
    parsing: { type: "warning", text: t("_settings.parsing") },
    failed: { type: "danger", text: t("_settings.failed") },
  };
  return map[status] || { type: "info", text: status };
};
</script>

<template>
  <div class="settings-page">
    <h2 class="page-title">{{ $t("_settings.title") }}</h2>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <el-tab-pane :label="$t('_settings.changePassword')" name="password">
        <div class="tab-content">
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="100px"
            style="max-width: 480px"
          >
            <el-form-item :label="$t('_settings.currentPassword')" prop="oldPassword">
              <el-input
                v-model="passwordForm.oldPassword"
                type="password"
                show-password
                :placeholder="$t('_settings.pleaseEnterCurrentPassword')"
                :prefix-icon="Lock"
              />
            </el-form-item>
            <el-form-item :label="$t('_settings.newPassword')" prop="newPassword">
              <el-input
                v-model="passwordForm.newPassword"
                type="password"
                show-password
                :placeholder="$t('_settings.newPasswordHint')"
                :prefix-icon="Lock"
              />
            </el-form-item>
            <el-form-item :label="$t('_settings.confirmNewPassword')" prop="confirmPassword">
              <el-input
                v-model="passwordForm.confirmPassword"
                type="password"
                show-password
                :placeholder="$t('_settings.pleaseConfirmNewPassword')"
                :prefix-icon="Lock"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="passwordLoading" @click="changePassword">
                {{ $t("_settings.confirmModify") }}
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="isAdmin" :label="$t('_settings.defaultModel')" name="model">
        <div class="tab-content">
          <p class="tab-desc">{{ $t("_settings.modelSelectionDesc") }}</p>
          <el-alert
            v-if="modelError"
            type="warning"
            :title="modelError"
            show-icon
            closable
            style="margin-bottom: 16px"
            @close="modelError = ''"
          />
          <div class="model-list">
            <template v-if="models.length > 0">
              <div
                v-for="model in models"
                :key="model.key"
                class="model-card"
                :class="{ active: selectedModel === model.key }"
                @click="selectedModel = model.key"
              >
                <div class="model-header">
                  <div class="model-radio">
                    <el-icon :size="20" v-if="selectedModel === model.key" style="color: var(--tk-color-primary)">
                      <component :is="Cpu" />
                    </el-icon>
                    <div v-else class="radio-empty" />
                  </div>
                  <div>
                    <div class="model-name">{{ model.displayName }}</div>
                    <div class="model-provider">{{ model.provider }}</div>
                  </div>
                </div>
                <p class="model-desc">{{ model.description }}</p>
              </div>
            </template>
          </div>
          <el-button type="primary" :loading="modelLoading" @click="saveModel" style="margin-top: 24px">
            {{ $t("_settings.saveSettings") }}
          </el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="isAdmin" :label="$t('_settings.fileManagement')" name="files">
        <div class="tab-content">
          <div class="file-actions">
            <el-button :icon="Upload" type="primary" :loading="uploading" @click="handleUpload">
              {{ $t("_settings.uploadFile") }}
            </el-button>
            <input ref="fileInputRef" type="file" style="display: none" @change="onFileSelected" />
            <span class="file-hint">{{ $t("_settings.uploadFileHint") }}</span>
          </div>

          <el-table v-loading="filesLoading" :data="files" style="width: 100%; margin-top: 20px" border stripe>
            <el-table-column :label="$t('_settings.fileName')" min-width="200">
              <template #default="{ row }">
                <div class="file-name-cell">
                  <el-icon :size="16"><Files /></el-icon>
                  <span>{{ row.fileName }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="fileType" :label="$t('_settings.fileType')" width="80" align="center" />
            <el-table-column prop="fileSize" :label="$t('_settings.fileSize')" width="100" align="center" />
            <el-table-column prop="courseName" :label="$t('_settings.course')" width="160" />
            <el-table-column :label="$t('_settings.fileStatus')" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusTag(row.status).type" size="small" effect="light">
                  {{ getStatusTag(row.status).text }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="uploadTime" :label="$t('_settings.uploadTime')" width="120" />
            <el-table-column :label="$t('_common.operation')" width="100" align="center" fixed="right">
              <template #default="{ row }">
                <el-button :icon="Delete" link type="danger" size="small" @click="deleteFile(row)">
                  {{ $t("_common.delete") }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style lang="scss" scoped>
.settings-page {
  padding: 4px 0;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 24px;
}

.settings-tabs {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 0 24px 24px;

  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }

  :deep(.el-tabs__item) {
    font-size: 15px;
    font-weight: 500;
  }
}

.tab-content {
  padding-top: 20px;
  min-height: 360px;
}

.tab-desc {
  font-size: 13px;
  color: var(--tk-gray-color-600);
  margin: 0 0 20px;
}

// Model cards
.model-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 600px;
}

.model-card {
  padding: 18px 20px;
  border: 2px solid var(--tk-surface-border-color);
  border-radius: 10px;
  cursor: pointer;
  transition:
    border-color 0.25s,
    box-shadow 0.25s,
    transform 0.2s;

  &:hover {
    border-color: color-mix(in srgb, var(--tk-color-primary) 40%, transparent);
    transform: translateY(-1px);
  }
  transition: all 0.15s;

  &:hover {
    border-color: var(--tk-color-primary);
  }

  &.active {
    border-color: var(--tk-color-primary);
    background: var(--tk-bg-primary);
  }
}

.model-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.model-radio {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.radio-empty {
  width: 18px;
  height: 18px;
  border: 2px solid var(--tk-gray-color-300);
  border-radius: 50%;
}

.model-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
}

.model-provider {
  font-size: 12px;
  color: var(--tk-gray-color-500);
  margin-top: 2px;
}

.model-desc {
  font-size: 13px;
  color: var(--tk-gray-color-600);
  margin: 10px 0 0 38px;
  line-height: 1.5;
}

// File management
.file-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.file-hint {
  font-size: 12px;
  color: var(--tk-gray-color-500);
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
</style>
