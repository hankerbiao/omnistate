import type { ReactNode } from 'react';

interface PageToolbarProps {
  /** 左侧：统计、筛选摘要等 */
  meta?: ReactNode;
  /** 右侧：主操作按钮 */
  actions?: ReactNode;
  className?: string;
}

/**
 * 页面级工具栏：与 Topbar 标题配合，避免重复大标题，集中放统计与操作。
 */
const PageToolbar: React.FC<PageToolbarProps> = ({ meta, actions, className = '' }) => {
  return (
    <div className={`page-toolbar ${className}`.trim()}>
      <div className="page-toolbar__meta">{meta}</div>
      {actions && <div className="page-toolbar__actions">{actions}</div>}
    </div>
  );
};

interface StatPillProps {
  label: string;
  value: string | number;
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  dot?: boolean;
  pulse?: boolean;
}

export const StatPill: React.FC<StatPillProps> = ({
  label,
  value,
  tone = 'default',
  dot = false,
  pulse = false,
}) => (
  <span className={`stat-pill stat-pill--${tone}`}>
    {dot && <span className={`stat-pill__dot${pulse ? ' stat-pill__dot--pulse' : ''}`} />}
    <span className="stat-pill__label">{label}</span>
    <span className="stat-pill__value">{value}</span>
  </span>
);

export default PageToolbar;
