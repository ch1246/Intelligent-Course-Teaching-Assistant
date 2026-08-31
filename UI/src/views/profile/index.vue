<script setup lang="ts">
import type { FormInstance } from "element-plus";
import { ref, reactive, useTemplateRef, computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { ElMessage, ElMessageBox } from "element-plus";
import { useUserStore } from "@/pinia";
import { t } from "@/common/languages";
import { http } from "@/common/http";
import { Message, Iphone, ChatLineSquare, Edit, Lock, Clock } from "@element-plus/icons-vue";
import UserInfoCard from "./components/user-info/index.vue";
import UserAvatar from "./components/user-avatar/index.vue";

defineOptions({ name: "Profile" });

const userStore = useUserStore();
const { userInfo } = storeToRefs(userStore);
const activeTab = ref("oplog");

const profileStats = ref<{ label: string; value: any; icon: string }[]>([
  { label: t("_home.statCourses"), value: "-", icon: "ep:school" },
  { label: t("_profile.systemUsers"), value: "-", icon: "ep:user" },
  { label: t("_home.statMessages"), value: "-", icon: "ep:chat-dot-round" },
]);

async function loadProfileStats() {
  try {
    const res = await http.get<httpNs.Response<any>>("/admin/dashboard");
    const d = res.data || {};
    if (userRole.value === "admin" || userRole.value === "teacher") {
      profileStats.value = [
        { label: t("_home.statCourses"), value: d.active_course_count ?? d.course_count ?? 0, icon: "ep:school" },
        { label: t("_profile.systemUsers"), value: d.student_count ?? 0, icon: "ep:user" },
        { label: t("_home.statMessages"), value: d.total_messages ?? 0, icon: "ep:chat-dot-round" },
      ];
    } else {
      profileStats.value = [
        { label: t("_profile.enrolledCourses"), value: d.course_count ?? 0, icon: "ep:collection" },
        { label: t("_profile.learningHours"), value: "0h", icon: "ep:timer" },
        { label: t("_home.statMessages"), value: d.total_messages ?? 0, icon: "ep:document" },
      ];
    }
  } catch {
    /* keep empty */
  }
}

onMounted(loadProfileStats);

const userRole = computed(() => {
  const roles = userInfo.value.roles || [];
  if (roles.includes("admin")) return "admin";
  if (roles.includes("teacher")) return "teacher";
  return "student";
});

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    admin: t("_profile.admin"),
    teacher: t("_profile.teacher"),
    student: t("_profile.student"),
  };
  return map[userRole.value] || t("_profile.user");
});

// Messages
interface UserMessage {
  id: number;
  title: string;
  content: string;
  type: "system" | "course" | "review";
  read: boolean;
  time: string;
}

const messages = ref<UserMessage[]>([
  {
    id: 1,
    title: t("_profile.messageSystemTitle"),
    content: t("_profile.messageSystemWelcome"),
    type: "system",
    read: true,
    time: "2026-07-15 09:00",
  },
  {
    id: 2,
    title: t("_profile.messageCourseTitle"),
    content: t("_profile.messageCourseStart"),
    type: "course",
    read: false,
    time: "2026-07-14 18:30",
  },
  {
    id: 3,
    title: t("_profile.messageReviewTitle"),
    content: t("_profile.messageReviewApproved"),
    type: "review",
    read: false,
    time: "2026-07-14 15:20",
  },
  {
    id: 4,
    title: t("_profile.messageSystemTitle"),
    content: t("_profile.messageSystemMaintenance"),
    type: "system",
    read: true,
    time: "2026-07-13 10:00",
  },
  {
    id: 5,
    title: t("_profile.messageCourseTitle"),
    content: t("_profile.messageCourseDeadline"),
    type: "course",
    read: true,
    time: "2026-07-12 14:00",
  },
  {
    id: 6,
    title: t("_profile.messageReviewTitle"),
    content: t("_profile.messageReviewRejected"),
    type: "review",
    read: false,
    time: "2026-07-11 09:45",
  },
]);

const unreadCount = computed(() => messages.value.filter(m => !m.read).length);

