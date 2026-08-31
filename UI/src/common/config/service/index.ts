import type { ServiceConfig } from "./types";
import { defineServiceConfig } from "./override-config";

export { defaultServiceConfig } from "./base-config";

// 可以在这里覆盖框架默认的配置
const overrideServiceConfig: DeepPartial<ServiceConfig> = {
  layout: {
    watchFrame: true,
  },
  widget: {
    notification: true, // 开启通知铃铛
    search: false, // 关闭全局搜索
  },
  shortcutKey: {
    search: false, // 关闭搜索快捷键
  },
};

// 冻结对象防止运行时修改
export const serviceConfig = Object.freeze(defineServiceConfig(overrideServiceConfig));
