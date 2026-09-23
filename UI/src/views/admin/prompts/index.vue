<template>
  <div class="prompt-templates-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t("_route.AdminPrompts") }}</span>
          <div class="header-actions">
            <el-input
              v-model="search"
              :placeholder="$t('_prompts.searchPlaceholder')"
              style="width: 220px"
              clearable
              @keyup.enter="onSearch"
              @clear="onSearch"
            />
            <el-select
              v-model="skillFilter"
              :placeholder="$t('_common.filterSkill')"
              clearable
              style="width: 140px; margin: 0 8px"
              @change="onSearch"
            >
              <el-option :label="$t('_prompts.skillQA')" value="qa" />
              <el-option :label="$t('_prompts.skillFormula')" value="formula" />
              <el-option :label="$t('_prompts.skillCode')" value="code_debug" />
              <el-option :label="$t('_prompts.skillLab')" value="lab_guide" />
              <el-option :label="$t('_prompts.skillPaper')" value="paper_reader" />
            </el-select>
            <el-button type="primary" @click="handleCreate">{{ $t("_prompts.createTitle") }}</el-button>
          </div>
        </div>
      </template>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" :label="$t('_prompts.name')" min-width="180" />
        <el-table-column :label="$t('_prompts.skillLabel')" width="120">
          <template #default="{ row }">
            <el-tag>{{ skillLabel(row.skill) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" :label="$t('_prompts.versionLabel')" width="80" />
        <el-table-column :label="$t('_registerApproval.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? $t("_common.active") : $t("_common.inactive") }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('_common.default')" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="warning" size="small">{{ $t("_common.default") }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" :label="$t('_common.creator')" width="100" />
        <el-table-column prop="updated_at" :label="$t('_common.updateTime')" width="170" />
        <el-table-column :label="$t('_registerApproval.actions')" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">{{ $t("_common.edit") }}</el-button>
            <el-button size="small" @click="handleVersions(row)">{{ $t("_prompts.viewVersions") }}</el-button>
            <el-button v-if="!row.is_default" size="small" type="warning" @click="handleSetDefault(row)">
              {{ $t("_common.setDefault") }}
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">{{ $t("_common.delete") }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 16px; text-align: right">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total,sizes,prev,pager,next"
          @change="fetchList"
        />
      </div>
    </el-card>

    <!-- Version history dialog -->
    <el-dialog v-model="versionVisible" :title="$t('_prompts.viewVersions')" width="700px">
      <el-table :data="versions" stripe max-height="400">
        <el-table-column prop="version" :label="$t('_prompts.versionLabel')" width="80" />
        <el-table-column prop="change_note" :label="$t('_prompts.changeNote')" min-width="180" />
        <el-table-column prop="creator_name" :label="$t('_common.creator')" width="100" />
        <el-table-column prop="created_at" :label="$t('_common.time')" width="170" />
        <el-table-column :label="$t('_registerApproval.actions')" width="100">
          <template #default="{ row: vrow }">
            <el-button size="small" @click="handleRollback(vrow)">{{ $t("_prompts.rollback") }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { http } from "@/common/http";
import { t } from "@/common/languages";

defineOptions({ name: "AdminPrompts" });

const router = useRouter();
const list = ref<any[]>([]);
const loading = ref(false);
const search = ref("");
const skillFilter = ref("");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const versions = ref<any[]>([]);
const versionVisible = ref(false);

const skillMap: Record<string, string> = {
  qa: t("_prompts.skillQA"),
  formula: t("_prompts.skillFormula"),
  code_debug: t("_prompts.skillCode"),
  lab_guide: t("_prompts.skillLab"),
  paper_reader: t("_prompts.skillPaper"),
};
const skillLabel = (s: string) => skillMap[s] || s;

async function fetchList() {
  loading.value = true;
  try {
    const res: any = await http.get("/admin/prompts", {
      params: {
        page: page.value,
        pageSize: pageSize.value,
        skill: skillFilter.value || undefined,
        keyword: search.value || undefined,
      },
    });
    list.value = res.data.list;
    total.value = res.data.total;
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.fetchFailed"));
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  page.value = 1;
  fetchList();
}

function handleCreate() {
  router.push("/admin/prompts/create");
}
function handleEdit(row: any) {
  router.push(`/admin/prompts/${row.id}/edit`);
}

async function handleVersions(row: any) {
  try {
    const res: any = await http.get(`/admin/prompts/${row.id}/versions`);
    versions.value = res.data;
    versionVisible.value = true;
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.fetchFailed"));
  }
}

async function handleRollback(vrow: any) {
  try {
    await ElMessageBox.confirm(t("_prompts.rollbackConfirm"), t("_common.confirm"), { type: "warning" });
    await http.post(`/admin/prompts/${vrow.template}/rollback`, { version_id: vrow.id });
    ElMessage.success(t("_prompts.rollbackSuccess"));
    versionVisible.value = false;
    fetchList();
  } catch {
    /* cancelled or error */
  }
}

async function handleSetDefault(row: any) {
  try {
    await http.put(`/admin/prompts/${row.id}/default`);
    ElMessage.success(t("_common.setDefaultSuccess"));
    fetchList();
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.operationFailed"));
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(t("_common.confirmDelete", { name: row.name }), t("_common.confirm"), { type: "warning" });
    await http.delete(`/admin/prompts/${row.id}`);
    ElMessage.success(t("_common.deleteSuccess"));
    fetchList();
  } catch {
    /* cancelled or error */
  }
}

onMounted(fetchList);
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
