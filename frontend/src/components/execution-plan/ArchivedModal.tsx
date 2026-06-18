/**
 * ArchivedModal - 已归档条目弹窗
 */
import type { ArchivedModalProps, PlanItemSummary } from './types';

const RERUNNABLE_STATUSES = ['fail', 'done'];

export default function ArchivedModal({ open, loading, items, onClose, onUnarchive, onRerunItem }: ArchivedModalProps) {
  if (!open) return null;
  const typedItems = items as PlanItemSummary[];
  const doneCount = typedItems.filter((i: PlanItemSummary) => i.status === 'done').length;
  const failCount = typedItems.filter((i: PlanItemSummary) => i.status === 'fail').length;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg-elevated)', borderRadius: 12, width: 620, maxWidth: '94vw',
          maxHeight: '80vh', display: 'flex', flexDirection: 'column',
          boxShadow: '0 30px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)',
        }}
      >
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>已归档条目</div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{items.length} 条记录</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {doneCount > 0 && (
              <div style={{ padding: '3px 8px', borderRadius: 6, background: 'rgba(63,185,80,0.1)', fontSize: 10, color: '#3fb950', fontWeight: 600 }}>
                已完成 {doneCount}
              </div>
            )}
            {failCount > 0 && (
              <div style={{ padding: '3px 8px', borderRadius: 6, background: 'rgba(248,81,73,0.1)', fontSize: 10, color: '#f85149', fontWeight: 600 }}>
                失败 {failCount}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            x
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {loading ? (
            <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>加载中...</div>
          ) : items.length === 0 ? (
            <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
              暂无已归档条目
              <div style={{ fontSize: 11, marginTop: 4 }}>已完成的任务会自动归档到这里</div>
            </div>
          ) : (
            typedItems.map((item: PlanItemSummary & { plan_title?: string }) => (
              <div
                key={item.item_id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                  borderRadius: 6, border: '1px solid var(--border-subtle)', background: 'var(--bg-primary)', fontSize: 12,
                }}
              >
                <div
                  style={{
                    width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                    background: item.status === 'done' ? '#3fb950' : item.status === 'fail' ? '#f85149' : '#8b949e',
                  }}
                />
                <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', flexShrink: 0 }}>
                  {item.case_id}
                </span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                  {item.case_title}
                </span>
                <span style={{ fontSize: 10, color: 'var(--text-secondary)', flexShrink: 0 }}>
                  {item.plan_title}
                </span>
                <span
                  style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 4, flexShrink: 0, fontWeight: 600,
                    color: item.status === 'done' ? '#3fb950' : item.status === 'fail' ? '#f85149' : '#8b949e',
                    background: item.status === 'done' ? 'rgba(63,185,80,0.12)' : item.status === 'fail' ? 'rgba(248,81,73,0.12)' : 'rgba(139,148,158,0.12)',
                  }}
                >
                  {item.status === 'done' ? '已完成' : item.status === 'fail' ? '失败' : item.status}
                </span>
                <button
                  onClick={() => onUnarchive(item.item_id)}
                  style={{
                    padding: '3px 10px', fontSize: 10, border: 'none', borderRadius: 4, cursor: 'pointer',
                    background: 'var(--surface-secondary)', color: 'var(--text-secondary)', fontWeight: 500, flexShrink: 0,
                  }}
                >
                  取回
                </button>
                {RERUNNABLE_STATUSES.includes(item.status) && onRerunItem && (
                  <button
                    onClick={() => onRerunItem(item)}
                    style={{
                      padding: '3px 10px', fontSize: 10, border: '1px solid #f8514940', borderRadius: 4, cursor: 'pointer',
                      background: 'rgba(248,81,73,0.06)', color: '#f85149', fontWeight: 500, flexShrink: 0,
                    }}
                  >
                    重新执行
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}