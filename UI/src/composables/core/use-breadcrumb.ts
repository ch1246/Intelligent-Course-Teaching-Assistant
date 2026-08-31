import type { RouteLocationNormalizedLoaded } from "vue-router";
import { ref, watch, readonly } from "vue";
import { tryOnScopeDispose } from "@vueuse/core";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { LAYOUT_NAME, HOME_NAME } from "@/common/config";
import { formatTitle } from "@/router/helper";
import { useRouteStore } from "@/pinia";
import { useRouteFn } from "./use-route-fn";

/**
 * 面包屑导航管理
 */
export const useBreadcrumbs = () => {
  const breadcrumbList = ref<RouteLocationNormalizedLoaded[]>([]);
  const { homeRoute, loadedRouteList } = useRouteStore();
  const { findParentRoutesByPath } = useRouteFn();
  const route = useRoute();

  /**
   * 检查首页路由是否有效
   */
  const isValidHomeRoute = () => {
    return !!homeRoute?.path && !!homeRoute?.name;
  };

  /**
   * 获取面包屑列表
   */
  const getBreadcrumbs = (currentRoute: RouteLocationNormalizedLoaded): RouteLocationNormalizedLoaded[] => {
    // 首页不存在
    if (!isValidHomeRoute()) {
      ElMessage.error({
        message:
          "您的首页无法获取，请前往 router/routesConfig.ts，找到 HOME_NAME 变量，将 HOME_NAME 值修改为您首页路由的 name 值",
        duration: 10000,
      });
      return [];
    }

    // 当前路由的父级路由组成的数组
    let matched = findParentRoutesByPath(
      currentRoute.meta._fullPath,
      loadedRouteList
    ) as RouteLocationNormalizedLoaded[];
    currentRoute.meta.title = formatTitle(currentRoute);
    matched.push(currentRoute);

    // 首页加上其他页面（如果当前就是首页，不重复添加）
    const isHomeRoute = currentRoute.name === HOME_NAME;
    if (!isHomeRoute) {
      const homeBreadcrumb = {
        ...homeRoute,
        meta: { ...homeRoute?.meta, title: "首页" },
      } as RouteLocationNormalizedLoaded;
      matched = [homeBreadcrumb, ...matched];
    }
    // 过滤掉 hideInBread 的配置
    return matched.filter(
      item => (item.name || item.meta?.title) && !item.meta?.hideInBread && item.name !== LAYOUT_NAME
    );
  };

  const stop = watch(
    () => route.fullPath,
    () => (breadcrumbList.value = getBreadcrumbs(route)),
    { immediate: true }
  );

  tryOnScopeDispose(stop);

  return { breadcrumbList: readonly(breadcrumbList), getBreadcrumbs };
};
