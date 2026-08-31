<script setup lang="ts" name="Register">
import type { FormInstance, FormRules } from "element-plus";
import { ref, reactive, inject, useTemplateRef } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { User, Phone, Lock, WarnTriangleFilled, CircleClose, UserFilled, School } from "@element-plus/icons-vue";
import { useNamespace } from "@/composables";
import { useVerifyCode } from "../use-verify-code";
import { t } from "@/common/languages";
import { UserService } from "@/common/api/user";

const ns = useNamespace("login-form");
const { isDisabled, text } = useVerifyCode();

const showPassword = ref(false);
const loading = ref(false);
const checked = ref(false);

const gradeOptions = ["2026", "2025", "2024", "2023", "2022", "2021", "2020"];
const collegeOptions = [
  t("_login.collegeAI"),
  t("_login.collegeCS"),
  t("_login.collegeSE"),
  t("_login.collegeDS"),
  t("_login.collegeMath"),
  t("_login.collegePhysics"),
];
const majorOptions = [
  t("_login.majorAI"),
  t("_login.majorCS"),
  t("_login.majorSE"),
  t("_login.majorDS"),
  t("_login.majorMath"),
  t("_login.majorPhysics"),
  t("_login.majorEE"),
];

const ruleForm = reactive({
  phone: "",
  verifyCode: "",
  password: "",
  repeatPassword: "",
  realName: "",
  studentId: "",
  sex: "",
  grade: "",
  college: "",
  major: "",
});

const validatePhone = (_: any, value: string, callback: (e?: Error) => void) => {
  if (!value) callback(new Error(t("_login.pleaseEnterPhone")));
  else if (!/^1[3-9]\d{9}$/.test(value)) callback(new Error(t("_login.pleaseEnterValidPhone")));
  else callback();
};

const validatePassword = (_: any, value: string, callback: (e?: Error) => void) => {
  if (!value) callback(new Error(t("_login.pleaseEnterPassword")));
  else if (value.length < 8) callback(new Error(t("_login.passwordMinLength")));
  else if (!/[a-zA-Z]/.test(value) || !/\d/.test(value))
    callback(new Error(t("_login.passwordMustContainLetterAndNumber")));
  else callback();
};

const validateRepeatPassword = (_: any, value: string, callback: (e?: Error) => void) => {
  if (!value) callback(new Error(t("_login.pleaseConfirmPassword")));
  else if (ruleForm.password !== value) callback(new Error(t("_login.passwordMismatch")));
  else callback();
};

const rules: FormRules = {
  phone: [{ required: true, validator: validatePhone, trigger: "blur" }],
  password: [{ required: true, validator: validatePassword, trigger: "blur" }],
  repeatPassword: [{ required: true, validator: validateRepeatPassword, trigger: "blur" }],
  realName: [{ required: true, message: t("_login.pleaseEnterRealName"), trigger: "blur" }],
  studentId: [{ required: true, message: t("_login.pleaseEnterStudentId"), trigger: "blur" }],
  sex: [{ required: true, message: t("_login.pleaseSelectSex"), trigger: "change" }],
  grade: [{ required: true, message: t("_login.pleaseSelectGrade"), trigger: "change" }],
  college: [{ required: true, message: t("_login.pleaseSelectCollege"), trigger: "change" }],
  major: [{ required: true, message: t("_login.pleaseSelectMajor"), trigger: "change" }],
};

const ruleFormRef = useTemplateRef<FormInstance>("ruleFormRef");

const register = async () => {
  if (!ruleFormRef.value) return;
  await ruleFormRef.value.validate(async valid => {
    if (!valid) return;
    if (!checked.value) {
      ElMessage.warning(t("_login.pleaseAcceptPrivacy"));
      return;
    }
    loading.value = true;
    try {
      await UserService.register({
        username: ruleForm.studentId,
        password: ruleForm.password,
        student_id: ruleForm.studentId,
        name: ruleForm.realName,
        sex: ruleForm.sex,
        dept: ruleForm.college,
        major: ruleForm.major,
        grade: ruleForm.grade,
        phone: ruleForm.phone,
      });
      ElMessage.success(t("_login.registerSuccess"));
      switchLoginMode("login");
    } finally {
      loading.value = false;
    }
  });
};

const switchLoginMode = inject("switchLoginMode") as (mode: string) => void;

const onBackToLogin = () => {
  useVerifyCode().end();
  switchLoginMode("login");
};

