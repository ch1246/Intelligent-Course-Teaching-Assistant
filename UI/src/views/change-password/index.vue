<script setup lang="ts">
import type { FormInstance } from "element-plus";
import { ref, reactive, useTemplateRef, computed } from "vue";
import { ElMessage } from "element-plus";
import { Lock } from "@element-plus/icons-vue";
import { t } from "@/common/languages";
import { http } from "@/common/http";

defineOptions({ name: "ChangePassword" });

const passwordFormRef = useTemplateRef<FormInstance>("passwordFormRef");
const passwordLoading = ref(false);
const passwordForm = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const passwordStrength = computed(() => {
  const val = passwordForm.newPassword;
  if (!val) return { level: 0, text: "", color: "" };
  let score = 0;
  if (val.length >= 8) score++;
  if (val.length >= 12) score++;
  if (/[a-z]/.test(val) && /[A-Z]/.test(val)) score++;
  if (/\d/.test(val)) score++;
  if (/[^a-zA-Z0-9]/.test(val)) score++;

  if (score <= 2) return { level: 1, text: t("_settings.passwordStrengthWeak"), color: "var(--tk-color-warning)" };
  if (score <= 3) return { level: 2, text: t("_settings.passwordStrengthMedium"), color: "#d97706" };
  return { level: 3, text: t("_settings.passwordStrengthStrong"), color: "var(--tk-color-success)" };
});

const validateNewPassword = (_: any, value: string, callback: (e?: Error) => void) => {
  if (!value) callback(new Error(t("_settings.passwordRequired")));
  else if (value.length < 8) callback(new Error(t("_settings.passwordMinLength")));
  else if (!/[a-zA-Z]/.test(value) || !/\d/.test(value))
    callback(new Error(t("_settings.passwordMustContainLettersAndNumbers")));
  else callback();
};

const validateConfirmPassword = (_: any, value: string, callback: (e?: Error) => void) => {
  if (!value) callback(new Error(t("_settings.passwordConfirmRequired")));
  else if (passwordForm.newPassword !== value) callback(new Error(t("_settings.passwordMismatch")));
  else callback();
};

const passwordRules = {
  oldPassword: [{ required: true, message: t("_settings.currentPasswordRequired"), trigger: "blur" }],
  newPassword: [{ validator: validateNewPassword, trigger: "blur" }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: "blur" }],
};

const changePassword = async () => {
  if (!passwordFormRef.value) return;
  await passwordFormRef.value.validate(async valid => {
    if (!valid) return;
    passwordLoading.value = true;
    try {
      await http.post("/auth/change-password", {
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword,
      });
      ElMessage.success(t("_settings.passwordChanged"));
      passwordForm.oldPassword = "";
      passwordForm.newPassword = "";
      passwordForm.confirmPassword = "";
    } catch {
      ElMessage.error(t("_settings.passwordChangeFailed"));
    } finally {
      passwordLoading.value = false;
    }
  });
};
</script>

<template>
  <div class="change-password-page">
    <h2 class="page-title">{{ $t("_settings.changePassword") }}</h2>
    <div class="form-card">
      <!-- Lock icon -->
      <div class="lock-icon-wrapper">
        <div class="lock-icon-circle">
          <el-icon :size="28"><Lock /></el-icon>
        </div>
      </div>

      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
        style="max-width: 480px; margin: 0 auto"
      >
        <el-form-item :label="$t('_settings.currentPassword')" prop="oldPassword">
          <el-input
            v-model="passwordForm.oldPassword"
            type="password"
            show-password
            :placeholder="$t('_settings.pleaseEnterCurrentPassword')"
            :prefix-icon="Lock"
          />
        </el-form-item>
        <el-form-item :label="$t('_settings.newPassword')" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            show-password
            :placeholder="$t('_settings.newPasswordHint')"
            :prefix-icon="Lock"
          />
          <!-- Password strength indicator -->
          <div v-if="passwordForm.newPassword" class="password-strength">
            <div class="strength-bars">
              <span
                v-for="i in 3"
                :key="i"
                class="strength-bar"
                :class="{ active: i <= passwordStrength.level }"
                :style="{ background: i <= passwordStrength.level ? passwordStrength.color : '' }"
              ></span>
            </div>
            <span class="strength-text" :style="{ color: passwordStrength.color }">
              {{ passwordStrength.text }}
            </span>
          </div>
        </el-form-item>
        <el-form-item :label="$t('_settings.confirmNewPassword')" prop="confirmPassword">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            show-password
            :placeholder="$t('_settings.pleaseConfirmNewPassword')"
            :prefix-icon="Lock"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="passwordLoading" @click="changePassword">
            {{ $t("_settings.confirmModify") }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- Security tips -->
      <div class="security-tips">
        <p class="tips-title">{{ $t("_settings.passwordTipsTitle") }}</p>
        <ul class="tips-list">
          <li>{{ $t("_settings.passwordTipLength") }}</li>
          <li>{{ $t("_settings.passwordTipChars") }}</li>
          <li>{{ $t("_settings.passwordTipUnique") }}</li>
          <li>{{ $t("_settings.passwordTipChange") }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.change-password-page {
  padding: 4px 0;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 24px;
}

.form-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 32px 24px;
  box-shadow: var(--tk-box-shadow-sm);
}

// Lock icon
.lock-icon-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 28px;
}

.lock-icon-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);
}

// Password strength
.password-strength {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.strength-bars {
  display: flex;
  gap: 4px;
}

.strength-bar {
  width: 40px;
  height: 4px;
  border-radius: 2px;
  background: var(--tk-gray-color-200);
  transition: background 0.3s ease;

  &.active {
    background: var(--tk-color-warning);
  }
}

.strength-text {
  font-size: 12px;
  color: var(--tk-gray-color-500);
}

// Security tips
.security-tips {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--tk-surface-border-color);
}

.tips-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--tk-gray-color-900);
  margin: 0 0 12px;
}

.tips-list {
  margin: 0;
  padding: 0;
  list-style: none;

  li {
    position: relative;
    padding: 6px 0 6px 18px;
    font-size: 13px;
    color: var(--tk-gray-color-500);
    line-height: 1.6;

    &::before {
      content: "";
      position: absolute;
      left: 0;
      top: 12px;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    }
  }
}
</style>