const getMsgTypeIcon = (type: string) => {
  const map: Record<string, string> = { system: "ep:bell", course: "ep:notebook", review: "ep:circle-check" };
  return map[type] || "ep:bell";
};

const getMsgTypeColor = (type: string) => {
  const map: Record<string, string> = {
    system: "var(--tk-color-primary)",
    course: "var(--tk-color-success)",
    review: "var(--tk-color-warning)",
  };
  return map[type] || "var(--tk-gray-color-500)";
};

const markAllRead = () => {
  messages.value.forEach(m => (m.read = true));
  ElMessage.success(t("_profile.markAllReadSuccess"));
};

// Operation Log
interface OpLog {
  id: number;
  type:
    | "login"
    | "logout"
    | "passwordReset"
    | "passwordChange"
    | "profileUpdate"
    | "emailBind"
    | "phoneBind"
    | "wechatBind";
  ip: string;
  browser: string;
  time: string;
}

const opLogs = ref<OpLog[]>([
  { id: 1, type: "login", ip: "192.168.1.105", browser: "Chrome 125", time: "2026-07-16 08:30:22" },
  { id: 2, type: "profileUpdate", ip: "192.168.1.105", browser: "Chrome 125", time: "2026-07-15 14:22:10" },
  { id: 3, type: "logout", ip: "192.168.1.105", browser: "Chrome 125", time: "2026-07-15 14:20:05" },
  { id: 4, type: "login", ip: "192.168.1.105", browser: "Chrome 125", time: "2026-07-15 09:15:48" },
  { id: 5, type: "passwordChange", ip: "192.168.1.105", browser: "Chrome 125", time: "2026-07-14 16:05:33" },
  { id: 6, type: "emailBind", ip: "10.0.0.88", browser: "Firefox 126", time: "2026-07-13 11:45:12" },
  { id: 7, type: "login", ip: "10.0.0.88", browser: "Firefox 126", time: "2026-07-13 11:42:00" },
  { id: 8, type: "login", ip: "192.168.1.105", browser: "Chrome 124", time: "2026-07-12 08:10:55" },
  { id: 9, type: "phoneBind", ip: "192.168.1.105", browser: "Chrome 124", time: "2026-07-11 15:30:18" },
  { id: 10, type: "login", ip: "172.16.0.50", browser: "Edge 124", time: "2026-07-10 09:00:42" },
  { id: 11, type: "wechatBind", ip: "172.16.0.50", browser: "Edge 124", time: "2026-07-09 17:20:30" },
  { id: 12, type: "passwordReset", ip: "172.16.0.50", browser: "Edge 124", time: "2026-07-08 20:45:11" },
]);

const getOpTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    login: t("_profile.opLogin"),
    logout: t("_profile.opLogout"),
    passwordReset: t("_profile.opPasswordReset"),
    passwordChange: t("_profile.opPasswordChange"),
    profileUpdate: t("_profile.opProfileUpdate"),
    emailBind: t("_profile.opEmailBind"),
    phoneBind: t("_profile.opPhoneBind"),
    wechatBind: t("_profile.opWechatBind"),
  };
  return map[type] || type;
};

const getOpTypeDesc = (type: string) => {
  const map: Record<string, string> = {
    login: t("_profile.opLoginDesc"),
    logout: t("_profile.opLogoutDesc"),
    passwordReset: t("_profile.opPasswordResetDesc"),
    passwordChange: t("_profile.opPasswordChangeDesc"),
    profileUpdate: t("_profile.opProfileUpdateDesc"),
    emailBind: t("_profile.opEmailBindDesc"),
    phoneBind: t("_profile.opPhoneBindDesc"),
    wechatBind: t("_profile.opWechatBindDesc"),
  };
  return map[type] || "";
};

const getOpTypeColor = (type: string) => {
  const map: Record<string, string> = {
    login: "var(--tk-color-primary)",
    logout: "var(--tk-gray-color-400)",
    passwordReset: "var(--tk-color-warning)",
    passwordChange: "var(--tk-color-warning)",
    profileUpdate: "var(--tk-color-success)",
    emailBind: "var(--tk-color-info)",
    phoneBind: "var(--tk-color-info)",
    wechatBind: "var(--tk-color-success)",
  };
  return map[type] || "var(--tk-gray-color-500)";
};