const showPrivacy = () => {
  ElMessageBox.alert(t("_login.privacyPolicyContent"), t("_login.privacyPolicy"), {
    confirmButtonText: t("_common.confirm"),
  });
};
</script>

<template>
  <el-form ref="ruleFormRef" :model="ruleForm" :rules="rules" size="default" :class="[ns.b(), 'register-form']">
    <el-form-item prop="phone">
      <el-input clearable v-model="ruleForm.phone" :placeholder="$t('_login.phoneNumber')" :prefix-icon="Phone" />
    </el-form-item>

    <el-form-item prop="verifyCode">
      <div style="display: flex; justify-content: space-between; width: 100%; gap: 12px">
        <el-input
          clearable
          v-model="ruleForm.verifyCode"
          :placeholder="$t('_login.smsVerifyCode')"
          :prefix-icon="WarnTriangleFilled"
        />
        <el-button :disabled="isDisabled" @click="useVerifyCode().start(ruleFormRef, 'phone')">
          {{ text.length > 0 ? text + $t("_common.secondsRetry") : $t("_common.getCode") }}
        </el-button>
      </div>
    </el-form-item>

    <el-form-item prop="password">
      <el-input
        clearable
        v-model="ruleForm.password"
        :placeholder="$t('_login.passwordHint')"
        :prefix-icon="Lock"
        :type="showPassword ? 'text' : 'password'"
      />
    </el-form-item>

    <el-form-item prop="repeatPassword">
      <el-input
        clearable
        v-model="ruleForm.repeatPassword"
        :placeholder="$t('_login.confirmPassword')"
        :prefix-icon="Lock"
        :type="showPassword ? 'text' : 'password'"
      />
    </el-form-item>

    <el-form-item>
      <el-checkbox v-model="showPassword">{{ $t("_login.showPassword") }}</el-checkbox>
    </el-form-item>

    <div class="form-row">
      <el-form-item prop="realName">
        <el-input clearable v-model="ruleForm.realName" :placeholder="$t('_login.realName')" :prefix-icon="User" />
      </el-form-item>
      <el-form-item prop="studentId">
        <el-input clearable v-model="ruleForm.studentId" :placeholder="$t('_login.studentId')" :prefix-icon="School" />
      </el-form-item>
    </div>

    <div class="form-row">
      <el-form-item prop="sex">
        <el-select v-model="ruleForm.sex" :placeholder="$t('_login.sex')">
          <el-option :label="$t('_login.sexMale')" value="男" />
          <el-option :label="$t('_login.sexFemale')" value="女" />
        </el-select>
      </el-form-item>
      <el-form-item prop="grade">
        <el-select v-model="ruleForm.grade" :placeholder="$t('_login.grade')">
          <el-option
            v-for="item in gradeOptions"
            :key="item"
            :label="$t('_login.gradeSuffix', { grade: item })"
            :value="$t('_login.gradeSuffix', { grade: item })"
          />
        </el-select>
      </el-form-item>
    </div>

    <el-form-item prop="college">
      <el-select v-model="ruleForm.college" :placeholder="$t('_login.college')" style="width: 100%">
        <el-option v-for="item in collegeOptions" :key="item" :label="item" :value="item" />
      </el-select>
    </el-form-item>

    <el-form-item prop="major">
      <el-select v-model="ruleForm.major" :placeholder="$t('_login.major')" style="width: 100%">
        <el-option v-for="item in majorOptions" :key="item" :label="item" :value="item" />
      </el-select>
    </el-form-item>

    <el-form-item>
      <el-checkbox v-model="checked">{{ $t("_login.acceptPrivacy") }}</el-checkbox>
      <el-button link type="primary" @click="showPrivacy">{{ $t("_login.privacyPolicy") }}</el-button>
    </el-form-item>

    <el-form-item>
      <div :class="ns.e('btn')" class="flx-align-center-between">
        <el-button :icon="CircleClose" round size="large" @click="onBackToLogin">
          {{ $t("_login.alreadyHaveAccount") }}
        </el-button>
        <el-button :icon="UserFilled" round @click="register" size="large" type="primary" :loading="loading">
          {{ $t("_login.register") }}
        </el-button>
      </div>
    </el-form-item>
  </el-form>
</template>

<style lang="scss" scoped>
@use "../loginForm";

.register-form {
  .form-row {
    display: flex;
    gap: 16px;

    :deep(.el-form-item) {
      flex: 1;
    }
  }

  :deep(.el-form-item) {
    margin-bottom: 18px;
  }
}
</style>
