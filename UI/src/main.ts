// ── 清除旧版本缓存（升级前版本遗留数据）──
(function () {
  const OLD_PREFIXES = ["teek-v2:", "teek-v1:"] as const;
  const keys = Object.keys(localStorage);
  let cleared = 0;
  for (const k of keys) {
    if (OLD_PREFIXES.some(p => k.startsWith(p))) {
      localStorage.removeItem(k);
      cleared++;
    }
  }
  if (cleared > 0) console.info(`[init] 已清除 ${cleared} 条旧版本缓存，即将重建路由与菜单`);
})();

import { createApp } from "vue";
import pinia from "@/pinia";
import router from "@/router";
import directives from "@/common/directives";
import I18n from "@/common/languages";
import { errorHandler, checkNeed, log } from "@/common/utils";
import { Icon, Auth, Role } from "@/components";
import App from "./App.vue";
import Vue3TreeOrg from "vue3-tree-org";
import "virtual:svg-icons-register";
import "vue3-tree-org/lib/vue3-tree-org.css";

import "@styles/normalize.css";
import "@styles/reset.css";
import "@styles/var/index.scss"; // 主题变量
import "@styles/common/base.scss";
import "@styles/common/atomic.scss";
import "@styles/common/scrollbar.scss";
import "@styles/common/transition.scss";
import "@styles/common/theme-animation.scss";
import "@styles/plugin.scss";

// 重写部分 Element Plus 样式
import "@styles/element-plus/el-ui.scss";
import "@styles/element-plus/el-dark.scss";
// Element Plus 全量样式：同步引入，避免首屏 FOUC（登录页输入框/表单样式闪烁）
import "@styles/element-plus/el-light.scss";

// 系统图标
import "@/common/assets/iconfont/system/iconfont.js";
import "@assets/iconfont/system/iconfont.css";

const app = createApp(App);

window.log = log;
checkNeed() && (app.config.errorHandler = errorHandler);

// 全局注册按钮级别权限、页面级别权限、Icon 图标组件组件
app.use(Auth).use(Role).use(Icon);

// 注册树形组件
app.use(Vue3TreeOrg);

// 是否全部引入 Element Plus 的组件
if (import.meta.env.VITE_LOAD_ALL_EP_COMPONENTS === "true") {
  import("element-plus").then(ElementPlus => {
    app.use(ElementPlus);
  });
}

// KaTeX — 聊天数学公式渲染
import "katex/dist/katex.min.css";

app.use(I18n).use(pinia).use(router).use(directives).mount("#app");
