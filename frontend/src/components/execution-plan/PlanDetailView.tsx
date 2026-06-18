/**
 * PlanDetailView - 右侧计划详情 + 视图切换
 */
import { useMemo } from 'react';
import StatusBoard from './StatusBoard';
import ComponentBoard from './ComponentBoard';
import DataTable from './DataTable';
import type { PlanDetailViewProps, ViewMode, ItemStatus } from './types';

const STATUS = ['pending', 'running', 'fail', 'done'] as const;
const PLAN_STATUS_META: Record<string, { label: string; color: string }> = {
  active: { label: '进行中', color: '#3fb950' },
  done: { label: '已完成', color: '#8b949e' },
};

export default function PlanDetailView({
  plan, items, viewMode, onViewModeChange, isEditing,
  onStartEditing, onCancelEditing, onSaveEditing, onRemoveItem, saving,
  onShowAddCases, users, onViewResult, onRerunItem, onBatchAssign,
  onTerminateItem, onDeleteItem, onDeletePlan, onUpdateItemAssignee,
}: PlanDetailViewProps) {
  const meta = PLAN_STATUS_META[plan.status] || { label: plan.status, color: '#8b949e' };

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { pending: 0, running: 0, fail: 0, done: 0 };
    for (const item of items) {
      const key = STATUS.includes(item.status as ItemStatus) ? item.status : 'pending';
      counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
  }, [items]);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '16px 20px' }}>
      {/* Plan header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', background: 'var(--surface-primary)', borderRadius: 8, border: '1px solid var(--border-subtle)', flexShrink: 0, marginBottom: 12 }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>{plan.title}</span>
        <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: `${meta.color}18`, color: meta.color, fontWeight: 600 }}>
          {meta.label}
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
          {plan.start_date || '-'} 至 {plan.end_date || '-'}
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
          进度 {plan.progress_percent ?? 0}% ({plan.done_count}/{plan.item_count})
        </span>
        <div style={{ width: 60, height: 3, background: 'var(--surface-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${plan.progress_percent ?? 0}%`, height: '100%', background: plan.status === 'active' ? 'var(--accent-primary)' : '#8b949e', borderRadius: 2 }} />
        </div>
        <div style={{ display: 'flex', gap: 4, fontSize: 10 }}>
          {([
            { key: 'pending', label: '待执行', color: '#8b949e' },
            { key: 'running', label: '执行中', color: '#58a6ff' },
            { key: 'fail', label: '失败', color: '#f85149' },
            { key: 'done', label: '已完成', color: '#3fb950' },
          ] as const).map((s) => statusCounts[s.key] > 0 && (
            <span key={s.key} style={{ padding: '1px 5px', borderRadius: 4, background: `${s.color}12`, color: s.color, fontWeight: 600 }}>
              {s.label}: {statusCounts[s.key]}
            </span>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        {isEditing ? (
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn btn--ghost btn--sm" onClick={onCancelEditing} disabled={saving} style={{ fontSize: 12 }}>取消</button>
            <button className="btn btn--primary btn--sm" onClick={() => onSaveEditing()} disabled={saving} style={{ fontSize: 12 }}>
              {saving ? '保存中...' : '保存更改'}
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn btn--ghost btn--sm" onClick={onStartEditing} style={{ fontSize: 12 }}>编辑</button>
            <button className="btn btn--ghost btn--sm" onClick={() => onDeletePlan(plan.plan_id)} style={{ fontSize: 12, color: '#f85149' }}>删除</button>
          </div>
        )}
      </div>

      {/* View switcher + add cases (edit mode) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 10, flexShrink: 0 }}>
        {([
          { key: 'statusBoard' as ViewMode, label: '状态看板' },
          { key: 'listView' as ViewMode, label: '列表' },
        ]).map((v) => (
          <button
            key={v.key}
            onClick={() => onViewModeChange(v.key)}
            style={{
              padding: '4px 12px', fontSize: 12, border: '1px solid var(--border-subtle)', borderRadius: 6, cursor: 'pointer',
              background: viewMode === v.key ? 'var(--accent-primary)' : 'var(--surface-primary)',
              color: viewMode === v.key ? '#fff' : 'var(--text-secondary)',
              fontWeight: viewMode === v.key ? 600 : 400,
            }}
          >
            {v.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        {isEditing && (
          <button className="btn btn--ghost btn--sm" onClick={onShowAddCases} style={{ fontSize: 12 }}>
            + 添加用例
          </button>
        )}
      </div>

      {/* View content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {items.length === 0 ? (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', gap: 6 }}>
            <span style={{ fontSize: 13 }}>该计划暂无条目</span>
            {isEditing && (
              <button className="btn btn--ghost btn--sm" onClick={onShowAddCases} style={{ fontSize: 12 }}>添加用例</button>
            )}
          </div>
        ) : viewMode === 'statusBoard' ? (
          <StatusBoard items={items} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} onRerunItem={onRerunItem} onTerminateItem={onTerminateItem} onDeleteItem={onDeleteItem} onUpdateItemAssignee={onUpdateItemAssignee} />
        ) : viewMode === 'componentView' ? (
          <ComponentBoard items={items} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} />
        ) : (
          <DataTable items={items} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} onRerunItem={onRerunItem} onBatchAssign={onBatchAssign} onTerminateItem={onTerminateItem} onDeleteItem={onDeleteItem} onUpdateItemAssignee={onUpdateItemAssignee} />
        )}
      </div>
    </div>
  );
}