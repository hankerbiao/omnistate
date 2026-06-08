import type { ReactNode } from 'react';

interface DetailHeaderProps {
  id?: string;
  badges?: ReactNode;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export const DetailHeader: React.FC<DetailHeaderProps> = ({
  id,
  badges,
  title,
  subtitle,
  actions,
}) => (
  <div className="split-detail-header">
    <div className="split-detail-header__info">
      {(id || badges) && (
        <div className="split-detail-header__meta">
          {id && <span className="split-detail-header__id">{id}</span>}
          {badges}
        </div>
      )}
      <h2 className="split-detail-header__title">{title}</h2>
      {subtitle && <p className="split-detail-header__subtitle">{subtitle}</p>}
    </div>
    {actions && <div className="split-detail-header__actions">{actions}</div>}
  </div>
);

interface DetailStatProps {
  label: string;
  value: string | number;
  hint?: string;
}

export const DetailStatGrid: React.FC<{ stats: DetailStatProps[] }> = ({ stats }) => (
  <div className="split-detail-stats">
    {stats.map(stat => (
      <div key={stat.label} className="split-detail-stats__item">
        <div className="split-detail-stats__value">{stat.value}</div>
        <div className="split-detail-stats__label">{stat.label}</div>
        {stat.hint && <div className="split-detail-stats__hint">{stat.hint}</div>}
      </div>
    ))}
  </div>
);

interface DetailSectionProps {
  title: string;
  hint?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export const DetailSection: React.FC<DetailSectionProps> = ({
  title,
  hint,
  actions,
  children,
}) => (
  <section className="split-detail-section">
    <div className="split-detail-section__header">
      <div>
        <h3 className="split-detail-section__title">{title}</h3>
        {hint && <span className="split-detail-section__hint">{hint}</span>}
      </div>
      {actions}
    </div>
    <div className="split-detail-section__body">{children}</div>
  </section>
);

interface DetailTagListProps {
  items: { key: string; label: string }[];
  emptyText?: string;
  loading?: boolean;
  max?: number;
}

export const DetailTagList: React.FC<DetailTagListProps> = ({
  items,
  emptyText = '暂无数据',
  loading = false,
  max = 30,
}) => {
  if (loading) {
    return <p className="split-detail-empty-text">加载中...</p>;
  }
  if (items.length === 0) {
    return <p className="split-detail-empty-text">{emptyText}</p>;
  }
  const visible = items.slice(0, max);
  const overflow = items.length - max;
  return (
    <div className="split-detail-tags">
      {visible.map(item => (
        <span key={item.key} className="split-detail-tags__item">{item.label}</span>
      ))}
      {overflow > 0 && (
        <span className="split-detail-tags__overflow">+{overflow}</span>
      )}
    </div>
  );
};

export const DetailEmpty: React.FC<{ icon?: string; text: string }> = ({
  icon = '👈',
  text,
}) => (
  <div className="empty-state" style={{ height: '100%' }}>
    <div className="empty-state__icon">{icon}</div>
    <p className="empty-state__text">{text}</p>
  </div>
);

export const DetailMetaRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="split-detail-meta-row">
    <span className="split-detail-meta-row__label">{label}</span>
    <span className="split-detail-meta-row__value">{value}</span>
  </div>
);
