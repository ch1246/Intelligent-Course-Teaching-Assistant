<script setup lang="ts">
import { computed } from "vue";
import { useUserStore } from "@/pinia";
import { storeToRefs } from "pinia";
import { ElMessage } from "element-plus";
import { t } from "@/common/languages";

defineOptions({ name: "PermissionSwitch" });

const userStore = useUserStore();
const { roles } = storeToRefs(userStore);

const currentRole = computed(() => {
  const r = roles.value;
  if (!r || r.length === 0) return t("_permission.studentRole");
  if (r.includes("admin")) return t("_permission.adminRole");
  if (r.includes("teacher")) return t("_permission.teacherRole");
  return t("_permission.studentRole");
});

const roleCards = [
  {
    key: "admin",
    name: t("_permission.adminRole"),
    desc: t("_permission.adminDesc"),
    icon: "ep:avatar",
    color: "#667eea",
    gradient: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
  },
  {
    key: "teacher",
    name: t("_permission.teacherRole"),
    desc: t("_permission.teacherDesc"),
    icon: "ep:user",
    color: "#67c23a",
    gradient: "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
  },
  {
    key: "student",
    name: t("_permission.studentRole"),
    desc: t("_permission.studentDesc"),
    icon: "ep:user-filled",
    color: "#409eff",
    gradient: "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
  },
];

const isCurrentRole = (roleKey: string) => {
  if (roleKey === "admin" && roles.value.includes("admin")) return true;
  if (roleKey === "teacher" && roles.value.includes("teacher")) return true;
  if (roleKey === "student" && !roles.value.includes("admin") && !roles.value.includes("teacher")) return true;
  return false;
};

const switchTo = async (roleKey: string) => {
  if (isCurrentRole(roleKey)) return;

  const roleMap: Record<string, string[]> = {
    admin: ["admin"],
    teacher: ["teacher"],
    student: [],
  };

  await userStore.changeRoles(roleMap[roleKey]);
  const name = roleCards.find(c => c.key === roleKey)?.name || roleKey;
  ElMessage.success(t("_permission.switchSuccess", { role: name }));
};
</script>

<template>
  <div class="permission-switch">
    <div class="page-header">
      <h2 class="page-title">{{ $t("_permission.switchTitle") }}</h2>
      <p class="page-desc">{{ $t("_permission.switchDesc") }}</p>
    </div>

    <div class="current-badge">
      <span class="badge-label">{{ $t("_permission.currentRole") }}：</span>
      <el-tag type="primary" size="large" effect="dark" round>{{ currentRole }}</el-tag>
    </div>

    <div class="role-cards">
      <div
        v-for="card in roleCards"
        :key="card.key"
        class="role-card"
        :class="{ active: isCurrentRole(card.key) }"
        @click="switchTo(card.key)"
      >
        <div class="card-banner" :style="{ background: card.gradient }">
          <el-icon :size="40" color="#fff">
            <component :is="card.icon" />
          </el-icon>
        </div>
        <div class="card-body">
          <h3 class="card-name">{{ card.name }}</h3>
          <p class="card-desc">{{ card.desc }}</p>
        </div>
        <div v-if="isCurrentRole(card.key)" class="card-check">
          <el-icon :size="20" color="#fff"><Icon icon="ep:check" /></el-icon>
        </div>
      </div>
    </div>

    <div class="verify-section">
      <h3 class="section-title">{{ $t("_permission.permissionVerify") }}</h3>
      <el-alert
        :title="$t('_permission.adminPermissionTip')"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 20px"
      />

      <el-row :gutter="20">
        <el-col :span="8">
          <div class="verify-card">
            <div class="verify-card-header">
              <Icon icon="ep:connection" :size="20" />
              <span>{{ $t("_permission.componentVerify") }}</span>
            </div>
            <p class="verify-card-desc">{{ $t("_permission.componentVerifyDesc") }}</p>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="verify-card">
            <div class="verify-card-header">
              <Icon icon="ep:guide" :size="20" />
              <span>{{ $t("_permission.directiveVerify") }}</span>
            </div>
            <p class="verify-card-desc">{{ $t("_permission.directiveVerifyDesc") }}</p>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="verify-card">
            <div class="verify-card-header">
              <Icon icon="ep:operation" :size="20" />
              <span>{{ $t("_permission.functionVerify") }}</span>
            </div>
            <p class="verify-card-desc">{{ $t("_permission.functionVerifyDesc") }}</p>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.permission-switch {
  padding: 4px 0;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 8px;
}

.page-desc {
  font-size: 14px;
  color: var(--tk-gray-color-500);
  margin: 0;
}

.current-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 28px;

  .badge-label {
    font-size: 14px;
    color: var(--tk-gray-color-600);
  }
}

.role-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 36px;
}

.role-card {
  position: relative;
  background: var(--tk-surface-bg-color-box);
  border: 2px solid var(--tk-surface-border-color);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition:
    transform 0.2s,
    box-shadow 0.2s,
    border-color 0.2s;

  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--tk-box-shadow-md);
  }

  &.active {
    border-color: var(--tk-color-primary);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--tk-color-primary) 20%, transparent);
  }
}

.card-banner {
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-body {
  padding: 20px;
}

.card-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 8px;
}

.card-desc {
  font-size: 13px;
  color: var(--tk-gray-color-500);
  line-height: 1.6;
  margin: 0;
}

.card-check {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--tk-color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.verify-section {
  .section-title {
    font-size: 17px;
    font-weight: 600;
    color: var(--tk-gray-color-900);
    margin: 0 0 16px;
  }
}

.verify-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 8px;
  padding: 20px;

  .verify-card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: var(--tk-gray-color-800);
    margin-bottom: 10px;
  }

  .verify-card-desc {
    font-size: 13px;
    color: var(--tk-gray-color-500);
    line-height: 1.6;
  }
}

@media (max-width: 768px) {
  .role-cards {
    grid-template-columns: 1fr;
  }
}
</style>