// Profile edit
const profileFormRef = useTemplateRef<FormInstance>("profileFormRef");
const profileEditing = ref(false);
const profileForm = reactive({
  username: userInfo.value.username || "",
  signature: userInfo.value.signature || "",
  phone: userInfo.value.phone || "",
  email: userInfo.value.email || "",
  major: userInfo.value.major || "",
  grade: userInfo.value.grade || "",
  dept: userInfo.value.dept || "",
  sex: userInfo.value.sex || "男",
  age: userInfo.value.age || 0,
});

const saveProfile = async () => {
  if (!profileFormRef.value) return;
  await profileFormRef.value.validate(async valid => {
    if (!valid) return;
    try {
      await http.put("/profile/", profileForm);
      userStore.setUserInfo({ ...userInfo.value, ...profileForm });
      ElMessage.success(t("_profile.profileUpdated"));
      profileEditing.value = false;
    } catch {
      ElMessage.error(t("_profile.saveFailed"));
    }
  });
};

const cancelEdit = () => {
  // username is immutable
  profileForm.signature = userInfo.value.signature || "";
  profileForm.phone = userInfo.value.phone || "";
  profileForm.email = userInfo.value.email || "";

  profileEditing.value = false;
  profileFormRef.value?.clearValidate();
};

// Bind dialogs
const emailDialogVisible = ref(false);
const phoneDialogVisible = ref(false);
const wechatDialogVisible = ref(false);

const newEmail = ref("");
const newPhone = ref("");
const verifyCode = ref("");
const isWechatBound = ref(false);

const sendVerifyCode = async (target: string) => {
  ElMessage.success(t("_profile.codeSent", { target }));
};

const bindEmail = async () => {
  if (!newEmail.value) {
    ElMessage.warning(t("_profile.emailRequired"));
    return;
  }
  ElMessage.success(t("_profile.emailBound", { email: newEmail.value }));
  userStore.setUserInfo({ ...userInfo.value, email: newEmail.value });
  emailDialogVisible.value = false;
  newEmail.value = "";
};

const bindPhone = async () => {
  if (!newPhone.value) {
    ElMessage.warning(t("_profile.invalidPhone"));
    return;
  }
  ElMessage.success(t("_profile.phoneBound", { phone: newPhone.value }));
  userStore.setUserInfo({ ...userInfo.value, phone: newPhone.value });
  phoneDialogVisible.value = false;
  newPhone.value = "";
};

const toggleWechat = async () => {
  if (isWechatBound.value) {
    await ElMessageBox.confirm(t("_profile.confirmUnbindWechat"), t("_common.tip"), { type: "warning" });
    isWechatBound.value = false;
    ElMessage.success(t("_profile.wechatUnbound"));
  } else {
    wechatDialogVisible.value = true;
  }
};

const confirmWechatBind = () => {
  isWechatBound.value = true;
  wechatDialogVisible.value = false;
  ElMessage.success(t("_profile.wechatBoundSuccess"));
};

const profileRules = {
  phone: [
    { required: true, message: t("_profile.contactRequired"), trigger: "blur" },
    { pattern: /^1[3-9]\d{9}$/, message: t("_profile.invalidPhone"), trigger: "blur" },
  ],
  email: [
    { required: true, message: t("_profile.emailRequired"), trigger: "blur" },
    { type: "email", message: t("_profile.invalidEmail"), trigger: "blur" },
  ],
};
</script>

