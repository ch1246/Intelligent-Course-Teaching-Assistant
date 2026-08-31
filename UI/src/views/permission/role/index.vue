<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { t } from "@/common/languages";

defineOptions({ name: "PermissionRole" });

interface RoleItem {
  key: string;
  name: string;
  description: string;
}

const roleList = ref<RoleItem[]>([
  { key: "admin", name: t("_permission.adminRole"), description: t("_permission.adminDesc") },
  { key: "teacher", name: t("_permission.teacherRole"), description: t("_permission.teacherDesc") },
  { key: "student", name: t("_permission.studentRole"), description: t("_permission.studentDesc") },
]);

const dialogVisible = ref(false);
const dialogTitle = ref("");
const isEdit = ref(false);
const editingKey = ref("");

const formRef = ref<FormInstance>();
const form = reactive({
  key: "",
  name: "",
  description: "",
});

const rules: FormRules = {
  key: [{ required: true, message: t("_permission.roleKeyRequired"), trigger: "blur" }],
  name: [{ required: true, message: t("_permission.roleNameRequired"), trigger: "blur" }],
};

const openCreateDialog = () => {
  isEdit.value = false;
  dialogTitle.value = t("_permission.createRole");
  form.key = "";
  form.name = "";
  form.description = "";
  dialogVisible.value = true;
};

const openEditDialog = (row: RoleItem) => {
  isEdit.value = true;
  dialogTitle.value = t("_permission.editRole");
  editingKey.value = row.key;
  form.key = row.key;
  form.name = row.name;
  form.description = row.description;
  dialogVisible.value = true;
};

const handleSubmit = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(valid => {
    if (!valid) return;

    if (isEdit.value) {
      const target = roleList.value.find(r => r.key === editingKey.value);
      if (target) {
        target.key = form.key;
        target.name = form.name;
        target.description = form.description;
      }
      ElMessage.success(t("_permission.updateSuccess"));
    } else {
      roleList.value.push({ key: form.key, name: form.name, description: form.description });
      ElMessage.success(t("_permission.createSuccess"));
    }

    dialogVisible.value = false;
  });
};

const handleDelete = (row: RoleItem) => {
  ElMessageBox.confirm(t("_permission.confirmDeleteRole", { name: row.name }), t("_common.warning"), {
    confirmButtonText: t("_common.confirm"),
    cancelButtonText: t("_common.cancel"),
    type: "warning",
  }).then(() => {
    roleList.value = roleList.value.filter(r => r.key !== row.key);
    ElMessage.success(t("_permission.deleteSuccess"));
  });
};
</script>

<template>
  <div class="permission-role">
    <div class="page-header">
      <h2 class="page-title">{{ $t("_permission.roleManagement") }}</h2>
    </div>

    <el-alert
      :title="$t('_permission.adminPermissionTip')"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    />

    <div class="toolbar">
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Icon icon="ep:plus" /></el-icon>
        {{ $t("_permission.addRole") }}
      </el-button>
    </div>

    <div class="table-wrap">
      <el-table :data="roleList" border stripe style="width: 100%">
        <el-table-column prop="key" :label="$t('_permission.roleKey')" min-width="140" />
        <el-table-column prop="name" :label="$t('_permission.roleName')" min-width="140" />
        <el-table-column prop="description" :label="$t('_permission.roleDescription')" min-width="300" />
        <el-table-column :label="$t('_common.operation')" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">
              {{ $t("_common.edit") }}
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              {{ $t("_common.delete") }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="480px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item :label="$t('_permission.roleKey')" prop="key">
          <el-input v-model="form.key" :placeholder="$t('_permission.roleKeyPlaceholder')" :disabled="isEdit" />
        </el-form-item>
        <el-form-item :label="$t('_permission.roleName')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('_permission.roleNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('_permission.roleDescription')">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('_permission.roleDescPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t("_common.cancel") }}</el-button>
        <el-button type="primary" @click="handleSubmit">{{ $t("_common.confirm") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.permission-role {
  padding: 4px 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0;
}

.toolbar {
  margin-bottom: 16px;
}

.table-wrap {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 8px;
  overflow: hidden;
}
</style>
