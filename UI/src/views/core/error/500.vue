<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { HOME_URL } from "@/common/config";
import { useNamespace } from "@/composables";
import { useUserStore } from "@/pinia";

defineOptions({ name: "500" });

const ns = useNamespace("error-page");

const router = useRouter();
const userStore = useUserStore();
const { userInfo } = storeToRefs(userStore);

const homePath = computed(() => {
  const roles = userInfo.value.roles || [];
  if (roles.includes("admin")) return "/admin/dashboard";
  return HOME_URL;
});
</script>

<template>
  <div :class="ns.b()" class="flx-center">
    <img src="@/common/assets/images/status/500.png" :class="ns.e('img')" alt="500" />
    <div :class="ns.e('detail')">
      <h2>500</h2>
      <h4>{{ $t("_errorPage.serverError") }}</h4>
      <el-button type="primary" @click="router.push(homePath)">{{ $t("_common.backToHome") }}</el-button>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use "./index";
</style>