<template>
  <div class="profile-page">
    <!-- Hero -->
    <div class="profile-hero">
      <div class="hero-left">
        <UserAvatar :user="userInfo" class="hero-avatar" />
        <div class="hero-info">
          <h2 class="hero-username">{{ userInfo.username }}</h2>
          <p class="hero-signature">{{ userInfo.signature || $t("_profile.lazySignature") }}</p>
          <div class="hero-tags">
            <el-tag size="small" class="hero-tag">
              {{ roleLabel }}
            </el-tag>
            <el-tag v-if="userInfo.dept" size="small" class="hero-tag">{{ userInfo.dept }}</el-tag>
            <el-tag v-if="userInfo.major" size="small" class="hero-tag">{{ userInfo.major }}</el-tag>
            <el-tag v-if="userInfo.grade" size="small" class="hero-tag">{{ userInfo.grade }}</el-tag>
          </div>
        </div>
      </div>
      <div class="hero-right">
        <span class="register-time">{{ $t("_profile.registeredTime") }}{{ userInfo.registerTime }}</span>
        <div class="hero-stats">
          <div v-for="stat in profileStats" :key="stat.label" class="hero-stat-item">
            <Icon :icon="stat.icon" :size="18" />
            <div class="hero-stat-info">
              <span class="hero-stat-value">{{ stat.value }}</span>
              <span class="hero-stat-label">{{ stat.label }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-row :gutter="24" style="margin-top: 24px">
      <!-- Left: Tabs -->
      <el-col :xl="16" :lg="15" :xs="24">
        <div class="content-card">
          <el-tabs v-model="activeTab">
            <el-tab-pane :label="$t('_profile.editProfile')" name="profile">
              <div class="avatar-upload-row">
                <UserAvatar :user="userInfo" />
                <span class="avatar-upload-hint">{{ $t("_profile.clickUploadAvatar") }}</span>
              </div>

              <el-form
                ref="profileFormRef"
                :model="profileForm"
                :rules="profileRules"
                label-width="90px"
                :disabled="!profileEditing"
                style="max-width: 560px"
              >
                <el-form-item :label="$t('_profile.username')" prop="username">
                  <el-input :model-value="userInfo.username" disabled />
                </el-form-item>

                <el-form-item :label="$t('_profile.signature')">
                  <el-input
                    v-model="profileForm.signature"
                    maxlength="100"
                    :placeholder="$t('_profile.signaturePlaceholder')"
                  />
                </el-form-item>

                <el-form-item :label="$t('_profile.contact')" prop="phone">
                  <el-input v-model="profileForm.phone" maxlength="11" :disabled="!profileEditing" />
                </el-form-item>

                <el-form-item :label="$t('_profile.email')" prop="email">
                  <el-input v-model="profileForm.email" maxlength="50" :disabled="!profileEditing" />
                </el-form-item>

                <el-divider content-position="left" style="font-size: 13px; color: var(--tk-gray-color-500)">
                  {{ $t("_profile.immutableInfo") }}
                </el-divider>

                <el-form-item :label="$t('_profile.college')">
                  <el-input :model-value="userInfo.dept" disabled />
                </el-form-item>

                <el-form-item :label="$t('_profile.major')">
                  <el-input :model-value="userInfo.major || $t('_profile.notFilled')" disabled />
                </el-form-item>

                <el-form-item :label="$t('_profile.grade')">
                  <el-input :model-value="userInfo.grade || $t('_profile.notFilled')" disabled />
                </el-form-item>

                <el-form-item :label="$t('_profile.gender')">
                  <el-input :model-value="userInfo.sex || $t('_profile.notFilled')" disabled />
                </el-form-item>
              </el-form>

              <div style="margin-top: 16px">
                <el-button v-if="!profileEditing" type="primary" :icon="Edit" @click="profileEditing = true">
                  {{ $t("_profile.editProfileInfo") }}
                </el-button>
                <template v-else>
                  <el-button type="primary" @click="saveProfile">{{ $t("_profile.save") }}</el-button>
                  <el-button @click="cancelEdit">{{ $t("_common.cancel") }}</el-button>
                </template>
              </div>
            </el-tab-pane>

            <el-tab-pane :label="$t('_profile.accountSecurity')" name="security">
              <div class="security-list">
                <div class="security-item">
                  <div class="security-left">
                    <el-icon :size="20"><Lock /></el-icon>
                    <div>
                      <div class="security-title">{{ $t("_profile.changePassword") }}</div>
                      <div class="security-desc">{{ $t("_profile.changePasswordTip") }}</div>
                    </div>
                  </div>
                  <el-button text type="primary" @click="$router.push('/change-password')">
                    {{ $t("_profile.modifyPassword") }}
                  </el-button>
                </div>

                <div class="security-item">
                  <div class="security-left">
                    <el-icon :size="20"><Message /></el-icon>
                    <div>
                      <div class="security-title">{{ $t("_profile.bindEmail") }}</div>
                      <div class="security-desc">
                        {{ userInfo.email || $t("_profile.emailNotBound") }}
                      </div>
                    </div>
                  </div>
                  <el-button text type="primary" @click="emailDialogVisible = true">
                    {{ $t("_common.changeBind") }}
                  </el-button>
                </div>

                <div class="security-item">
                  <div class="security-left">
                    <el-icon :size="20"><Iphone /></el-icon>
                    <div>
                      <div class="security-title">{{ $t("_profile.bindPhone") }}</div>
                      <div class="security-desc">
                        {{ userInfo.phone || $t("_profile.phoneNotBound") }}
                      </div>
                    </div>
                  </div>
                  <el-button text type="primary" @click="phoneDialogVisible = true">
                    {{ $t("_common.changeBind") }}
                  </el-button>
                </div>

                <div class="security-item">
                  <div class="security-left">
                    <el-icon :size="20"><ChatLineSquare /></el-icon>
                    <div>
                      <div class="security-title">{{ $t("_profile.bindWechat") }}</div>
                      <div class="security-desc">
                        {{ isWechatBound ? $t("_profile.wechatBound") : $t("_profile.wechatNotBound") }}
                      </div>
                    </div>
                  </div>
                  <el-button text :type="isWechatBound ? 'danger' : 'primary'" @click="toggleWechat">
                    {{ isWechatBound ? $t("_profile.unbind") : $t("_profile.bind") }}
                  </el-button>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane name="messages">
              <template #label>
                <span class="tab-label-with-badge">
                  {{ $t("_profile.myMessages") }}
                  <el-badge v-if="unreadCount" :value="unreadCount" :max="99" class="msg-badge" />
                </span>
              </template>
              <div class="messages-header">
                <span class="msg-count">{{ $t("_profile.totalMessages", { count: messages.length }) }}</span>
                <el-button text type="primary" size="small" @click="markAllRead">
                  {{ $t("_profile.markAllRead") }}
                </el-button>
              </div>
              <div class="messages-list">
                <div v-for="msg in messages" :key="msg.id" class="msg-item" :class="{ 'msg-unread': !msg.read }">
                  <div class="msg-icon" :style="{ color: getMsgTypeColor(msg.type) }">
                    <Icon :icon="getMsgTypeIcon(msg.type)" :size="20" />
                  </div>
                  <div class="msg-body">
                    <div class="msg-header">
                      <span class="msg-title">{{ msg.title }}</span>
                      <span class="msg-time">{{ msg.time }}</span>
                    </div>
                    <p class="msg-content">{{ msg.content }}</p>
                  </div>
                  <el-tag v-if="!msg.read" size="small" type="danger" effect="light" class="msg-dot">
                    {{ $t("_profile.newMessage") }}
                  </el-tag>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane :label="$t('_profile.operationLog')" name="oplog">
              <div class="oplog-list">
                <div v-for="log in opLogs" :key="log.id" class="oplog-item">
                  <div class="oplog-dot" :style="{ '--dot-color': getOpTypeColor(log.type) }">
                    <el-icon :size="14"><Clock /></el-icon>
                  </div>
                  <div class="oplog-body">
                    <div class="oplog-header">
                      <span class="oplog-title">{{ getOpTypeLabel(log.type) }}</span>
                      <span class="oplog-time">{{ log.time }}</span>
                    </div>
                    <p class="oplog-desc">{{ getOpTypeDesc(log.type) }}</p>
                    <div class="oplog-meta">
                      <span>{{ $t("_profile.opIp") }}: {{ log.ip }}</span>
                      <span>{{ $t("_profile.opBrowser") }}: {{ log.browser }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-col>

      <!-- Right -->
      <el-col :xl="8" :lg="9" :xs="24">
        <div class="side-card">
          <UserInfoCard :user="userInfo" />
        </div>
      </el-col>
    </el-row>

    <!-- Email Dialog -->
    <el-dialog
      v-model="emailDialogVisible"
      :title="$t('_profile.changeBindEmail')"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px">
        <el-form-item :label="$t('_profile.currentEmail')">
          <el-input :model-value="userInfo.email" disabled />
        </el-form-item>
        <el-form-item :label="$t('_profile.newEmail')">
          <el-input v-model="newEmail" :placeholder="$t('_profile.pleaseEnterNewEmail')" />
        </el-form-item>
        <el-form-item :label="$t('_common.verifyCode')">
          <div class="verify-row">
            <el-input v-model="verifyCode" :placeholder="$t('_common.enterVerifyCode')" />
            <el-button type="primary" text @click="sendVerifyCode($t('_common.email'))">
              {{ $t("_common.sendCode") }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="emailDialogVisible = false">{{ $t("_common.cancel") }}</el-button>
        <el-button type="primary" @click="bindEmail">{{ $t("_profile.confirmBind") }}</el-button>
      </template>
    </el-dialog>

    <!-- Phone Dialog -->
    <el-dialog
      v-model="phoneDialogVisible"
      :title="$t('_profile.changeBindPhone')"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px">
        <el-form-item :label="$t('_profile.currentPhone')">
          <el-input :model-value="userInfo.phone" disabled />
        </el-form-item>
        <el-form-item :label="$t('_profile.newPhoneNumber')">
          <el-input v-model="newPhone" :placeholder="$t('_profile.pleaseEnterNewPhone')" />
        </el-form-item>
        <el-form-item :label="$t('_common.verifyCode')">
          <div class="verify-row">
            <el-input v-model="verifyCode" :placeholder="$t('_common.enterVerifyCode')" />
            <el-button type="primary" text @click="sendVerifyCode($t('_common.phone'))">
              {{ $t("_common.sendCode") }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="phoneDialogVisible = false">{{ $t("_common.cancel") }}</el-button>
        <el-button type="primary" @click="bindPhone">{{ $t("_profile.confirmBind") }}</el-button>
      </template>
    </el-dialog>

    <!-- WeChat Dialog -->
    <el-dialog
      v-model="wechatDialogVisible"
      :title="$t('_profile.bindWechatTitle')"
      width="380px"
      :close-on-click-modal="false"
      center
    >
      <div class="wechat-bind-content">
        <div class="qr-placeholder">
          <el-icon :size="80"><ChatLineSquare /></el-icon>
          <span>{{ $t("_profile.scanBindWechat") }}</span>
        </div>
        <p class="qr-tip">{{ $t("_profile.scanQrCodeTip") }}</p>
      </div>
      <template #footer>
        <el-button @click="wechatDialogVisible = false">{{ $t("_common.cancel") }}</el-button>
        <el-button type="primary" @click="confirmWechatBind">{{ $t("_profile.simulateBindSuccess") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.profile-page {
  padding: 4px 0;
}

// Hero
.profile-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 28px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  border-radius: 12px;
  color: #fff;
}

.hero-avatar {
  :deep(img),
  :deep(.el-avatar) {
    width: 64px !important;
    height: 64px !important;
    border: 3px solid rgba(255, 255, 255, 0.4);
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.15);
  }
}

.hero-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.hero-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hero-username {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.hero-signature {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  margin: 0;
}

.hero-tags {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.hero-tag {
  background: rgba(255, 255, 255, 0.2) !important;
  border-color: rgba(255, 255, 255, 0.25) !important;
  color: #fff !important;

  :deep(.el-tag__content) {
    color: #fff;
  }
}

.hero-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
}

.register-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.hero-stats {
  display: flex;
  gap: 16px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  padding: 10px 16px;
}

.hero-stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: rgba(255, 255, 255, 0.85);
}

.hero-stat-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.hero-stat-value {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.hero-stat-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
}

// Content
.content-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 0 24px 24px;
  min-height: 400px;
  box-shadow: var(--tk-box-shadow-sm);
}

.avatar-upload-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 0 20px;
}

.avatar-upload-hint {
  font-size: 13px;
  color: var(--tk-gray-color-500);
}

.side-card {
  background: var(--tk-surface-bg-color-box);
  border: 1px solid var(--tk-surface-border-color);
  border-radius: 12px;
  padding: 16px;
  box-shadow: var(--tk-box-shadow-sm);
}

// Security
.security-list {
  display: flex;
  flex-direction: column;
}

.security-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 16px;
  margin: 0 -16px;
  border-bottom: 1px solid var(--tk-surface-border-color);
  border-radius: 8px;
  transition: background 0.2s ease;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: color-mix(in srgb, var(--tk-color-primary) 3%, transparent);
  }
}

