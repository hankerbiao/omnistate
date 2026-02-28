import { useState, useCallback } from 'react';
import { User } from '../../constants/config';

interface LoginForm {
  user_id: string;
  password: string;
  rememberMe: boolean;
}

export function useAuth(initialUsers: User[]) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loginForm, setLoginForm] = useState<LoginForm>({ user_id: '', password: '', rememberMe: false });
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');

  const handleLogin = useCallback(() => {
    if (!loginForm.user_id || !loginForm.password) {
      setLoginError('请输入用户ID和密码');
      return false;
    }
    const user = initialUsers.find(u => u.user_id === loginForm.user_id && u.status === 'ACTIVE');
    if (user) {
      setCurrentUser(user);
      setIsLoggedIn(true);
      setLoginError('');
      return true;
    } else {
      setLoginError('用户ID或密码错误');
      return false;
    }
  }, [loginForm.user_id, loginForm.password, initialUsers]);

  const handleLogout = useCallback(() => {
    setIsLoggedIn(false);
    setCurrentUser(null);
  }, []);

  const login = useCallback((user: User) => {
    setCurrentUser(user);
    setIsLoggedIn(true);
  }, []);

  return {
    isLoggedIn,
    currentUser,
    loginForm,
    setLoginForm,
    showPassword,
    setShowPassword,
    loginError,
    setLoginError,
    handleLogin,
    handleLogout,
    login,
  };
}
