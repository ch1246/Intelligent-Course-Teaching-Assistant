<script setup lang="ts">
import type { FormInstance } from "element-plus";
import { ref, reactive, computed, onMounted, useTemplateRef } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Refresh, Plus, Edit, Delete, Check, Connection } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "AdminAgentAPI" });

interface AgentAPIConfig {
  id: number;
  name: string;
  base_url: string;
  api_key: string;
  model_list: string[];
  default_model: string;
  is_active: boolean;
  is_default: boolean;
  created_by: number;
  creator_name: string;
  created_at: string;
  updated_at: string;
}

const configs = ref<AgentAPIConfig[]>([]);
const loading = ref(false);
const search = ref("");
const dialogVisible = ref(false);
const dialogTitle = ref("");
const isEditing = ref(false);
const editId = ref<number | null>(null);
const formRef = useTemplateRef<FormInstance>("formRef");

const form = reactive({
  name: "",
  base_url: "",
  api_key: "",
  model_list_str: "",
  default_model: "",
  is_active: true,
  is_default: false,
});

const rules = {
  name: [{ required: true, message: String(t("_agentAPI.form.nameRequired")), trigger: "blur" }],
  base_url: [{ required: true, message: String(t("_agentAPI.form.baseUrlRequired")), trigger: "blur" }],
  api_key: [
    {
      validator: (_rule: unknown, value: string, cb: (e?: Error) => void) => {
        if (!isEditing.value && !value) {
          return cb(new Error(String(t("_agentAPI.form.apiKeyRequired"))));
        }
        cb();
      },
      trigger: "blur",
    },
  ],
  model_list_str: [{ required: true, message: String(t("_agentAPI.form.modelListRequired")), trigger: "blur" }],
};

const filteredConfigs = computed(() => {
  if (!search.value) return configs.value;
  const s = search.value.toLowerCase();
  return configs.value.filter(c => c.name.toLowerCase().includes(s) || c.base_url.toLowerCase().includes(s));
});

