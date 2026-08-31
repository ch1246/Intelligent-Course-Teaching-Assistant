<script setup lang="ts" name="UserAvatar">
import type { UserInfo } from "@/pinia";
import { ref, toRefs } from "vue";
import { ElMessage } from "element-plus";
import { serviceConfig } from "@/common/config";
import { t } from "@/common/languages";
import { Cropper } from "@/components";
import { useNamespace } from "@/composables";
import { useUserStore } from "@/pinia";
import { http } from "@/common/http";

const ns = useNamespace("user-avatar");

const props = defineProps<{ user: UserInfo }>();
const { user } = toRefs(props);
const dialogVisible = ref(false);

const userStore = useUserStore();

const openDialog = () => {
  dialogVisible.value = true;
};

const handleClose = () => {
  dialogVisible.value = false;
};
const uploadImage = async (imgData: FormData) => {
  const avatarFile = imgData.get("file") as File;
  if (avatarFile) {
    try {
      const res = await http.post<httpNs.Response<{ avatar: string }>>("/profile/avatar", imgData, {
        headers: { "Content-Type": "multipart/form-data" },
      } as any);
      const avatarUrl = res.data?.avatar || (typeof res.data === "string" ? res.data : "");
      if (avatarUrl) {
        userStore.setUserInfo({ ...userStore.userInfo, avatar: avatarUrl });
      }
      dialogVisible.value = false;
      ElMessage.success(t("_profile.avatarChanged"));
    } catch {
      ElMessage.error(t("_profile.avatarUploadFailed"));
    }
  }
};
</script>

<template>
  <div :class="ns.b()">
    <div :class="ns.e('header')" @click="openDialog">
      <el-image
        :src="user.avatar"
        :title="$t('_profile.clickUploadAvatar')"
        :class="ns.e('avatar')"
        :alt="$t('_profile.avatar')"
      >
        <template #error>
          <el-image :src="serviceConfig.layout.avatar" :class="ns.e('avatar')" :alt="$t('_profile.avatar')" />
        </template>
      </el-image>
    </div>

    <el-dialog
      :title="$t('_profile.changeAvatar')"
      v-model="dialogVisible"
      width="800px"
      append-to-body
      @close="handleClose"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <Cropper
        :imgLink="user.avatar"
        :crop-width="200"
        :crop-height="200"
        :crop-container-height="350"
        image-type="base64"
        @upload-image="uploadImage"
      />
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
@use "./index";
</style>
