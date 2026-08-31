<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { CircleCheckFilled } from "@element-plus/icons-vue";
import { useNamespace, useTheme } from "@/composables";
import { useSettingStore } from "@/pinia";
import { serviceConfig } from "@/common/config";
import { GlobalThemeEnum } from "@/common/enums";
import lightTheme from "@/common/assets/images/system-theme/light.png";
import darkTheme from "@/common/assets/images/system-theme/dark.png";
import systemTheme from "@/common/assets/images/system-theme/system.png";

defineOptions({ name: "GlobalTheme" });

const ns = useNamespace("global-theme");

const { changeGlobalTheme, changeFunctionalColor, changeGreyOrWeak } = useTheme();
const settingStore = useSettingStore();
const { t } = useI18n();

const { theme } = storeToRefs(settingStore);

const globalThemeModeList = [
  { name: computed(() => t("_setting.theme.modeSelect.light")), theme: GlobalThemeEnum.Light, img: lightTheme },
  {
    name: computed(() => t("_setting.theme.modeSelect.dark")),
    theme: GlobalThemeEnum.Dark,
    img: darkTheme,
  },
  { name: computed(() => t("_setting.theme.modeSelect.system")), theme: GlobalThemeEnum.System, img: systemTheme },
];

/**
 * 颜色配置项列表
 */
const functionalColorOptions: { type: any; labelKey: string; storeKey: string }[] = [
  { type: "primary", labelKey: "_setting.theme.primaryColor", storeKey: "primaryColor" },
  { type: "success", labelKey: "_setting.theme.successColor", storeKey: "successColor" },
  { type: "warning", labelKey: "_setting.theme.warningColor", storeKey: "warningColor" },
  { type: "danger", labelKey: "_setting.theme.dangerColor", storeKey: "dangerColor" },
  { type: "error", labelKey: "_setting.theme.errorColor", storeKey: "errorColor" },
  { type: "info", labelKey: "_setting.theme.infoColor", storeKey: "infoColor" },
  // 如果还有 secondary，也可以加在这里
  // { type: "secondary", labelKey: "_setting.theme.secondaryColor", storeKey: "secondaryColor" },
];

// 预定义主题颜色
const colorList = computed(() => [
  theme.value.primaryColor,
  theme.value.successColor,
  theme.value.warningColor,
  theme.value.dangerColor,
  theme.value.errorColor,
  theme.value.infoColor,
  ...(serviceConfig.theme.presetsColor ?? []),
]);

/**
 * 圆角选项
 */
const radiusOptions = [
  { value: 0, label: "None" },
  { value: 0.25, label: "Small" },
  { value: 0.5, label: "Medium" },
  { value: 0.75, label: "Large" },
  { value: 1, label: "Round" },
  { value: 1.25, label: "Round Small" },
  { value: 1.5, label: "Round Medium" },
  { value: 1.75, label: "Round Large" },
  { value: 2, label: "Round Plus" },
];
</script>

<template>
  <div :class="ns.b()">
    <div class="flx-wrap gap-15">
      <div
        v-for="item in globalThemeModeList"
        :key="item.theme"
        :class="ns.e('theme-item')"
        @click="changeGlobalTheme(item.theme)"
      >
        <div :class="[ns.e('box'), ns.is('active', item.theme === theme.globalThemeMode)]">
          <img :src="item.img" />
        </div>
        <Icon :class="ns.m('icon')" v-show="item.theme === theme.globalThemeMode"><CircleCheckFilled /></Icon>
        <p :class="ns.m('name')">{{ item.name }}</p>
      </div>
    </div>

    <!-- 主题外观锁定为 Teek 品牌 -->
    <!--
    <div :class="ns.e('item')">
      <span>主题外观</span>
      <el-select v-model="theme.surface" placeholder="Select" @change="changeThemeSurface" style="width: 50%">
        ...
      </el-select>
    </div>
    -->

    <div :class="ns.e('item-two')">
      <template v-for="item in functionalColorOptions" :key="item.type">
        <div>
          <span>{{ $t(item.labelKey) }}</span>
          <el-color-picker
            v-model="(theme as any)[item.storeKey]"
            :predefine="colorList"
            @change="val => val && changeFunctionalColor(val, item.type)"
          />
        </div>
      </template>
    </div>

    <div :class="ns.e('item')">
      <span>{{ $t("_setting.theme.functionalColorStrictly") }}</span>
      <el-switch v-model="theme.functionalColorStrictly" />
    </div>

    <div :class="ns.e('item')">
      <span>{{ $t("_setting.theme.greyMode") }}</span>
      <el-switch v-model="theme.greyMode" @change="changeGreyOrWeak($event as boolean, 'greyMode')" />
    </div>

    <div :class="ns.e('item')">
      <span>{{ $t("_setting.theme.weakMode") }}</span>
      <el-switch v-model="theme.weakMode" @change="changeGreyOrWeak($event as boolean, 'weakMode')" />
    </div>

    <div :class="ns.e('item')">
      <span>{{ $t("_setting.theme.radius") }}</span>
      <el-select v-model="theme.radius" placeholder="Select" style="width: 50%">
        <el-option v-for="item in radiusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "./index";
</style>
