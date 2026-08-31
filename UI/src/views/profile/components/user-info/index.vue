<script setup lang="ts" name="UserCard">
import type { UserInfo } from "@/pinia";
import { computed } from "vue";
import { serviceConfig } from "@/common/config";
import { useNamespace } from "@/composables";
import { t } from "@/common/languages";

const ns = useNamespace("user-info");

const { user } = defineProps<{ user: UserInfo }>();

const userInfo = computed(() => [
  { label: t("_profile.email"), value: user.email },
  { label: t("_profile.contact"), value: user.phone },
  { label: t("_profile.gender"), value: user.sex },
  { label: t("_profile.age"), value: user.age ? String(user.age) : t("_profile.notFilled") },
  { label: t("_profile.college"), value: user.dept },
  { label: t("_profile.major"), value: user.major || t("_profile.notFilled") },
  { label: t("_profile.grade"), value: user.grade || t("_profile.notFilled") },
  { label: t("_profile.registeredTime"), value: user.registerTime },
]);
</script>

<template>
  <el-card shadow="never" :class="[ns.b(), 'tk-card-minimal']">
    <div :class="ns.e('head')">
      <slot>
        <el-image :src="user.avatar" :class="ns.m('avatar')" alt="头像">
          <template #error>
            <el-image :src="serviceConfig.layout.avatar" :class="ns.m('avatar')" alt="头像" />
          </template>
        </el-image>
      </slot>

      <p :class="ns.em('head', 'name')">{{ user.username }}</p>
      <p :class="ns.em('head', 'desc')">{{ user.signature }}</p>
    </div>

    <div :class="ns.e('info')">
      <ul class="flx-column gap-10">
        <li v-for="item in userInfo" :key="item.label" class="flx-align-center-between">
          <span>{{ item.label }}</span>
          <span>{{ item.value }}</span>
        </li>
      </ul>
    </div>
  </el-card>
</template>

<style lang="scss" scoped>
@use "./index";
</style>
