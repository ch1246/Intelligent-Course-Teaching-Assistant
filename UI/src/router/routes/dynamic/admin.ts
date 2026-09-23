import { Setting } from "@element-plus/icons-vue";

const adminRoutes: RouterConfigRaw = {
  path: "/admin",
  name: "AdminCenter",
  meta: {
    title: "管理中心",
    icon: Setting,
    alwaysShowRoot: true,
    roles: ["admin", "teacher"],
  },
  children: [
    {
      path: "dashboard",
      name: "AdminDashboard",
      component: "/admin/dashboard/index",
      meta: {
        title: "管理仪表盘",
        roles: ["admin", "teacher"],
      },
    },
    {
      path: "users",
      name: "AdminUsers",
      component: "/admin/users/index",
      meta: {
        title: "用户管理",
        roles: ["admin"],
      },
    },
    {
      path: "courses",
      name: "AdminCourses",
      component: "/admin/courses/index",
      meta: {
        title: "课程管理",
        roles: ["admin"],
      },
    },
    {
      path: "enroll-review",
      name: "AdminEnrollReview",
      component: "/admin/enroll-review/index",
      meta: {
        title: "选课审核",
        roles: ["admin", "teacher"],
      },
    },
    {
      path: "vector-db",
      name: "AdminVectorDB",
      component: "/admin/vector-db/index",
      meta: {
        title: "向量知识库",
        roles: ["admin", "teacher"],
      },
    },
    {
      path: "default-model",
      name: "AdminDefaultModel",
      component: "/admin/agent-api/index",
      meta: {
        title: "Agent API 配置",
        roles: ["admin"],
      },
    },
    {
      path: "permission-switch",
      name: "AdminPermissionSwitch",
      component: "/permission/switch/index",
      meta: {
        title: "权限切换",
        roles: ["admin"],
      },
    },
    {
      path: "permission-role",
      name: "AdminPermissionRole",
      component: "/permission/role/index",
      meta: {
        title: "权限管理",
        roles: ["admin"],
      },
    },
    {
      path: "register-approval",
      name: "AdminRegisterApproval",
      component: "/admin/register-approval/index",
      meta: {
        title: "注册审核",
        roles: ["admin"],
      },
    },
    {
      path: "context-strategies",
      name: "AdminContextStrategies",
      component: "/admin/context-strategy/index",
      meta: { title: "上下文策略", roles: ["admin", "teacher"] },
    },
    {
      path: "pipelines",
      name: "AdminPipelines",
      component: "/admin/pipelines/index",
      meta: { title: "管道编排", roles: ["admin", "teacher"] },
    },
    {
      path: "traces",
      name: "AdminTraces",
      component: "/admin/traces/index",
      meta: { title: "链路追踪", roles: ["admin", "teacher"] },
    },
    {
      path: "prompts",
      name: "AdminPrompts",
      component: "/admin/prompts/index",
      meta: { title: "提示词模板", roles: ["admin", "teacher"] },
    },
    {
      path: "prompts/create",
      name: "AdminPromptsCreate",
      component: "/admin/prompts/edit",
      meta: { title: "新建模板", hideInMenu: true, roles: ["admin", "teacher"] },
    },
    {
      path: "prompts/:id/edit",
      name: "AdminPromptsEdit",
      component: "/admin/prompts/edit",
      meta: { title: "编辑模板", hideInMenu: true, roles: ["admin", "teacher"] },
    },
  ],
};

export { adminRoutes };
