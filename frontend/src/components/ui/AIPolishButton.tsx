import React, { useState, useCallback } from 'react';
import { api } from '../../services/api';

interface AIPolishButtonProps {
  text: string;
  onPolished: (text: string) => void;
}

const AI_GRADIENT = 'linear-gradient(135deg, #7c3aed, #6366f1)';
const AI_GRADIENT_HOVER = 'linear-gradient(135deg, #8b5cf6, #818cf8)';

const AIPolishButton: React.FC<AIPolishButtonProps> = ({ text, onPolished }) => {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [hover, setHover] = useState(false);

  const handleClick = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    setLoading(true);
    setStatus('idle');
    try {
      const polished = await api.aiPolish(text);
      onPolished(polished);
      setStatus('success');
      setTimeout(() => setStatus('idle'), 2000);
    } catch {
      setStatus('error');
      setTimeout(() => setStatus('idle'), 3000);
    } finally {
      setLoading(false);
    }
  }, [text, onPolished]);

  const label = status === 'success' ? '✓ 已润色'
    : status === 'error' ? '✗ 失败'
    : 'AI润色';

  const isActive = status === 'success' || status === 'error';

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={loading || !text.trim()}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        ...styles.btn,
        ...(isActive ? {} : {
          background: hover ? AI_GRADIENT_HOVER : AI_GRADIENT,
          boxShadow: hover
            ? '0 2px 8px rgba(124, 58, 237, 0.35)'
            : '0 1px 3px rgba(124, 58, 237, 0.2)',
        }),
        ...(loading ? styles.loading : {}),
        ...(status === 'success' ? styles.success : {}),
        ...(status === 'error' ? styles.error : {}),
      }}
      title="使用 AI 润色此段文本"
    >
      {loading ? (
        <span style={styles.spinner} />
      ) : (
        <span style={styles.icon}>✦</span>
      )}
      <span>{label}</span>
    </button>
  );
};

const styles: Record<string, React.CSSProperties> = {
  btn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '4px 10px',
    fontSize: 11,
    fontWeight: 600,
    border: 'none',
    borderRadius: 6,
    color: '#fff',
    cursor: 'pointer',
    transition: 'all 0.2s',
    lineHeight: 1.3,
    letterSpacing: '0.3px',
  },
  loading: {
    opacity: 0.7,
    cursor: 'wait',
    background: 'linear-gradient(135deg, #7c3aed, #6366f1)',
    boxShadow: '0 1px 3px rgba(124, 58, 237, 0.2)',
  },
  success: {
    background: '#16a34a',
    boxShadow: '0 1px 3px rgba(22, 163, 74, 0.25)',
    color: '#fff',
  },
  error: {
    background: '#dc2626',
    boxShadow: '0 1px 3px rgba(220, 38, 38, 0.25)',
    color: '#fff',
  },
  icon: {
    fontSize: 14,
    lineHeight: 1,
    filter: 'drop-shadow(0 0 2px rgba(255,255,255,0.3))',
  },
  spinner: {
    display: 'inline-block',
    width: 10,
    height: 10,
    border: '2px solid rgba(255,255,255,0.4)',
    borderTopColor: '#fff',
    borderRadius: '50%',
    animation: 'spin 0.6s linear infinite',
  },
};

export default AIPolishButton;
