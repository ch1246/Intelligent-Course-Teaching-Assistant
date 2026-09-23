<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Refresh, View } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "AdminTraces" });

interface TraceLog {
  id: number;
  session: number;
  pipeline: number | null;
  phase: string;
  duration_ms: number;
  detail: Record<string, any>;
  created_at: string;
}

const list = ref<TraceLog[]>([]);
const loading = ref(false);
const total = ref(0);
const page = ref(1);
const pageSize = ref(50);
const phaseFilter = ref("");
const detailVisible = ref(false);
const currentDetail = ref<Record<string, any>>({});
const currentPhase = ref("");

const phaseOptions = [
  { value: "", label: "全部" },
  { value: "retrieve", label: "检索" },
  { value: "build_prompt", label: "组装提示词" },
  { value: "generate", label: "生成" },
  { value: "memory", label: "记忆更新" },
];

const phaseColors: Record<string, string> = {
  retrieve: "#6366f1",
  build_prompt: "#8b5cf6",
  generate: "#f59e0b",
  memory: "#22c55e",
};

async function fetchList() {
  loading.value = true;
  try {
    const res: any = await http.get("/admin/traces", {
      params: {
        page: page.value,
        pageSize: pageSize.value,
        phase: phaseFilter.value || undefined,
      },
    });
    list.value = res.data.list || [];
    total.value = res.data.total || 0;
  } catch (err: any) {
    ElMessage.error(err?.message || t("_common.fetchFailed"));
  } finally {
    loading.value = false;
  }
}

function viewDetail(trace: TraceLog) {
  currentPhase.value = trace.phase;
  currentDetail.value = trace.detail || {};
  detailVisible.value = true;
}

function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}μs`;
  if (ms < 1000) return `${ms.toFixed(1)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function phaseLabel(phase: string): string {
  const map: Record<string, string> = {
    retrieve: "检索",
    build_prompt: "组装提示词",
    generate: "生成",
    memory: "记忆更新",
  };
  return map[phase] || phase;
}

onMounted(fetchList);
</script>

<template>
  <div class="traces-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t("_route.AdminTraces") }}</span>
          <div class="header-actions">
            <el-select v-model="phaseFilter" clearable :placeholder="t('_trace.filterPhase')" style="width: 140px" @change="fetchList">
              <el-option v-for="opt in phaseOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
            <el-button :icon="Refresh" @click="fetchList" />
          </div>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column :label="t('_trace.session')" width="90" align="center">
          <template #default="{ row }">#{{ row.session }}</template>
        </el-table-column>
        <el-table-column :label="t('_trace.phase')" width="120">
          <template #default="{ row }">
            <el-tag :color="phaseColors[row.phase]" effect="dark" size="small" style="border: none; color: #fff">
              {{ phaseLabel(row.phase) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('_trace.duration')" width="120" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.duration_ms > 1000 ? '#f59e0b' : 'inherit', fontWeight: row.duration_ms > 1000 ? 600 : 400 }">
              {{ formatDuration(row.duration_ms) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="t('_trace.detailPreview')" min-width="300">
          <template #default="{ row }">
            <code class="detail-preview">{{ JSON.stringify(row.detail).slice(0, 120) }}{{ JSON.stringify(row.detail).length > 120 ? "..." : "" }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="t('_common.time')" width="170" />
        <el-table-column :label="t('_common.actions')" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :icon="View" @click="viewDetail(row)">{{ t("_trace.viewDetail") }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; text-align: right">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total,sizes,prev,pager,next"
          @change="fetchList"
        />
      </div>
    </el-card>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" :title="`${t('_trace.traceDetail')} - ${phaseLabel(currentPhase)}`" width="700px">
      <div class="detail-content">
        <div v-for="(value, key) in currentDetail" :key="key" class="detail-row">
          <span class="detail-key">{{ key }}</span>
          <span class="detail-value" v-if="typeof value === 'object'">
            <pre>{{ JSON.stringify(value, null, 2) }}</pre>
          </span>
          <span class="detail-value" v-else>{{ value }}</span>
        </div>
        <el-empty v-if="Object.keys(currentDetail).length === 0" :description="t('_trace.noDetail')" />
      </div>
    </el-dialog>
  </div>
</template>

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
.detail-preview {
  font-size: 12px;
  color: var(--tk-gray-color-600);
  background: var(--tk-gray-color-100);
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
}
.detail-content {
  max-height: 500px;
  overflow-y: auto;
}
.detail-row {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--tk-surface-border-color);
}
.detail-key {
  min-width: 140px;
  font-weight: 600;
  color: var(--tk-gray-color-700);
  flex-shrink: 0;
}
.detail-value {
  flex: 1;
  color: var(--tk-gray-color-800);
  word-break: break-all;
  pre {
    margin: 0;
    font-size: 12px;
    white-space: pre-wrap;
    background: var(--tk-gray-color-100);
    padding: 8px;
    border-radius: 6px;
    max-height: 300px;
    overflow-y: auto;
  }
}
</style>
