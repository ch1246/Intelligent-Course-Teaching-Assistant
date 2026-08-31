<script setup lang="ts">
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { ElSwitch } from "element-plus";
import { Sunny, Moon } from "@element-plus/icons-vue";
import { useSettingStore } from "@/pinia";
import { switchThemeWithAnimation } from "@/layout/components/header/components/light-dark-switch/animation";

defineOptions({ name: "SwitchDark" });

const settingStore = useSettingStore();
const { isDark } = storeToRefs(settingStore);
const dark = ref(isDark.value);

const onAddDarkChange = (e: Event) => {
  switchThemeWithAnimation(e);
};
</script>

<template>
  <el-switch
    v-model="dark"
    @click="onAddDarkChange"
    inline-prompt
    :active-icon="Sunny"
    :inactive-icon="Moon"
    class="theme-switch"
  />
</template>

<style lang="scss" scoped>
.theme-switch {
  --el-switch-on-color: var(--tk-color-primary);
  --el-switch-off-color: var(--tk-gray-color-400);

  :deep(.el-switch__core) {
    width: 52px !important;
    height: 26px;
    border-radius: 13px;
    transition: all 0.3s ease;
  }

  :deep(.el-switch__action) {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  :deep(.el-icon) {
    font-size: 12px;
  }
}
</style>
