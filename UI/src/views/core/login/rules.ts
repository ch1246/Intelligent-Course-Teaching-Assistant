import type { FormRules } from "element-plus";
import { isPhone } from "@/common/utils";
import { t } from "@/common/languages";

/** 6位数字验证码正则 */
export const REGEXP_SIX = /^\d{6}$/;

/** 密码正则（密码格式应为8-18位数字、字母、符号的任意两种组合） */
export const REGEXP_PWD =
  /^(?![0-9]+$)(?![a-z]+$)(?![A-Z]+$)(?!([^(0-9a-zA-Z)]|[()])+$)(?!^.*[\u4E00-\u9FA5].*$)([^(0-9a-zA-Z)]|[()]|[a-z]|[A-Z]|[0-9]){8,18}$/;

/** 手机登录校验 */
export const phoneRules: FormRules = {
  phone: [
    {
      validator: (rule, value, callback) => {
        if (value === "") {
          callback(new Error(t("_login.pleaseEnterPhone")));
        } else if (!isPhone(value)) {
          callback(new Error(t("_login.pleaseEnterValidPhoneFormat")));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
  verifyCode: [
    {
      validator: (rule, value, callback) => {
        if (value === "") {
          callback(new Error(t("_login.pleaseEnterVerifyCode")));
        } else if (!REGEXP_SIX.test(value)) {
          callback(new Error(t("_login.pleaseEnterSmsCode")));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};

/** 忘记密码校验 */
export const updateRules: FormRules = {
  phone: [
    {
      validator: (rule, value, callback) => {
        if (value === "") {
          callback(new Error(t("_login.pleaseEnterPhone")));
        } else if (!isPhone(value)) {
          callback(new Error(t("_login.pleaseEnterValidPhoneFormat")));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
  verifyCode: [
    {
      validator: (rule, value, callback) => {
        if (value === "") {
          callback(new Error(t("_login.pleaseEnterVerifyCode")));
        } else if (!REGEXP_SIX.test(value)) {
          callback(new Error(t("_login.pleaseEnterSmsCode")));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
  password: [
    {
      validator: (rule, value, callback) => {
        if (value === "") {
          callback(new Error(t("_login.pleaseEnterPassword")));
        } else if (!REGEXP_PWD.test(value)) {
          callback(new Error(t("_login.passwordFormatRule")));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};
