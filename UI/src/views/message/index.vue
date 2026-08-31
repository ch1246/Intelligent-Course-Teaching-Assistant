<script setup lang="ts">
import { ChatLineSquare } from "@element-plus/icons-vue";

defineOptions({ name: "Message" });
</script>

<template>
  <div class="message-page">
    <h2 class="page-title">{{ $t("_profile.myMessages") }}</h2>
    <div class="empty-card">
      <div class="empty-icon-circle">
        <el-icon :size="36"><ChatLineSquare /></el-icon>
      </div>
      <h3 class="empty-title">{{ $t("_profile.myMessages") }}</h3>
      <p class="empty-description">{{ $t("_profile.noMessagesYet") }}</p>
      <el-button type="primary" @click="$router.push('/profile')">
        {{ $t("_common.back") }}
      </el-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.message-page {
  padding: 4px 0;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 24px;
}

.empty-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 64px 24px;
  box-shadow: var(--tk-box-shadow-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.empty-icon-circle {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 24px;
  box-shadow: 0 6px 20px rgba(79, 70, 229, 0.3);
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 8px;
}

.empty-description {
  font-size: 14px;
  color: var(--tk-gray-color-500);
  margin: 0 0 24px;
  line-height: 1.5;
}
</style>
