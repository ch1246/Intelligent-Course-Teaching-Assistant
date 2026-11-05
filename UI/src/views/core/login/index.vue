<script setup lang="ts" name="Login">
import type { Component } from "vue";
import { ref, provide } from "vue";
import { serviceConfig } from "@/common/config";
import { SwitchDark } from "@/components";
import { useNamespace } from "@/composables";
import LoginForm from "./loginForm.vue";
import Register from "./components/register.vue";

const ns = useNamespace("login");

// 登录方式只保留「账号密码」与「注册」。
// 原先还有 phone（手机登录，后端无此接口）、forget（忘记密码，前端收手机号而后端
// 要 email，永远打不通）、qrCode（模拟登录，无任何切换入口）三种，均为接不上
// 后端的模板演示，已删除，免得用户以为存在实际能力。
const formComponents: Record<string, Component> = {
  login: LoginForm,
  register: Register,
};

const formMode = ref("login");

const switchLoginMode = (mode: string) => {
  formMode.value = mode;
};

provide("switchLoginMode", switchLoginMode);
</script>

<template>
  <div :class="ns.b()">
    <SwitchDark :class="ns.e('dark')" />
    <div :class="ns.e('wrapper')">
      <div :class="ns.e('left')">
        <img
          src="@/common/assets/images/login/login_left.png"
          alt="login"
          width="900"
          height="600"
          style="width: 100%; height: auto"
        />
      </div>

      <div :class="ns.e('right')">
        <div :class="ns.e('right__header')" class="flx-center">
          <img :src="serviceConfig.logo.source" alt="" width="60" height="53" style="width: 60px; height: auto" />
          <h2 class="title">{{ serviceConfig.layout.name }}</h2>
        </div>

        <component :is="formComponents[formMode]" />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "./index";
</style>