.security-left {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--tk-gray-color-500);
}

.security-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--tk-gray-color-900);
  margin-bottom: 2px;
}

.security-desc {
  font-size: 12px;
  color: var(--tk-gray-color-500);
}

.verify-row {
  display: flex;
  gap: 10px;
  width: 100%;

  .el-button {
    flex-shrink: 0;
  }
}

.wechat-bind-content {
  text-align: center;
}

.qr-placeholder {
  width: 160px;
  height: 160px;
  margin: 0 auto 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--tk-bg-color);
  border: 1px dashed var(--tk-surface-border-color);
  border-radius: 8px;
  color: var(--tk-color-success);
  font-size: 13px;
}

.qr-tip {
  font-size: 13px;
  color: var(--tk-gray-color-500);
}

// Messages tab
.tab-label-with-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.msg-badge {
  :deep(.el-badge__content) {
    transform: scale(0.8);
  }
}

.messages-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.msg-count {
  font-size: 13px;
  color: var(--tk-gray-color-500);
}

.messages-list {
  display: flex;
  flex-direction: column;
}

.msg-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  margin: 0 -16px;
  border-bottom: 1px solid var(--tk-surface-border-color);
  border-left: 3px solid transparent;
  border-radius: 0 8px 8px 0;
  transition:
    background 0.2s ease,
    border-color 0.2s ease;

  &:last-child {
    border-bottom: none;
  }
}

