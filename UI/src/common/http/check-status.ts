import { t } from "@/common/languages";

/**
 * 校验网络请求状态码
 * @param status 状态码
 */
export const checkStatus = (status: number) => {
  switch (status) {
    case 400: {
      return t("_httpError.requestFailed");
    }
    case 401: {
      return t("_httpError.loginExpired");
    }
    case 403: {
      return t("_httpError.noPermission");
    }
    case 404: {
      return t("_httpError.resourceNotFound");
    }
    case 405: {
      return t("_httpError.methodNotAllowed");
    }
    case 408: {
      return t("_httpError.requestTimeout");
    }
    case 500: {
      return t("_httpError.serverError");
    }
    case 502: {
      return t("_httpError.gatewayError");
    }
    case 503: {
      return t("_httpError.serviceUnavailable");
    }
    case 504: {
      return t("_httpError.gatewayTimeout");
    }
    default:
      return t("_httpError.requestFailedGeneric");
  }
};
