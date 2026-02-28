import { BACKEND_API_BASE_URL, BACKEND_API_TIMEOUT_MS } from '../../constants/config';
import { ApiClient } from './ApiClient';
import { TestDesignerApi } from './TestDesignerApi';

const normalizedBaseUrl = BACKEND_API_BASE_URL.trim();

export const isBackendEnabled = normalizedBaseUrl.length > 0;

// ========== 认证令牌管理 ==========

let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
};

export const getAccessToken = (): string | null => {
  return accessToken;
};

export const clearAccessToken = () => {
  accessToken = null;
};

export const testDesignerApi = isBackendEnabled
  ? new TestDesignerApi(
      new ApiClient({
        baseUrl: normalizedBaseUrl,
        timeoutMs: BACKEND_API_TIMEOUT_MS,
        getAuthToken: () => accessToken
      })
    )
  : null;
