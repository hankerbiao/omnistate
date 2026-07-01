import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { api } from '../services/api';
import { SWITCHABLE_USERS } from '../config/users';

interface AuthContextType {
  isAuthenticated: boolean;
  currentUsername: string;
  currentUserId: string;
  currentUserData: Record<string, any> | null;  // 完整用户信息，供 ProfilePage 等组件消费
  currentUserRole: string;
  userPermissions: string[];
  handleLoginSuccess: () => Promise<void>;
  handleLogout: () => void;
  handleSwitchUser: (userId: string, password: string) => Promise<void>;
  switchableUsers: typeof SWITCHABLE_USERS;
}

const AuthContext = createContext<AuthContextType | null>(null);

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const token = localStorage.getItem('jwt_token');
    if (token) {
      api.setToken(token);
      return true;
    }
    return false;
  });

  const [userPermissions, setUserPermissions] = useState<string[]>([]);
  const [currentUsername, setCurrentUsername] = useState<string>('');
  const [currentUserId, setCurrentUserId] = useState<string>('');
  const [currentUserData, setCurrentUserData] = useState<Record<string, any> | null>(null);
  const [currentUserRole, setCurrentUserRole] = useState<string>('');

  // 防重标志：登录流程正在进行中，阻止 useEffect 恢复逻辑重复触发
  const _loginInProgress = useRef(false);

  const resolveUserRole = useCallback((userId: string) =>
    SWITCHABLE_USERS.find((u) => u.userId === userId)?.label || userId,
  []);

  const clearUserState = useCallback(() => {
    setCurrentUsername('');
    setCurrentUserId('');
    setCurrentUserData(null);
    setCurrentUserRole('');
    setUserPermissions([]);
  }, []);

  const setUserInfoFromResponse = useCallback((data: { username?: string; user_id?: string }) => {
    setCurrentUserData(data as Record<string, any>);
    if (data.username) {
      setCurrentUsername(data.username);
    } else if (data.user_id) {
      setCurrentUsername(data.user_id);
    }
    if (data.user_id) {
      setCurrentUserId(data.user_id);
      setCurrentUserRole(resolveUserRole(data.user_id));
    }
  }, [resolveUserRole]);

  const fetchUserPermissions = useCallback(async () => {
    try {
      const response = await api.getCurrentUserPermissions();
      setUserPermissions(response.data?.permissions || []);
    } catch (err) {
      console.error('Failed to fetch user permissions:', err);
      setUserPermissions([]);
    }
  }, []);

  const fetchAndSetCurrentUser = useCallback(async (): Promise<boolean> => {
    try {
      const userRes = await api.getCurrentUser();
      if (userRes.data) setUserInfoFromResponse(userRes.data);
      return true;
    } catch (err) {
      console.error('Failed to fetch current user:', err);
      return false;
    }
  }, [setUserInfoFromResponse]);

  // 应用启动时（页面刷新或首次加载），从 token 恢复用户信息
  useEffect(() => {
    if (isAuthenticated && !currentUserId && !_loginInProgress.current) {
      _loginInProgress.current = true;
      (async () => {
        const ok = await fetchAndSetCurrentUser();
        if (!ok) {
          api.clearToken();
          setIsAuthenticated(false);
          clearUserState();
          _loginInProgress.current = false;
          return;
        }
        await fetchUserPermissions();
        _loginInProgress.current = false;
      })();
    }
  }, [isAuthenticated, currentUserId, fetchAndSetCurrentUser, clearUserState, fetchUserPermissions]);

  const handleLoginSuccess = useCallback(async () => {
    _loginInProgress.current = true;
    setIsAuthenticated(true);
    await fetchAndSetCurrentUser();
    await fetchUserPermissions();
    _loginInProgress.current = false;
  }, [fetchAndSetCurrentUser, fetchUserPermissions]);

  const handleLogout = useCallback(() => {
    api.clearToken();
    setIsAuthenticated(false);
    setUserPermissions([]);
    setCurrentUsername('');
    setCurrentUserId('');
    setCurrentUserRole('');
  }, []);

  const handleSwitchUser = useCallback(async (userId: string, password: string) => {
    try {
      const loginRes = await api.login({ user_id: userId, password });
      api.setToken(loginRes.data.access_token);
      const ok = await fetchAndSetCurrentUser();
      if (!ok) throw new Error('获取用户信息失败');
      const permRes = await api.getCurrentUserPermissions();
      setUserPermissions(permRes.data?.permissions || []);
    } catch (err) {
      console.error('Switch user failed:', err);
    }
  }, [fetchAndSetCurrentUser]);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        currentUsername,
        currentUserId,
        currentUserData,
        currentUserRole,
        userPermissions,
        handleLoginSuccess,
        handleLogout,
        handleSwitchUser,
        switchableUsers: SWITCHABLE_USERS,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
