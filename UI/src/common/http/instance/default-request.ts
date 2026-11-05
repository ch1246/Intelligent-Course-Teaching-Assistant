import { isValidURL, message, createSimpleUuid } from "@/common/utils";
import { useUserStore } from "@/pinia";
import router from "@/router";
import { useErrorLogStore } from "@/pinia/stores/error-log";
import { LOGIN_URL } from "@/common/config";
import { createRequest } from "../request";
import type { RequestConfig } from "../types";
import type { AxiosError } from "axios";

// 默认API请求实例，包含完整的拦截器和全局处理器
export const http = createRequest({
  options: {
    baseURL: import.meta.env.VITE_API_URL,
  },
  interceptors: {
    // 请求前处理
    onRequest: (config: RequestConfig) => {
      // 添加认证 token
      const userStore = useUserStore();
      if (userStore.accessToken) config.headers.Authorization = `Bearer ${userStore.accessToken}`;
      return config;
    },
  },
  handlers: {
    // 消息提示
    showMessage: (msg: string, type: "success" | "warning" | "info" | "error" = "info") => {
      message[type](msg);
    },
    // 用户登出处理
    logout: () => {
      const userStore = useUserStore();
      userStore.logout();
      router.push(LOGIN_URL);
    },
    // 添加错误日志
    resolveError: (error: any) => {
      const e = processError(error);
      const errorStore = useErrorLogStore();
      // 添加错误日志到 store 里
      e && errorStore.addErrorLog(e);

      // 服务器结果都没有返回(可能服务器错误可能客户端断网)，断网处理:可以跳转到断网页面
      if (!window.navigator.onLine) router.replace("/500");
    },
    // 刷新 token 函数
    refreshToken: async () => {
      try {
        const userStore = useUserStore();
        // 调用刷新 token 的 API
        const res = await userStore.doRefreshToken();
        return !!res;
      } catch (error) {
        console.error("Token refresh failed:", error);
        return false;
      }
    },
  },
});

/**
 * 处理 Axios 错误并格式化为错误日志对象
 *
 * @param error AxiosError 实例
 */
const processError = (error: AxiosError) => {
  // 直接从 error.config 取值，避免多余的 JSON 序列化/反序列化
  const config = error.config as RequestConfig | undefined;
  if (!config) return;

  const { baseURL = "", url = "", params, method = "", data } = config;
  const requestURL = isValidURL(baseURL) ? baseURL + url : url;
  let message = error.message || "";

  if (message.includes("token") || message.includes("401")) message += "，token 不存在或者失效了";

  let stack = `您发送的请求为 ${method.toUpperCase()}，您请求的地址为 ${requestURL}`;

  if (params && Object.keys(params).length > 0) {
    stack += `，请求携带的 params 为 ${JSON.stringify(params)}`;
  }
  if (data && typeof data === "object" && Object.keys(data).length > 0) {
    stack += `，请求携带的 data 为 ${JSON.stringify(data)}`;
  }

  error.stack = stack;
  error.message = message;

  return {
    id: createSimpleUuid(),
    error,
    vm: null,
    info: "axios 请求错误",
    url: window.location.href,
    hasRead: false,
  };
};
