import type { LoginParams } from "@/common/api/user";
import { ref } from "vue";
import { defineStore } from "pinia";
import { useRouteFn } from "@/composables";
import { resetRouter } from "@/router";
import { useLayoutStore } from "./layout";
import { UserService } from "@/common/api/user";
import { http } from "@/common/http";

export interface UserInfo {
  /** 用户 ID */
  userId?: string;
  /** 用户名 */
  username?: string;
  /** 用户性别 */
  sex?: string;
  /** 年龄 */
  age?: number;
  /** 签名 */
  signature?: string;
  /** 用户邮箱 */
  email?: string;
  /** 用户联系方式 */
  phone?: string;
  /** 用户头像 */
  avatar?: string;
  /** 用户角色 */
  roles?: string[];
  /** 职位/专业 */
  major?: string;
  grade?: string;
  studentId?: string;
  /** 部门/学院 */
  dept?: string;
  /** 注册时间 */
  registerTime?: string;
}

export const useUserStore = defineStore(
  "userStore",
  () => {
    const accessToken = ref("");
    const refreshToken = ref("");

    const userInfo = ref<UserInfo>({});
    const roles = ref<string[]>([]);
    const searchHistory = ref<RouterConfig[]>([]);

    // 锁屏状态
    const isLock = ref(false);
    // 锁屏密码
    const lockPassword = ref("");

    const login = async (loginParams: LoginParams) => {
      try {
        const res = await UserService.login(loginParams);
        const { accessToken, refreshToken, user } = res.data;
        setToken(accessToken, refreshToken);
        // 后端登录接口同步返回 user 信息，立即缓存
        if (user) {
          const rolesArr = user.role ? [user.role] : user.roles || [];
          setUserInfo({
            userId: String(user.id || ""),
            username: user.username || "",
            roles: rolesArr,
            avatar: user.avatar || "",
            signature: user.signature || "",
            sex: user.sex || "",
            dept: user.dept || "",
            major: user.major || "",
            grade: user.grade || "",
            studentId: user.student_id || "",
            email: user.email || "",
            phone: user.phone || "",
            age: user.age,
            registerTime: user.date_joined || "",
          });
        }
        return { accessToken, refreshToken, user };
      } catch {
        return null;
      }
    };

    const getUserInfo = async () => {
      try {
        const res = await UserService.getUserInfo();
        const data = res.data;
        // 后端返回 role 单值，前端用 roles 数组
        const userInfo: UserInfo = {
          userId: String(data.id || ""),
          username: data.username,
          sex: data.sex,
          age: data.age,
          signature: data.signature,
          email: data.email,
          phone: data.phone,
          avatar: data.avatar,
          roles: data.role ? [data.role] : [],
          major: data.major || "",
          grade: data.grade || "",
          studentId: data.student_id || "",
          dept: data.dept,
          registerTime: data.date_joined,
        };
        setUserInfo(userInfo);
        return userInfo;
      } catch {
        return null;
      }
    };

    /**
     * 刷新 token
     */
    const doRefreshToken = async () => {
      try {
        const res = await http.post<httpNs.Response<{ accessToken: string; refreshToken: string }>>("/auth/refresh", {
          refreshToken: refreshToken.value,
        });
        const { accessToken: newAt, refreshToken: newRt } = res.data;
        setToken(newAt, newRt);
        return true;
      } catch {
        return false;
      }
    };

    /**
     * 设置锁屏状态
     * @param status 锁屏状态
     */
    const setLockStatus = (status: boolean) => {
      isLock.value = status;
    };

    /**
     * 设置锁屏密码
     * @param password 锁屏密码
     */
    const setLockPassword = (password: string) => {
      lockPassword.value = password;
    };

    const logout = async () => {
      // 重置锁屏状态
      isLock.value = false;
      // 清空锁屏密码
      lockPassword.value = "";
      userInfo.value = {};
      clearPermission();

      const layoutStore = useLayoutStore();
      layoutStore.removeAllTabs();
      layoutStore.setKeepAliveName();
      resetRouter();
    };

    const clearPermission = () => {
      setToken("", "");
      setRoles([]);
    };

    const changeRoles = async (rolesParam: string[]) => {
      // 模拟新的 token
      const accessToken = rolesParam[0] + "-token";
      setToken(accessToken);
      setRoles(rolesParam); // 正常不是直接赋予角色，而是调用 this.getUserInfo(token)，根据 token 重新获取对应的角色
      // await this.getUserInfo(token);
      resetRouter();
      useRouteFn().initDynamicRoutes(rolesParam);
    };

    const setToken = (newAccessToken: string, newRefreshToken?: string) => {
      accessToken.value = newAccessToken;
      if (newRefreshToken) {
        refreshToken.value = newRefreshToken;
      }
    };

    const setUserInfo = (userInfoParam: UserInfo) => {
      userInfo.value = userInfoParam;
      roles.value = userInfoParam.roles || [];
    };

    const setRoles = (rolesParam: string[]) => (roles.value = rolesParam);

    const setSearchHistory = (searchHistoryParam: RouterConfig[]) => (searchHistory.value = searchHistoryParam);

    return {
      lockPassword,
      accessToken,
      refreshToken,
      userInfo,
      roles,
      searchHistory,
      isLock,

      login,
      logout,
      getUserInfo,
      doRefreshToken,
      clearPermission,
      changeRoles,
      setUserInfo,
      setToken,
      setRoles,
      setSearchHistory,
      setLockStatus,
      setLockPassword,
    };
  },
  {
    persist: {
      pick: ["accessToken", "refreshToken", "searchHistory", "isLock", "lockPassword", "roles", "userInfo"],
    },
  }
);
