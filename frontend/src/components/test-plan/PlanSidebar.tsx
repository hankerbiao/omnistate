/**
 * PlanSidebar — Left sidebar with plan list
 */
import type { PlanSummary } from './types';
import { PLAN_STATUS_META } from './types';

interface PlanSidebarProps {
  plans: PlanSummary[];
  activePlanId: string;
  loading: boolean;
  searchQuery: string;
  onSelect: (id: string) => void;
}

export function PlanSidebar({ plans, activePlanId, loading, searchQuery, onSelect }: PlanSidebarProps) {
  return (
    <div style={{
      width: 280, flexShrink: 0, borderRight: '1px solid var(--border-subtle)',
      background: 'var(--surface-primary)', display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
        计划列表
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: 20, textAlign: 'center', fontSize: 12, color: 'var(--text-tertiary)' }}>加载中...</div>
        ) : plans.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
              {searchQuery ? '没有匹配的计划' : '暂无执行计划'}
            </div>
            {searchQuery && (
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>尝试更换搜索关键词</div>
            )}
          </div>
        ) : (
          plans.map(p => {
            const isActive = p.plan_id === activePlanId;
            const meta = PLAN_STATUS_META[p.status] || { label: p.status, color: 'var(--text-tertiary)' };
            return (
              <div key={p.plan_id} onClick={() => onSelect(p.plan_id)}
                style={{
                  padding: '10px 14px', cursor: 'pointer', borderBottom: '1px solid var(--border-subtle)',
                  background: isActive ? 'color-mix(in srgb, var(--accent-primary) 8%, transparent)' : 'transparent',
                  borderLeft: isActive ? '3px solid var(--accent-primary)' : '3px solid transparent',
                }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{p.title}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                  {p.start_date || '-'} 至 {p.end_date || '-'}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                  <div style={{ flex: 1, height: 3, background: 'var(--surface-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      width: `${p.progress_percent ?? 0}%`, height: '100%',
                      background: p.status === 'active' ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                      borderRadius: 2, transition: 'width 0.3s',
                    }} />
                  </div>
                  <span style={{ fontSize: 10, color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
                    {p.done_count}/{p.item_count}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