async function fetchConfigs() {
  loading.value = true;
  try {
    const res = await http.get<httpNs.Response<AgentAPIConfig[]>>("/admin/agent-api-configs");
    configs.value = res.data || [];
  } catch (err: any) {
    ElMessage.error(err?.message || String(t("_agentAPI.fetchFailed")));
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  dialogTitle.value = String(t("_agentAPI.addConfig"));
  isEditing.value = false;
  editId.value = null;
  form.name = "";
  form.base_url = "";
  form.api_key = "";
  form.model_list_str = "";
  form.default_model = "";
  form.is_active = true;
  form.is_default = false;
  dialogVisible.value = true;
}

function openEdit(row: AgentAPIConfig) {
  dialogTitle.value = String(t("_agentAPI.editConfig"));
  isEditing.value = true;
  editId.value = row.id;
  form.name = row.name;
  form.base_url = row.base_url;
  form.api_key = ""; // 留空表示不修改密钥
  form.model_list_str = (row.model_list || []).join(", ");
  form.default_model = row.default_model;
  form.is_active = row.is_active;
  form.is_default = row.is_default;
  dialogVisible.value = true;
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  const model_list = form.model_list_str
    .split(",")
    .map(m => m.trim())
    .filter(Boolean);

  const payload: Record<string, any> = {
    name: form.name,
    base_url: form.base_url,
    model_list,
    default_model: form.default_model || (model_list[0] ?? ""),
    is_active: form.is_active,
    is_default: form.is_default,
  };
  if (form.api_key || !isEditing.value) {
    payload.api_key = form.api_key;
  }

  try {
    if (isEditing.value && editId.value) {
      await http.put<httpNs.Response<AgentAPIConfig>>(`/admin/agent-api-configs/${editId.value}`, payload);
      ElMessage.success(String(t("_agentAPI.updateSuccess")));
    } else {
      await http.post<httpNs.Response<AgentAPIConfig>>("/admin/agent-api-configs", payload);
      ElMessage.success(String(t("_agentAPI.createSuccess")));
    }
    dialogVisible.value = false;
    fetchConfigs();
  } catch (err: any) {
    ElMessage.error(err?.message || String(t("_agentAPI.saveFailed")));
  }
}

async function handleDelete(row: AgentAPIConfig) {
  try {
    await ElMessageBox.confirm(
      String(t("_agentAPI.deleteConfirm")).replace("{name}", row.name),
      String(t("_agentAPI.deleteTitle")),
      { type: "warning" }
    );
    await http.delete(`/admin/agent-api-configs/${row.id}`);
    ElMessage.success(String(t("_agentAPI.deleteSuccess")));
    fetchConfigs();
  } catch {
    /* cancelled or error */
  }
}

async function setDefault(row: AgentAPIConfig) {
  try {
    await http.put<httpNs.Response<AgentAPIConfig>>(`/admin/agent-api-configs/${row.id}/default`);
    ElMessage.success(String(t("_agentAPI.setDefaultSuccess")));
    fetchConfigs();
  } catch (err: any) {
    ElMessage.error(err?.message || String(t("_agentAPI.operationFailed")));
  }
}

function maskKey(key: string): string {
  if (!key) return "";
  if (key.length <= 8) return "****";
  return key.slice(0, 4) + "****" + key.slice(-4);
}

onMounted(() => {
  fetchConfigs();
});
</script>

<template>
  <div class="agent-api-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>{{ t("_agentAPI.title") }}</h2>
      <p class="desc">{{ t("_agentAPI.description") }}</p>
    </div>

    <!-- 操作栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="search"
          :placeholder="String(t('_agentAPI.searchPlaceholder'))"
          clearable
          :prefix-icon="Search"
          style="width: 280px"
          @clear="fetchConfigs"
          @keyup.enter="fetchConfigs"
        />
        <el-button :icon="Refresh" @click="fetchConfigs" />
      </div>
      <div class="toolbar-right">
        <el-button type="primary" :icon="Plus" @click="openCreate">
          {{ t("_agentAPI.addConfig") }}
        </el-button>
      </div>
    </div>

    <!-- 配置列表 -->
    <div v-loading="loading" class="config-cards">
      <div v-if="filteredConfigs.length === 0 && !loading" class="empty-state">
        <el-empty :description="t('_agentAPI.noConfig')" />
      </div>
      <div
        v-for="config in filteredConfigs"
        :key="config.id"
        class="config-card"
        :class="{ default: config.is_default }"
      >
        <div class="card-header">
          <div class="card-title">
            <el-icon :size="20"><Connection /></el-icon>
            <span class="name">{{ config.name }}</span>
            <el-tag v-if="config.is_default" type="success" size="small" effect="dark">
              {{ t("_agentAPI.default") }}
            </el-tag>
            <el-tag v-if="!config.is_active" type="danger" size="small" effect="dark">
              {{ t("_agentAPI.disabled") }}
            </el-tag>
          </div>
          <div class="card-actions">
            <el-tooltip :content="String(t('_agentAPI.setDefault'))" v-if="!config.is_default">
              <el-button type="success" :icon="Check" circle size="small" @click="setDefault(config)" />
            </el-tooltip>
            <el-button :icon="Edit" circle size="small" @click="openEdit(config)" />
            <el-button :icon="Delete" circle size="small" type="danger" @click="handleDelete(config)" />
          </div>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">URL:</span>
            <code>{{ config.base_url }}</code>
          </div>
          <div class="info-row">
            <span class="label">Key:</span>
            <code>{{ maskKey(config.api_key) }}</code>
          </div>
          <div class="info-row">
            <span class="label">{{ t("_agentAPI.models") }}:</span>
            <div class="model-tags">
              <el-tag
                v-for="model in config.model_list"
                :key="model"
                size="small"
                :type="model === config.default_model ? 'primary' : 'info'"
              >
                {{ model }}
                <span v-if="model === config.default_model" class="default-dot">●</span>
              </el-tag>
            </div>
          </div>
          <div class="card-footer-info">
            <span>{{ t("_agentAPI.createdBy") }}: {{ config.creator_name }}</span>
            <span>{{ config.updated_at }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="580px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item :label="String(t('_agentAPI.form.name'))" prop="name">
          <el-input v-model="form.name" :placeholder="String(t('_agentAPI.form.namePlaceholder'))" />
        </el-form-item>
        <el-form-item :label="String(t('_agentAPI.form.baseUrl'))" prop="base_url">
          <el-input v-model="form.base_url" :placeholder="String(t('_agentAPI.form.baseUrlPlaceholder'))" />
        </el-form-item>
        <el-form-item :label="String(t('_agentAPI.form.apiKey'))" prop="api_key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="
              isEditing
                ? String(t('_agentAPI.form.apiKeyPlaceholderEdit'))
                : String(t('_agentAPI.form.apiKeyPlaceholder'))
            "
          />
        </el-form-item>
        <el-form-item :label="String(t('_agentAPI.form.models'))" prop="model_list_str">
          <el-input v-model="form.model_list_str" :placeholder="String(t('_agentAPI.form.modelsPlaceholder'))" />
          <div class="form-tip">{{ t("_agentAPI.form.modelsTip") }}</div>
        </el-form-item>
        <el-form-item :label="String(t('_agentAPI.form.defaultModel'))">
          <el-input v-model="form.default_model" :placeholder="String(t('_agentAPI.form.defaultModelPlaceholder'))" />
        </el-form-item>
        <el-form-item :label="String(t('_agentAPI.form.status'))">
          <el-switch v-model="form.is_active" />
          <span style="margin-left: 8px; color: var(--tk-gray-color-500)">
            {{ form.is_active ? t("_agentAPI.form.enabled") : t("_agentAPI.form.disabled") }}
          </span>
        </el-form-item>
        <el-form-item :label="String(t('_agentAPI.form.setDefault'))">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t("_agentAPI.form.cancel") }}</el-button>
        <el-button type="primary" @click="handleSave">{{ t("_agentAPI.form.confirm") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.agent-api-container {
  padding: 20px;

  .page-header {
    margin-bottom: 20px;
    h2 {
      margin: 0 0 6px;
      font-size: 20px;
      font-weight: 600;
      color: var(--tk-surface-gray-color);
    }
    .desc {
      margin: 0;
      color: var(--tk-gray-color-500);
      font-size: 14px;
    }
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    .toolbar-left {
      display: flex;
      gap: 8px;
      align-items: center;
    }
  }

  .config-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 16px;
  }

  .config-card {
    background: var(--tk-surface-bg-color-box);
    border: 1px solid var(--tk-surface-border-color);
    border-radius: 10px;
    padding: 20px;
    transition:
      box-shadow 0.25s ease,
      border-color 0.25s ease;

    &:hover {
      box-shadow: var(--tk-box-shadow-md);
    }

    &.default {
      border-color: var(--tk-color-success);
      background: color-mix(in srgb, var(--tk-color-success) 6%, var(--tk-surface-bg-color-box));
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      .card-title {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--tk-color-primary);
        .name {
          font-size: 16px;
          font-weight: 600;
          color: var(--tk-surface-gray-color);
        }
      }
      .card-actions {
        display: flex;
        gap: 6px;
      }
    }

    .card-body {
      .info-row {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        gap: 8px;
        .label {
          color: var(--tk-gray-color-500);
          font-size: 13px;
          min-width: 40px;
        }
        code {
          background: var(--tk-gray-color-100);
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 13px;
          color: var(--tk-gray-color-700);
          word-break: break-all;
        }
        .model-tags {
          display: flex;
          gap: 4px;
          flex-wrap: wrap;
          .default-dot {
            margin-left: 4px;
            color: var(--tk-color-primary);
          }
        }
      }
      .card-footer-info {
        display: flex;
        justify-content: space-between;
        margin-top: 12px;
        padding-top: 8px;
        border-top: 1px solid var(--tk-surface-border-color);
        font-size: 12px;
        color: var(--tk-gray-color-400);
      }
    }
  }

  .empty-state {
    grid-column: 1 / -1;
    padding: 60px 0;
  }
  .form-tip {
    font-size: 12px;
    color: var(--tk-gray-color-500);
    margin-top: 4px;
  }
}

.form-tip {
  font-size: 12px;
  color: var(--tk-gray-color-500);
  margin-top: 4px;
}
</style>
