<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Edit, Delete, Check } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "AdminPipelines" });

interface Pipeline {
  id: number;
  name: string;
  description: string;
  prompt_template: number;
  template_name: string;
  context_strategy: number;
  strategy_name: string;
  agent_config: number;
  agent_config_name: string;
  is_active: boolean;
  is_default: boolean;
  creator_name: string;
  created_at: string;
  updated_at: string;
}

interface Option {
  id: number;
  name: string;
}

const list = ref<Pipeline[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const dialogTitle = ref("");
const isEditing = ref(false);
const editId = ref<number | null>(null);

const form = ref({
  name: "",
  description: "",
  prompt_template: null as number | null,
  context_strategy: null as number | null,
  agent_config: null as number | null,
  is_active: true,
  is_default: false,
});

const templates = ref<Option[]>([]);
const strategies = ref<Option[]>([]);
const agentConfigs = ref<Option[]>([]);

async function fetchList() {
  loading.value = true;
  try {
    const res: any = await http.get("/admin/pipelines");
    list.value = res.data.list || [];
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.fetchFailed"));
  } finally {
    loading.value = false;
  }
}

async function fetchOptions() {
  try {
    const [tRes, sRes, aRes]: any[] = await Promise.all([
      http.get("/admin/prompts", { params: { pageSize: 100 } }),
      http.get("/admin/context-strategies", { params: { pageSize: 100 } }),
      http.get("/admin/agent-api-configs"),
    ]);
    templates.value = (tRes.data?.list || []).map((t: any) => ({ id: t.id, name: t.name }));
    strategies.value = (sRes.data?.list || []).map((s: any) => ({ id: s.id, name: s.name }));
    agentConfigs.value = (aRes.data || []).map((a: any) => ({ id: a.id, name: a.name }));
  } catch {
    /* options load failure is non-critical */
  }
}

function openCreate() {
  dialogTitle.value = t("_pipeline.createTitle");
  isEditing.value = false;
  editId.value = null;
  form.value = {
    name: "",
    description: "",
    prompt_template: null,
    context_strategy: null,
    agent_config: null,
    is_active: true,
    is_default: false,
  };
  dialogVisible.value = true;
}

function openEdit(row: Pipeline) {
  dialogTitle.value = t("_pipeline.editTitle");
  isEditing.value = true;
  editId.value = row.id;
  form.value = {
    name: row.name,
    description: row.description,
    prompt_template: row.prompt_template,
    context_strategy: row.context_strategy,
    agent_config: row.agent_config,
    is_active: row.is_active,
    is_default: row.is_default,
  };
  dialogVisible.value = true;
}

async function handleSave() {
  if (!form.value.name || !form.value.prompt_template || !form.value.context_strategy || !form.value.agent_config) {
    ElMessage.warning(t("_pipeline.fieldsRequired"));
    return;
  }
  try {
    if (isEditing.value && editId.value) {
      await http.put(`/admin/pipelines/${editId.value}`, form.value);
      ElMessage.success(t("_common.saveSuccess"));
    } else {
      await http.post("/admin/pipelines", form.value);
      ElMessage.success(t("_common.createSuccess"));
    }
    dialogVisible.value = false;
    fetchList();
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.operationFailed"));
  }
}

async function handleDelete(row: Pipeline) {
  try {
    await ElMessageBox.confirm(t("_common.confirmDelete", { name: row.name }), t("_common.confirm"), {
      type: "warning",
    });
    await http.delete(`/admin/pipelines/${row.id}`);
    ElMessage.success(t("_common.deleteSuccess"));
    fetchList();
  } catch {
    /* cancelled */
  }
}

async function setDefault(row: Pipeline) {
  try {
    await http.put(`/admin/pipelines/${row.id}/default`);
    ElMessage.success(t("_common.setDefaultSuccess"));
    fetchList();
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.operationFailed"));
  }
}

onMounted(() => {
  fetchList();
  fetchOptions();
});
</script>

<template>
  <div class="pipeline-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t("_route.AdminPipelines") }}</span>
          <el-button type="primary" :icon="Plus" @click="openCreate">
            {{ t("_pipeline.createTitle") }}
          </el-button>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" :label="t('_pipeline.name')" min-width="160" />
        <el-table-column :label="t('_pipeline.template')" min-width="140">
          <template #default="{ row }">
            <el-tag type="primary" size="small">{{ row.template_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('_pipeline.strategy')" min-width="140">
          <template #default="{ row }">
            <el-tag type="success" size="small">{{ row.strategy_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('_pipeline.agentConfig')" min-width="140">
          <template #default="{ row }">
            <el-tag type="warning" size="small">{{ row.agent_config_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('_common.status')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? t("_common.active") : t("_common.inactive") }}
            </el-tag>
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
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" destroy-on-close>
      <el-form :model="form" label-width="120px">
        <el-form-item :label="t('_pipeline.name')">
          <el-input v-model="form.name" :placeholder="t('_pipeline.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('_pipeline.description')">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('_pipeline.template')">
          <el-select v-model="form.prompt_template" :placeholder="t('_pipeline.selectTemplate')" style="width: 100%">
            <el-option v-for="opt in templates" :key="opt.id" :label="opt.name" :value="opt.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('_pipeline.strategy')">
          <el-select v-model="form.context_strategy" :placeholder="t('_pipeline.selectStrategy')" style="width: 100%">
            <el-option v-for="opt in strategies" :key="opt.id" :label="opt.name" :value="opt.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('_pipeline.agentConfig')">
          <el-select v-model="form.agent_config" :placeholder="t('_pipeline.selectAgentConfig')" style="width: 100%">
            <el-option v-for="opt in agentConfigs" :key="opt.id" :label="opt.name" :value="opt.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('_common.status')">
          <el-switch
            v-model="form.is_active"
            :active-text="t('_common.active')"
            :inactive-text="t('_common.inactive')"
          />
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
