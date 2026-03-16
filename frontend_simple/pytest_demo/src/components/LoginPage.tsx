import { useState } from 'react';
import { api } from '../services/api';
import type { LoginRequest } from '../types';

interface LoginPageProps {
  onLoginSuccess?: () => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [formData, setFormData] = useState<LoginRequest>({
    user_id: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await api.login(formData);
      console.log('Login successful:', response);

      const token = response.data.access_token;
      localStorage.setItem('jwt_token', token);
      api.setToken(token);

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
          <div style={styles.logoIcon}>⬢</div>
          <h1 style={styles.title}>TestHub</h1>
          <p style={styles.subtitle}>测试管理平台</p>
        </div>

        {success && (
          <div style={styles.successMessage}>
            <span style={styles.successIcon}>✓</span>
            登录成功
          </div>
        )}

        {error && (
          <div style={styles.errorMessage}>
            <span style={styles.errorIcon}>⚠</span>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputGroup}>
            <label htmlFor="user_id" style={styles.label}>
              <span style={styles.labelIcon}>◉</span>
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
              <span style={styles.labelIcon}>◈</span>
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
                <span style={styles.spinner} />
                登录中...
              </>
            ) : (
              <>
                <span style={styles.buttonIcon}>→</span>
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
    backgroundImage: `
      radial-gradient(circle at 1px 1px, var(--border-default) 1px, transparent 0)
    `,
    backgroundSize: '40px 40px',
    opacity: 0.5,
  } as const,
  glowOrb1: {
    position: 'absolute',
    top: '10%',
    left: '20%',
    width: '400px',
    height: '400px',
    background: 'radial-gradient(circle, rgba(57, 208, 214, 0.15) 0%, transparent 70%)',
    filter: 'blur(60px)',
    pointerEvents: 'none',
  } as const,
  glowOrb2: {
    position: 'absolute',
    bottom: '10%',
    right: '20%',
    width: '300px',
    height: '300px',
    background: 'radial-gradient(circle, rgba(88, 166, 255, 0.12) 0%, transparent 70%)',
    filter: 'blur(60px)',
    pointerEvents: 'none',
  } as const,
  card: {
    position: 'relative',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
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
  logoIcon: {
    fontSize: '48px',
    color: 'var(--accent-cyan)',
    filter: 'drop-shadow(0 0 20px rgba(57, 208, 214, 0.6))',
    display: 'block',
    marginBottom: '12px',
    animation: 'pulse 3s ease-in-out infinite',
  } as const,
  title: {
    fontSize: '32px',
    fontWeight: 700,
    letterSpacing: '-1px',
    background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
    margin: 0,
  } as const,
  subtitle: {
    fontSize: '14px',
    color: 'var(--text-muted)',
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
  labelIcon: {
    color: 'var(--accent-cyan)',
    fontSize: '12px',
  } as const,
  input: {
    width: '100%',
    padding: '14px 16px',
    fontSize: '15px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
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
    color: 'var(--bg-primary)',
    background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
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
  buttonIcon: {
    fontSize: '16px',
    transition: 'transform var(--transition-fast)',
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
    color: 'var(--accent-red)',
    fontSize: '14px',
    marginBottom: '24px',
    animation: 'slideDown 0.3s ease',
  } as const,
  errorIcon: {
    fontSize: '16px',
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
    color: 'var(--accent-green)',
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '24px',
    animation: 'slideDown 0.3s ease',
  } as const,
  successIcon: {
    fontSize: '16px',
    fontWeight: 'bold',
  } as const,
  footer: {
    marginTop: '32px',
    paddingTop: '24px',
    borderTop: '1px solid var(--border-muted)',
    textAlign: 'center' as const,
  } as const,
  footerText: {
    fontSize: '12px',
    color: 'var(--text-muted)',
  } as const,
  apiCode: {
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-cyan)',
    backgroundColor: 'var(--bg-tertiary)',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
  } as const,
};

export default LoginPage;