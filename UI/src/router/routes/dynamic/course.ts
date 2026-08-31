import { School, Setting } from "@element-plus/icons-vue";

const courseRoutes: RouterConfigRaw = {
  path: "/course",
  name: "CourseCenter",
  meta: {
    title: "课程中心",
    icon: School,
    alwaysShowRoot: true,
  },
  children: [
    {
      path: "dashboard",
      name: "CourseDashboard",
      component: "/course/dashboard/index",
      meta: {
        title: "课程仪表盘",
      },
    },
    {
      path: "enroll",
      name: "CourseEnroll",
      component: "/course/enroll/index",
      meta: {
        title: "课程申请",
      },
    },
    {
      path: "learning-time",
      name: "CourseLearningTime",
      component: "/course/learning-time/index",
      meta: {
        title: "学习时长",
        hideInMenu: true,
      },
    },
    {
      path: "chat-stats",
      name: "CourseChatStats",
      component: "/course/chat-stats/index",
      meta: {
        title: "对话统计",
        hideInMenu: true,
      },
    },
    {
      path: "chat/:courseId",
      name: "CourseChat",
      component: "/course/chat/index",
      meta: {
        title: "智能对话",
        hideInMenu: true,
        hideInTab: true,
        activeMenu: "/course/dashboard",
      },
    },
    {
      path: "summary",
      name: "CourseSummary",
      component: "/course/summary/index",
      meta: {
        title: "一键总结",
        hideInMenu: true,
        hideInTab: true,
      },
    },
  ],
};

const settingsRoutes: RouterConfigRaw = {
  path: "/settings",
  name: "Settings",
  component: "/settings/index",
  meta: {
    title: "个人设置",
    icon: Setting,
    hideInMenu: true,
  },
};

export { courseRoutes, settingsRoutes };