.msg-unread {
  background: color-mix(in srgb, var(--tk-color-primary) 3%, transparent);
  border-left-color: var(--tk-color-primary);

  &:hover {
    background: color-mix(in srgb, var(--tk-color-primary) 6%, transparent);
  }
}

.msg-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.msg-body {
  flex: 1;
  min-width: 0;
}

.msg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}

.msg-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--tk-gray-color-900);
}

.msg-time {
  font-size: 12px;
  color: var(--tk-gray-color-400);
  flex-shrink: 0;
}

.msg-content {
  font-size: 13px;
  color: var(--tk-gray-color-600);
  line-height: 1.5;
  margin: 0;
}

.msg-dot {
  flex-shrink: 0;
  margin-top: 2px;
}

// Operation Log
.oplog-list {
  display: flex;
  flex-direction: column;
}

.oplog-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  margin: 0 -16px;
  border-bottom: 1px solid var(--tk-surface-border-color);
  border-radius: 8px;
  transition: background 0.2s ease;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: color-mix(in srgb, var(--tk-color-primary) 3%, transparent);
  }
}

.oplog-dot {
  --dot-color: var(--tk-color-primary);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--dot-color) 10%, transparent);
  color: var(--dot-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.oplog-body {
  flex: 1;
  min-width: 0;
}

.oplog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 2px;
}

.oplog-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--tk-gray-color-900);
}

.oplog-time {
  font-size: 12px;
  color: var(--tk-gray-color-400);
  flex-shrink: 0;
}

.oplog-desc {
  font-size: 13px;
  color: var(--tk-gray-color-600);
  margin: 0 0 4px;
}

.oplog-meta {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: var(--tk-gray-color-400);
}

@media (max-width: 768px) {
  .profile-hero {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .hero-left {
    flex-direction: column;
  }

  .hero-right {
    align-items: center;
  }

  .hero-stats {
    flex-wrap: wrap;
    justify-content: center;
  }

  .side-card {
    margin-top: 20px;
  }
}
</style>
