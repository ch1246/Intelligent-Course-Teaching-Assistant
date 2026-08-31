<script setup lang="ts" name="QrCode">
import { inject } from "vue";
import { CircleClose } from "@element-plus/icons-vue";
import { QrCode } from "@/components";

const switchLoginMode = inject("switchLoginMode") as (mode: string) => void;
</script>

<template>
  <div class="qrCode-container">
    <QrCode :text="$t('_login.qrCodeLogin')" />

    <el-divider>
      <span>{{ $t("_login.qrCodeHint") }}</span>
    </el-divider>

    <el-button :icon="CircleClose" round size="large" @click="switchLoginMode('login')">
      {{ $t("_login.backToLogin") }}
    </el-button>
  </div>
</template>

<style lang="scss" scoped>
.qrCode-container {
  text-align: center;
}
</style>
