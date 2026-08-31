import { HomeFilled } from "@element-plus/icons-vue";

const homeRoutes: RouterConfigRaw = {
  path: "/home",
  name: "Home",
  component: "/home/index",
  meta: {
    title: "首页",
    icon: HomeFilled,
    isAffix: true,
    rank: 0,
  },
};

export { homeRoutes };
