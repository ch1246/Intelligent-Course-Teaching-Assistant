<script setup lang="ts">
import { ref, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import { ElButton, ElDrawer, ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { LOGIN_URL, OpenThemePanelKey } from "@/common/config";
import { mittBus } from "@/common/utils";
import { useCommon, useNamespace, useTheme } from "@/composables";
import { useSettingStore, useUserStore } from "@/pinia";
import { GlobalTheme } from "./components"; // MenuTheme / BaseConfig / BrowserTitle 在下方模板里被注释掉了，需要时再引入

import "./index.scss";
import router from "@/router";

defineOptions({ name: "ThemePanel" });

const ns = useNamespace("theme-panel");

const { t } = useI18n();
const userStore = useUserStore();
const settingStore = useSettingStore();
const { changeGlobalTheme, changeThemeSurface } = useTheme();

const { isMobile } = useCommon();

const resetSetting = () => {
  settingStore.$reset();
  changeGlobalTheme();
  changeThemeSurface();
};

/**
 * 退出登录
 */
const clearSettingCache = async () => {
  ElMessageBox.confirm(t("_headerBar.logout.confirm"), t("_headerBar.logout.confirmTitle"), {
    type: "warning",
  }).then(async () => {
    resetSetting();
    // 调用退出登录接口
    await userStore.logout();
    ElMessage.success(t("_headerBar.logout.success"));

    await nextTick();
    // 重定向到登陆页
    router.push(`${LOGIN_URL}?redirect=${router.currentRoute.value.path}`);
  });
};

/**
 * 打开主题设置
 */
const drawerVisible = ref(false);
mittBus.on(OpenThemePanelKey, () => (drawerVisible.value = true));
</script>

<template>
  <el-drawer
    v-model="drawerVisible"
    :size="360"
    :lock-scroll="false"
    :with-header="isMobile"
    :class="ns.b()"
    :modal-class="ns.b('modal')"
  >
    <template v-if="!isMobile">
      <!-- 布局切换仅保留经典布局，已锁定 -->
    </template>

    <!-- 全局主题 -->
    <h3>{{ $t("_setting.theme.label") }}</h3>

    <GlobalTheme />

    <!-- 菜单主题、基础配置、标题设置已固定，不再开放修改 -->
    <!-- <MenuTheme /> -->
    <!-- <BaseConfig /> -->
    <!-- <BrowserTitle /> -->

    <template #footer>
      <div class="flx-justify-between">
        <el-button plain type="primary" :icon="Refresh" @click="resetSetting">
          {{ $t("_setting.resetSetting") }}
        </el-button>

        <el-button plain @click="clearSettingCache">
          {{ $t("_setting.clearSettingCache") }}
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>
