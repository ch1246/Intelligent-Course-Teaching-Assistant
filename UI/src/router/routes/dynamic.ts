/**
 * 动态路由参数配置简介 📚
 *
 * @param path ==> 路由的地址，这是必须设置的，如果是个有效的 http 或者 https 链接，则点击该菜单跳转到新窗口
 * @param name ==> 路由的名字，这是必须设置的，如果开启了 I18n，某些路由又不想使用 I18n，则 name 以 _noUseI18n- 开头
 * @param component ==> 视图文件路径
 * @param meta ==> 菜单信息
 * @param meta.title ==> 显示在侧边栏、面包屑和标签栏的文字
 * @param meta.icon ==> 菜单图标
 * @param meta.hideInMenu ==> 是否不添加到菜单
 * @param meta.isAffix ==> 是否固定在 tabs nav
 * @param meta.isFull ==> 是否全屏，不渲染 Layout 布局
 * @param meta.activeMenu ==> Restful 路由搭配使用，当前路由为详情页时，需要高亮的菜单
 * @param meta.rank ==> 路由在左侧菜单的排序
 */

import { courseRoutes, settingsRoutes } from "./dynamic/course";
import { adminRoutes } from "./dynamic/admin";
import { homeRoutes } from "./dynamic/home";

export const dynamicRoutes: RouterConfigRaw[] = [
  { ...homeRoutes },
  { ...courseRoutes },
  { ...settingsRoutes },
  { ...adminRoutes },
];
