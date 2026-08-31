<script setup lang="ts" name="Forget">
import type { FormInstance } from "element-plus";
import { ref, reactive, inject, useTemplateRef } from "vue";
import { ElMessage } from "element-plus";
import { Phone, Lock, WarnTriangleFilled } from "@element-plus/icons-vue";
import { useNamespace } from "@/composables";
import { useVerifyCode } from "../use-verify-code";
import { updateRules } from "../rules";
import { t } from "@/common/languages";

const ns = useNamespace("login-form");
const { isDisabled, text } = useVerifyCode();

const loading = ref(false);
const ruleForm = reactive({
  phone: "",
  verifyCode: "",
  password: "",
  repeatPassword: "",
});

const ruleFormRef = useTemplateRef<FormInstance>("ruleFormRef");

const repeatPasswordRule = [
  {
    validator: (_: any, value: string, callback: (error?: string | Error | undefined) => void) => {
      if (value === "") {
        callback(new Error(t("_login.pleaseEnterConfirmPassword")));
      } else if (ruleForm.password !== value) {
        callback(new Error(t("_login.passwordMismatch")));
      } else {
        callback();
      }
    },
    trigger: "blur",
  },
];

const login = async () => {
  loading.value = true;

  if (!ruleFormRef.value) return;

  await ruleFormRef.value.validate((valid, fields) => {
    if (valid) {
      // 模拟请求，需根据实际开发进行修改
      setTimeout(() => {
        ElMessage.success(t("_login.changePasswordSuccess"));
        loading.value = false;
      }, 2000);
    } else {
      loading.value = false;
      Promise.resolve(fields);
    }
  });
};

const switchLoginMode = inject("switchLoginMode") as (mode: string) => void;

const onBack = () => {
  useVerifyCode().end();
  switchLoginMode("login");
};
</script>

<template>
  <el-form ref="ruleFormRef" :model="ruleForm" :rules="updateRules" size="large" :class="ns.b()">
    <el-form-item prop="phone">
      <el-input clearable v-model="ruleForm.phone" :placeholder="$t('_login.phoneNumber')" :prefix-icon="Phone" />
    </el-form-item>

    <el-form-item prop="verifyCode">
      <div style="display: flex; justify-content: space-between; width: 100%">
        <el-input
          clearable
          v-model="ruleForm.verifyCode"
          :placeholder="$t('_login.smsVerifyCode')"
          :prefix-icon="WarnTriangleFilled"
          @keydown.enter="login"
        />
        <el-button :disabled="isDisabled" class="ml-2" @click="useVerifyCode().start(ruleFormRef, 'phone')">
          {{ text.length > 0 ? text + $t("_common.secondsRetry") : $t("_common.getCode") }}
        </el-button>
      </div>
    </el-form-item>

    <el-form-item prop="password">
      <el-input
        clearable
        show-password
        v-model="ruleForm.password"
        :placeholder="$t('_login.newPassword')"
        :prefix-icon="Lock"
        @keydown.enter="login"
      />
    </el-form-item>

    <el-form-item :rules="repeatPasswordRule" prop="repeatPassword">
      <el-input
        clearable
        show-password
        v-model="ruleForm.repeatPassword"
        :placeholder="$t('_login.confirmPassword')"
        :prefix-icon="Lock"
        @keydown.enter="login"
      />
    </el-form-item>

    <el-form-item>
      <div :class="ns.e('btn')" class="flx-align-center-between">
        <el-button icon="CircleClose" round size="large" @click="onBack">{{ $t("_login.backToLogin") }}</el-button>
        <el-button icon="UserFilled" round size="large" type="primary" :loading="loading" @click="login">
          {{ $t("_login.loginButton") }}
        </el-button>
      </div>
    </el-form-item>
  </el-form>
</template>

<style lang="scss" scoped>
@use "../loginForm";

:deep(.el-button) {
  width: 140px;
}
</style>
