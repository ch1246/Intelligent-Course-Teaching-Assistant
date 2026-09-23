<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Edit, Delete, Check, Setting } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "AdminContextStrategy" });

interface ContextStrategy {
  id: number;
  name: string;
  description: string;
  top_k: number;
  similarity_threshold: number;
  chunk_size: number;
  chunk_overlap: number;
  max_context_tokens: number;
  include_memory: boolean;
  include_history: boolean;
  history_turns: number;
  rerank_enabled: boolean;
  enable_query_rewrite: boolean;
  compression_method: string;
  is_active: boolean;
  is_default: boolean;
  creator_name: string;
  created_at: string;
  updated_at: string;
}

const list = ref<ContextStrategy[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const dialogTitle = ref("");
const isEditing = ref(false);
const editId = ref<number | null>(null);

const form = ref({
  name: "",
  description: "",
  top_k: 5,
  similarity_threshold: 0.0,
  chunk_size: 500,
  chunk_overlap: 50,
  max_context_tokens: 3000,
  include_memory: true,
  include_history: true,
  history_turns: 10,
  rerank_enabled: false,
  enable_query_rewrite: false,
  compression_method: "truncate",
  is_active: true,
  is_default: false,
});

async function fetchList() {
  loading.value = true;
  try {
    const res: any = await http.get("/admin/context-strategies");
    list.value = res.data.list || [];
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.fetchFailed"));
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  dialogTitle.value = t("_contextStrategy.createTitle");
  isEditing.value = false;
  editId.value = null;
  form.value = {
    name: "",
    description: "",
    top_k: 5,
    similarity_threshold: 0.0,
    chunk_size: 500,
    chunk_overlap: 50,
    max_context_tokens: 3000,
    include_memory: true,
    include_history: true,
    history_turns: 10,
    rerank_enabled: false,
    enable_query_rewrite: false,
    compression_method: "truncate",
    is_active: true,
    is_default: false,
  };
  dialogVisible.value = true;
}

function openEdit(row: ContextStrategy) {
  dialogTitle.value = t("_contextStrategy.editTitle");
  isEditing.value = true;
  editId.value = row.id;
  form.value = {
    name: row.name,
    description: row.description,
    top_k: row.top_k,
    similarity_threshold: row.similarity_threshold,
    chunk_size: row.chunk_size,
    chunk_overlap: row.chunk_overlap,
    max_context_tokens: row.max_context_tokens,
    include_memory: row.include_memory,
    include_history: row.include_history,
    history_turns: row.history_turns,
    rerank_enabled: row.rerank_enabled,
    enable_query_rewrite: row.enable_query_rewrite,
    compression_method: row.compression_method,
    is_active: row.is_active,
    is_default: row.is_default,
  };
  dialogVisible.value = true;
}

async function handleSave() {
  if (!form.value.name) {
    ElMessage.warning(t("_contextStrategy.nameRequired"));
    return;
  }
  try {
    if (isEditing.value && editId.value) {
      await http.put(`/admin/context-strategies/${editId.value}`, form.value);
      ElMessage.success(t("_common.saveSuccess"));
    } else {
      await http.post("/admin/context-strategies", form.value);
      ElMessage.success(t("_common.createSuccess"));
    }
    dialogVisible.value = false;
    fetchList();
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.operationFailed"));
  }
}

async function handleDelete(row: ContextStrategy) {
  try {
    await ElMessageBox.confirm(
      t("_common.confirmDelete", { name: row.name }),
      t("_common.confirm"),
      { type: "warning" }
    );
    await http.delete(`/admin/context-strategies/${row.id}`);
    ElMessage.success(t("_common.deleteSuccess"));
    fetchList();
  } catch {
    /* cancelled */
  }
}

async function setDefault(row: ContextStrategy) {
  try {
    await http.put(`/admin/context-strategies/${row.id}/default`);
    ElMessage.success(t("_common.setDefaultSuccess"));
    fetchList();
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.operationFailed"));
  }
}

onMounted(fetchList);
</script>

<template>
  <div class="context-strategy-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t("_route.AdminContextStrategies") }}</span>
          <el-button type="primary" :icon="Plus" @click="openCreate">
            {{ t("_contextStrategy.createTitle") }}
          </el-button>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" :label="t('_contextStrategy.name')" min-width="160" />
        <el-table-column :label="t('_contextStrategy.topK')" width="80" align="center">
          <template #default="{ row }">{{ row.top_k }}</template>
        </el-table-column>
        <el-table-column :label="t('_contextStrategy.simThreshold')" width="100" align="center">
          <template #default="{ row }">{{ row.similarity_threshold }}</template>
        </el-table-column>
        <el-table-column :label="t('_contextStrategy.chunkSize')" width="90" align="center">
          <template #default="{ row }">{{ row.chunk_size }}</template>
        </el-table-column>
        <el-table-column :label="t('_contextStrategy.maxTokens')" width="110" align="center">
          <template #default="{ row }">{{ row.max_context_tokens }}</template>
        </el-table-column>
        <el-table-column :label="t('_contextStrategy.memory')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.include_memory ? 'success' : 'info'" size="small">
              {{ row.include_memory ? t("_common.on") : t("_common.off") }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('_contextStrategy.history')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.include_history ? 'success' : 'info'" size="small">
              {{ row.include_history ? t("_common.on") : t("_common.off") }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('_contextStrategy.compression')" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.compression_method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('_common.default')" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="warning" size="small">{{ t("_common.default") }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('_common.actions')" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :icon="Edit" @click="openEdit(row)">{{ t("_common.edit") }}</el-button>
            <el-button v-if="!row.is_default" size="small" :icon="Check" type="success" @click="setDefault(row)">
              {{ t("_common.setDefault") }}
            </el-button>
            <el-button size="small" :icon="Delete" type="danger" @click="handleDelete(row)">
              {{ t("_common.delete") }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px" destroy-on-close>
      <el-form :model="form" label-width="140px">
        <el-divider content-position="left">{{ t("_contextStrategy.basicInfo") }}</el-divider>
        <el-form-item :label="t('_contextStrategy.name')">
          <el-input v-model="form.name" :placeholder="t('_contextStrategy.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('_contextStrategy.description')">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>

        <el-divider content-position="left">{{ t("_contextStrategy.retrievalParams") }}</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="t('_contextStrategy.topK')">
              <el-input-number v-model="form.top_k" :min="1" :max="20" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('_contextStrategy.simThreshold')">
              <el-slider v-model="form.similarity_threshold" :min="0" :max="1" :step="0.05" show-input :format-tooltip="(v: number) => v.toFixed(2)" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">{{ t("_contextStrategy.chunkParams") }}</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="t('_contextStrategy.chunkSize')">
              <el-input-number v-model="form.chunk_size" :min="100" :max="2000" :step="50" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('_contextStrategy.chunkOverlap')">
              <el-input-number v-model="form.chunk_overlap" :min="0" :max="500" :step="10" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">{{ t("_contextStrategy.contextBudget") }}</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="t('_contextStrategy.maxTokens')">
              <el-input-number v-model="form.max_context_tokens" :min="500" :max="32000" :step="500" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('_contextStrategy.compression')">
              <el-select v-model="form.compression_method">
                <el-option label="截断 (truncate)" value="truncate" />
                <el-option label="LLM 摘要 (summarize)" value="summarize" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">{{ t("_contextStrategy.contentSwitches") }}</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item :label="t('_contextStrategy.memory')">
              <el-switch v-model="form.include_memory" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('_contextStrategy.history')">
              <el-switch v-model="form.include_history" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('_contextStrategy.historyTurns')">
              <el-input-number v-model="form.history_turns" :min="1" :max="50" :disabled="!form.include_history" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">{{ t("_contextStrategy.advanced") }}</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="t('_contextStrategy.rerank')">
              <el-switch v-model="form.rerank_enabled" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('_contextStrategy.queryRewrite')">
              <el-switch v-model="form.enable_query_rewrite" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="t('_common.status')">
          <el-switch v-model="form.is_active" :active-text="t('_common.active')" :inactive-text="t('_common.inactive')" />
          <el-switch v-model="form.is_default" :active-text="t('_common.setDefault')" style="margin-left: 20px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t("_common.cancel") }}</el-button>
        <el-button type="primary" @click="handleSave">{{ t("_common.confirm") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
