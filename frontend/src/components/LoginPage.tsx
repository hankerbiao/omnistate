import { useState } from 'react';
import { Hexagon, Check, AlertTriangle, User, Lock, ArrowRight, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { LoginRequest } from '../types';

interface LoginPageProps {
  onLoginSuccess?: () => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [formData, setFormData] = useState<LoginRequest>(() => {
    const savedUserId = localStorage.getItem('saved_user_id') || 'admin';
    const savedPassword = localStorage.getItem('saved_password') || 'Test@123';
    return {
      user_id: savedUserId,
      password: savedPassword,
    };
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [rememberPassword, setRememberPassword] = useState(() => {
    return !!localStorage.getItem('saved_user_id');
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await api.login(formData);

      const token = response.data.access_token;
      localStorage.setItem('jwt_token', token);
      api.setToken(token);

      if (rememberPassword) {
        localStorage.setItem('saved_user_id', formData.user_id);
        localStorage.setItem('saved_password', formData.password);
      } else {
        localStorage.removeItem('saved_user_id');
        localStorage.removeItem('saved_password');
      }

      setSuccess(true);

      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (err) {
      setError('登录失败，请检查用户名和密码');
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  return (
    <div style={styles.container}>
      <div style={styles.backgroundPattern} />
      <div style={styles.glowOrb1} />
      <div style={styles.glowOrb2} />

      <div style={styles.card}>
        <div style={styles.logoSection}>
          <Hexagon size={48} strokeWidth={1.5} style={{ color: 'var(--accent-primary)', display: 'block', margin: '0 auto 12px' }} />
          <h1 style={styles.title}>TestHub</h1>
          <p style={styles.subtitle}>测试管理平台</p>
        </div>

        {success && (
          <div style={styles.successMessage}>
            <Check size={16} strokeWidth={2.5} />
            登录成功
          </div>
        )}

        {error && (
          <div style={styles.errorMessage}>
            <AlertTriangle size={16} />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputGroup}>
            <label htmlFor="user_id" style={styles.label}>
              <User size={13} style={{ color: 'var(--accent-primary)' }} />
              用户ID
            </label>
            <input
              type="text"
              id="user_id"
              name="user_id"
              value={formData.user_id}
              onChange={handleChange}
              style={styles.input}
              placeholder="请输入用户ID"
              required
            />
          </div>

          <div style={styles.inputGroup}>
            <label htmlFor="password" style={styles.label}>
              <Lock size={13} style={{ color: 'var(--accent-primary)' }} />
              密码
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              style={styles.input}
              placeholder="请输入密码"
              required
            />
          </div>

          <div style={styles.checkboxGroup}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={rememberPassword}
                onChange={(e) => setRememberPassword(e.target.checked)}
                style={styles.checkboxInput}
              />
              <span
                style={{
                  ...styles.checkboxCustom,
                  ...(rememberPassword ? styles.checkboxCustomChecked : {}),
                }}
              >
                {rememberPassword && <Check size={12} strokeWidth={3} style={{ color: 'var(--surface-primary)' }} />}
              </span>
              <span style={styles.checkboxText}>保存密码</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              ...styles.button,
              ...(loading ? styles.buttonDisabled : {}),
            }}
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                登录中...
              </>
            ) : (
              <>
                <ArrowRight size={16} />
                登录
              </>
            )}
          </button>
        </form>

        <div style={styles.footer}>
          <p style={styles.footerText}>
            API: <code style={styles.apiCode}>{import.meta.env.VITE_API_BASE_URL || 'localhost:8000'}</code>
          </p>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'var(--bg-primary)',
    padding: '20px',
    position: 'relative',
    overflow: 'hidden',
  } as const,
  backgroundPattern: {
    position: 'absolute',
    inset: 0,
    backgroundImage: `radial-gradient(circle at 1px 1px, var(--border-default) 1px, transparent 0)`,
    backgroundSize: '40px 40px',
    opacity: 0.5,
  } as const,
  glowOrb1: {
    position: 'absolute',
    top: '10%',
    left: '20%',
    width: '400px',
    height: '400px',
    background: 'radial-gradient(circle, rgba(37, 99, 235, 0.12) 0%, transparent 70%)',
    filter: 'blur(60px)',
    pointerEvents: 'none',
  } as const,
  glowOrb2: {
    position: 'absolute',
    bottom: '10%',
    right: '20%',
    width: '300px',
    height: '300px',
    background: 'radial-gradient(circle, rgba(37, 99, 235, 0.08) 0%, transparent 70%)',
    filter: 'blur(60px)',
    pointerEvents: 'none',
  } as const,
  card: {
    position: 'relative',
    backgroundColor: 'var(--surface-elevated)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-subtle)',
    boxShadow: 'var(--shadow-lg)',
    padding: '48px 40px',
    width: '100%',
    maxWidth: '420px',
    animation: 'scaleIn 0.4s ease',
  } as const,
  logoSection: {
    textAlign: 'center' as const,
    marginBottom: '36px',
  } as const,
  title: {
    fontSize: '32px',
    fontWeight: 700,
    letterSpacing: '-1px',
    color: 'var(--accent-primary)',
    margin: 0,
  } as const,
  subtitle: {
    fontSize: '14px',
    color: 'var(--text-tertiary)',
    marginTop: '8px',
    letterSpacing: '2px',
    textTransform: 'uppercase' as const,
  } as const,
  form: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '24px',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  },
  label: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    letterSpacing: '0.5px',
  } as const,
  checkboxGroup: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    marginTop: '-12px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
    userSelect: 'none' as const,
  },
  checkboxInput: {
    position: 'absolute' as const,
    opacity: 0,
    width: 0,
    height: 0,
  },
  checkboxCustom: {
    width: '18px',
    height: '18px',
    borderRadius: '4px',
    border: '2px solid var(--border-default)',
    backgroundColor: 'var(--surface-primary)',
    transition: 'all var(--transition-fast)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  checkboxCustomChecked: {
    backgroundColor: 'var(--accent-primary)',
    border: '2px solid var(--accent-primary)',
  },
  checkboxText: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
  } as const,
  input: {
    width: '100%',
    padding: '14px 16px',
    fontSize: '15px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-primary)',
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    transition: 'all var(--transition-fast)',
  } as const,
  button: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    padding: '14px 24px',
    fontSize: '15px',
    fontWeight: 600,
    color: '#ffffff',
    backgroundColor: 'var(--accent-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
    marginTop: '8px',
  } as const,
  buttonDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  } as const,
  spinner: {
    width: '16px',
    height: '16px',
    border: '2px solid transparent',
    borderTopColor: 'currentColor',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  } as const,
  errorMessage: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 16px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--status-error)',
    fontSize: '14px',
    marginBottom: '24px',
    animation: 'slideDown 0.3s ease',
  } as const,
  successMessage: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    padding: '14px 16px',
    backgroundColor: 'var(--status-success-bg)',
    border: '1px solid var(--status-success)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--status-success)',
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '24px',
    animation: 'slideDown 0.3s ease',
  } as const,
  footer: {
    marginTop: '32px',
    paddingTop: '24px',
    borderTop: '1px solid var(--border-subtle)',
    textAlign: 'center' as const,
  } as const,
  footerText: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
  } as const,
  apiCode: {
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-primary)',
    backgroundColor: 'var(--surface-tertiary)',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
  } as const,
};

export default LoginPage;
