/**
 * @fileoverview 认证状态管理Hook
 * 统一管理用户登录状态、表单数据和认证逻辑
 */

import { useState, useCallback } from 'react';
import { User } from '../../constants/config';

// ========== 本地数据类型定义 ==========

/**
 * 登录表单数据结构
 */
interface LoginForm {
  user_id: string;    // 用户ID
  password: string;   // 密码
  rememberMe: boolean; // 记住我选项
}

/**
 * 认证状态管理Hook
 * 提供完整的用户认证状态管理功能，包括：
 * - 登录状态跟踪
 * - 当前用户信息管理
 * - 登录表单数据管理
 * - 密码显示控制
 * - 登录错误处理
 * @param initialUsers 初始用户列表（用于本地登录验证）
 * @returns 认证状态和方法
 */
export function useAuth(initialUsers: User[]) {
  // ========== 状态定义 ==========

  /** 是否已登录 */
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  /** 当前登录用户信息 */
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  /** 登录表单数据 */
  const [loginForm, setLoginForm] = useState<LoginForm>({
    user_id: '',
    password: '',
    rememberMe: false
  });

  /** 是否显示密码（安全考虑，默认隐藏） */
  const [showPassword, setShowPassword] = useState(false);

  /** 登录错误消息 */
  const [loginError, setLoginError] = useState('');

  // ========== 认证方法 ==========

  /**
   * 处理本地登录验证
   * 在初始用户列表中查找匹配的用户
   * @returns boolean 登录是否成功
   */
  const handleLogin = useCallback((): boolean => {
    // 验证输入完整性
    if (!loginForm.user_id || !loginForm.password) {
      setLoginError('请输入用户ID和密码');
      return false;
    }

    // 在初始用户列表中查找匹配用户（仅ACTIVE状态）
    const user = initialUsers.find(
      u => u.user_id === loginForm.user_id && u.status === 'ACTIVE'
    );

    // 登录成功处理
    if (user) {
      setCurrentUser(user);
      setIsLoggedIn(true);
      setLoginError(''); // 清除错误消息
      return true;
    }

    // 登录失败处理
    setLoginError('用户ID或密码错误');
    return false;
  }, [loginForm.user_id, loginForm.password, initialUsers]);

  /**
   * 处理用户登出
   * 清除所有认证状态
   */
  const handleLogout = useCallback(() => {
    setIsLoggedIn(false);
    setCurrentUser(null);
  }, []);

  /**
   * 直接设置用户登录状态
   * 用于后端登录成功后调用
   * @param user 用户信息对象
   */
  const login = useCallback((user: User) => {
    setCurrentUser(user);
    setIsLoggedIn(true);
  }, []);

  // ========== 返回值 ==========

  return {
    // 状态
    isLoggedIn,           // 登录状态
    currentUser,          // 当前用户
    loginForm,            // 登录表单数据
    showPassword,         // 密码显示状态
    loginError,           // 登录错误消息

    // 表单操作方法
    setLoginForm,         // 更新表单数据
    setShowPassword,      // 切换密码显示
    setLoginError,        // 设置错误消息

    // 认证操作方法
    handleLogin,          // 登录处理
    handleLogout,         // 登出处理
    login,                // 直接登录
  };
}
