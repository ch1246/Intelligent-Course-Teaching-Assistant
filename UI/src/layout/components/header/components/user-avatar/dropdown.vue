<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { ElDropdown, ElDropdownMenu, ElDropdownItem, ElImage, ElMessage, ElMessageBox } from "element-plus";
import { ArrowDownBold, Back, View } from "@element-plus/icons-vue";
import { serviceConfig, LOGIN_URL } from "@/common/config";
import { useNamespace } from "@/composables";
import { useUserStore } from "@/pinia";

defineOptions({ name: "UserAvatarDropdown" });

const ns = useNamespace("user-avatar-dropdown");

withDefaults(defineProps<{ showAvatar?: boolean }>(), {
  showAvatar: true,
});

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const userStore = useUserStore();

const { userInfo } = storeToRefs(userStore);

import { User, Lock, Cpu, FolderOpened } from "@element-plus/icons-vue";

const isAdmin = computed(() => userStore.roles.includes("admin"));

const allMenuItems = [
  { label: t("_route.Profile"), icon: User, click: () => toPage("/profile"), adminOnly: false },
  { label: t("_route.ChangePassword"), icon: Lock, click: () => toPage("/change-password"), adminOnly: false },
  { label: t("_route.AdminDefaultModel"), icon: Cpu, click: () => toPage("/admin/default-model"), adminOnly: true },
  { label: t("_route.FileManagement"), icon: FolderOpened, click: () => toPage("/file-management"), adminOnly: true },
];

const menuList = computed(() => allMenuItems.filter(item => !item.adminOnly || isAdmin.value));

/**
 * 跳转页面
 */
const toPage = (path: string) => {
  router.push(path);
};

/**
 * 退出登录
 */
const logout = async () => {
  const logOutI18n = t("_headerBar.logout") as Record<string, string>;
  ElMessageBox.confirm(logOutI18n.confirm, logOutI18n.confirmTitle, {
    confirmButtonText: t("_headerBar.ok"),
    cancelButtonText: t("_headerBar.cancel"),
    type: "warning",
  }).then(async () => {
    await userStore.logout();
    router.push(`${LOGIN_URL}?redirect=${route.path}`);
    ElMessage.success(logOutI18n.success);
  });
};
</script>

<template>
  <el-dropdown :class="ns.b()" class="customize" trigger="hover">
    <div class="flx-align-center">
      <template v-if="showAvatar">
        <el-image :src="userInfo.avatar" :class="ns.e('avatar')" alt="头像">
          <template #error>
            <el-image :src="serviceConfig.layout.avatar" alt="头像" />
          </template>
        </el-image>

        <span :class="ns.em('avatar', 'username')">{{ userInfo.username }}</span>
      </template>

      <Icon size="1em"><ArrowDownBold /></Icon>
    </div>

    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item v-for="item in menuList" :key="item.label" :icon="item.icon || View" @click="item.click">
          {{ item.label }}
        </el-dropdown-item>

        <el-dropdown-item divided :icon="Back" @click="logout">
          {{ t("_headerBar.logOut") }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style lang="scss" scoped>
@use "@styles/mixins/bem" as *;

@include b(user-avatar-dropdown) {
  @include e(avatar) {
    width: 35px;
    height: 35px;
    cursor: pointer;
    border-radius: 50%;

    @include m(username) {
      display: inline-block;
      margin: 0 7px 0 9px;
      font-size: 14px;
      cursor: pointer;
      user-select: none;
    }
  }
}
</style>
