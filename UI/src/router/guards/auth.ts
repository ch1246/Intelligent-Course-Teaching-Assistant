import type { Router } from "vue-router";
import { serviceConfig, LOGIN_URL } from "@/common/config";
import { useRouteFn } from "@/composables";
import { useRouteStore, useUserStore } from "@/pinia";
import { resetRouter } from "..";

export const createAuthGuard = (router: Router) => {
  let preloadDone = false;

  router.beforeEach(async (to, _from) => {
    const userStore = useUserStore();
    const routeStore = useRouteStore();
    const { initDynamicRoutes } = useRouteFn();
    const accessToken = userStore.accessToken;
    const whiteList = serviceConfig.router.whiteList;

    // 登录页：有 token 则留在当前页
    if (to.path === LOGIN_URL) {
      if (accessToken) return _from.fullPath;
      resetRouter();
      return true;
    }

    // 白名单放行
    if (whiteList.includes("*") || whiteList.includes("next") || whiteList.includes(to.path)) {
      if (!routeStore.loadedRouteList.length) {
        await initDynamicRoutes(["*"]);
        return { ...to, replace: true };
      }
      return true;
    }

    // 无 token → 登录页
    if (!accessToken) return { path: LOGIN_URL, replace: true };

    // 路由未加载 → 初始化
    if (!routeStore.loadedRouteList.length) {
      try {
        // 从缓存读取角色，同时后台刷新确保最新
        let roles = userStore.roles;
        if (!roles.length) {
          // 缓存未命中，必须等 API
          const info = await userStore.getUserInfo();
          if (info && info.roles && info.roles.length) {
            roles = info.roles;
          }
        }
        // 兜底：如果还是没有角色，尝试以 token payload 推断
        if (!roles.length) {
          try {
            const payload = JSON.parse(atob(accessToken.split(".")[1]));
            if (payload.role) roles = [payload.role];
          } catch {
            /* ignore */
          }
        }
        if (!roles.length) {
          userStore.clearPermission();
          return { path: LOGIN_URL, replace: true };
        }
        await initDynamicRoutes(roles);
        return { ...to, replace: true };
      } catch {
        userStore.clearPermission();
        return { path: LOGIN_URL, replace: true };
      }
    }

    return true;
  });

  router.afterEach(() => {
    if (!preloadDone) {
      try {
        const s = useRouteStore();
        if (s.loadedRouteList.length) {
          preloadDone = true;
          const preload = () => {
            import("@/views/home/index.vue").catch(() => {});
            import("@/views/course/dashboard/index.vue").catch(() => {});
          };
          typeof requestIdleCallback !== "undefined"
            ? requestIdleCallback(preload, { timeout: 2000 })
            : setTimeout(preload, 300);
        }
      } catch {
        /* ignore */
      }
    }
  });
};
