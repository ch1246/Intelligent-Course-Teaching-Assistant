<script setup lang="ts" name="LoginForm">
import type { FormInstance } from "element-plus";
import { ref, reactive, inject, useTemplateRef } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElNotification } from "element-plus";
import { User, Lock, WarnTriangleFilled, CircleClose, UserFilled } from "@element-plus/icons-vue";
import { serviceConfig, HOME_URL } from "@/common/config";
import { getTimeState } from "@/common/utils";
import { ImageVerifyCode } from "@/components";
import { useNamespace } from "@/composables";
import { useUserStore } from "@/pinia";
import { t } from "@/common/languages";

interface LoginForm {
  username: string;
  password: string;
  verifyCode: string;
}

const ns = useNamespace("login-form");

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const switchLoginMode = inject("switchLoginMode") as (mode: string) => void;

const loginRules = {
  username: [{ required: true, message: t("_login.pleaseEnterStudentId"), trigger: "blur" }],
  password: [{ required: true, message: t("_login.pleaseEnterPassword"), trigger: "blur" }],
  verifyCode: [
    {
      validator: (_: any, value: string, callback: (e?: Error) => void) => {
        if (value === "") {
          callback(new Error(t("_login.pleaseEnterVerifyCode")));
        } else if (imgCode.value !== value) {
          callback(new Error(t("_login.pleaseEnterCorrectVerifyCode")));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};

const loginFormRef = useTemplateRef<FormInstance>("loginFormRef");

const imgCode = ref("");
const loading = ref(false);
const loginForm = reactive<LoginForm>({ username: "", password: "", verifyCode: "" });
const checked = ref(false);

const handleForgetPwd = () => {
  switchLoginMode("forget");
};

const login = () => {
  loginFormRef.value?.validate(async valid => {
    if (!valid) return;
    loading.value = true;
    try {
      // 执行登录
      const result = await userStore.login({ ...loginForm });
      if (!result) {
        ElNotification({
          title: getTimeState(),
          message: t("_login.loginFailed"),
          type: "success",
          duration: 3000,
        });
        return;
      }

      // 跳转到首页或者 URL 携带的 redirect 页（优先级高）
      let path = HOME_URL;
      const { query } = route;

      if (query.redirect) path = query.redirect as string;

      const otherQuery = getOtherQuery(query);
      // otherQuery 不能是 {}，否则无法跳转
      if (Object.keys(otherQuery).length === 0) router.push(path);
      else router.push({ path, query: otherQuery });

      ElNotification.success({
        title: t("_login.welcomeLogin", { name: serviceConfig.layout.name }),
        message: getTimeState(),
        duration: 3000,
      });
    } finally {
      loading.value = false;
    }
  });
};

const getOtherQuery = (query: any) => {
  return Object.keys(query).reduce((acc: any, cur) => {
    if (cur !== "redirect") acc[cur] = query[cur];
    return acc;
  }, {});
};

const resetForm = () => {
  loginFormRef.value?.resetFields();
};
</script>

<template>
  <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" size="large" :class="ns.b()">
    <el-form-item prop="username">
      <el-input
        v-model="loginForm.username"
        :placeholder="$t('_login.studentId')"
        :prefix-icon="User"
        @keydown.enter="login"
      ></el-input>
    </el-form-item>

    <el-form-item prop="password">
      <el-input
        type="password"
        v-model="loginForm.password"
        :placeholder="$t('_login.password')"
        show-password
        autocomplete="new-password"
        :prefix-icon="Lock"
        @keydown.enter="login"
      ></el-input>
    </el-form-item>

    <el-form-item prop="verifyCode">
      <el-input
        clearable
        v-model="loginForm.verifyCode"
        :placeholder="$t('_login.verifyCode')"
        :prefix-icon="WarnTriangleFilled"
        @keydown.enter="login"
      >
        <template #append>
          <ImageVerifyCode v-model="imgCode" />
        </template>
      </el-input>
    </el-form-item>

    <el-form-item>
      <div :class="ns.e('item')" class="flx-align-center-between">
        <el-checkbox v-model="checked">{{ $t("_login.rememberPassword") }}</el-checkbox>
        <el-button link type="primary" @click="handleForgetPwd">{{ $t("_login.forgotPassword") }}</el-button>
      </div>
    </el-form-item>

    <el-form-item>
      <div :class="ns.e('btn')" class="flx-align-center-between">
        <el-button :icon="CircleClose" round @click="resetForm()" size="large">
          {{ $t("_login.resetButton") }}
        </el-button>
        <el-button :icon="UserFilled" round @click="login()" size="large" type="primary" :loading="loading">
          {{ $t("_login.loginButton") }}
        </el-button>
      </div>
    </el-form-item>

    <el-form-item>
      <div :class="ns.e('btn')" class="flx-align-center-between">
        <el-button @click="switchLoginMode('phone')" size="large">{{ $t("_login.phoneLogin") }}</el-button>
        <el-button @click="switchLoginMode('register')" size="large" type="primary" plain>
          {{ $t("_login.registerAccount") }}
        </el-button>
      </div>
    </el-form-item>
  </el-form>
</template>

<style lang="scss" scoped>
@use "./loginForm";
</style>
