/**
 * PlanDetailView + StatusBoard + StatusCard + ComponentBoard + DataTable
 * Display components for the test plan page.
 * Extracted from the original TestExecutionPlanDemo.tsx.
 */
import { useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/select';
import type { UserResponse } from '../../types';
import type { PlanSummary, PlanItemSummary, ViewMode, ItemStatus } from './types';
import { STATUS, STATUS_META, PLAN_STATUS_META, PRIORITY_COLORS, RERUNNABLE_STATUSES } from './types';

// ═══════════════════════════════════════════════════════════════════
//  PlanDetailView
// ═══════════════════════════════════════════════════════════════════

interface PlanDetailViewProps {
  plan: PlanSummary;
  items: PlanItemSummary[];
  viewMode: ViewMode;
  onViewModeChange: (m: ViewMode) => void;
  isEditing: boolean;
  onStartEditing: () => void;
  onCancelEditing: () => void;
  onSaveEditing: () => void;
  onRemoveItem: (itemId: string) => void;
  saving: boolean;
  onShowAddCases: () => void;
  users: UserResponse[];
  onRerunItem?: (item: PlanItemSummary) => void;
  onViewResult?: (item: PlanItemSummary) => void;
  onBatchAssign?: (itemIds: string[], assigneeId: string) => void;
  onTerminateItem?: (planId: string, itemId: string) => void;
  onDeleteItem?: (planId: string, itemId: string) => void;
  onDeletePlan?: (planId: string) => void;
  onUpdateItemAssignee?: (itemId: string, assigneeId: string) => void;
}

export function PlanDetailView(props: PlanDetailViewProps) {
  const { plan, items, viewMode, onViewModeChange, isEditing, onStartEditing, onCancelEditing, onSaveEditing, onRemoveItem, saving, onShowAddCases, users, onViewResult, onRerunItem, onBatchAssign, onTerminateItem, onDeleteItem, onDeletePlan, onUpdateItemAssignee } = props;
  const meta = PLAN_STATUS_META[plan.status] || { label: plan.status, color: 'var(--text-tertiary)' };

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
        <Badge variant={plan.status === 'active' ? 'success' : 'secondary'}>{meta.label}</Badge>
        <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{plan.start_date || '-'} 至 {plan.end_date || '-'}</span>
        <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>进度 {plan.progress_percent ?? 0}% ({plan.done_count}/{plan.item_count})</span>
        <div style={{ width: 60, height: 3, background: 'var(--surface-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${plan.progress_percent ?? 0}%`, height: '100%', background: plan.status === 'active' ? 'var(--accent-primary)' : 'var(--text-tertiary)', borderRadius: 2 }} />
        </div>
        <div className="flex gap-1 text-[10px]">
          {([['pending', '待执行', 'var(--text-tertiary)'], ['running', '执行中', 'var(--accent-primary)'], ['fail', '失败', 'var(--status-error)'], ['done', '已完成', 'var(--status-success)']] as const).map(([key, label, color]) =>
            statusCounts[key] > 0 && <span key={key} style={{ padding: '1px 5px', borderRadius: 4, background: `${color}12`, color, fontWeight: 600 }}>{label}: {statusCounts[key]}</span>
          )}
        </div>
        <div style={{ flex: 1 }} />
        {isEditing ? (
          <div className="flex gap-1.5">
            <button className="btn btn--ghost btn--sm" onClick={onCancelEditing} disabled={saving} style={{ fontSize: 12 }}>取消</button>
            <button className="btn btn--primary btn--sm" onClick={() => onSaveEditing()} disabled={saving} style={{ fontSize: 12 }}>{saving ? '保存中...' : '保存更改'}</button>
          </div>
        ) : (
          <div className="flex gap-1.5">
            <button className="btn btn--ghost btn--sm" onClick={onStartEditing} style={{ fontSize: 12 }}>编辑</button>
            {onDeletePlan && <button className="btn btn--ghost btn--sm" onClick={() => onDeletePlan(plan.plan_id)} style={{ fontSize: 12, color: 'var(--status-error)' }}>删除</button>}
          </div>
        )}
      </div>

      {/* View switcher */}
      <div className="flex items-center gap-1 mb-2.5 flex-shrink-0">
        {([{ key: 'statusBoard' as ViewMode, label: '状态看板' }, { key: 'listView' as ViewMode, label: '列表' }]).map(v => (
          <button key={v.key} onClick={() => onViewModeChange(v.key)}
            style={{ padding: '4px 12px', fontSize: 12, border: '1px solid var(--border-subtle)', borderRadius: 6, cursor: 'pointer', background: viewMode === v.key ? 'var(--accent-primary)' : 'var(--surface-primary)', color: viewMode === v.key ? '#fff' : 'var(--text-secondary)', fontWeight: viewMode === v.key ? 600 : 400 }}>
            {v.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        {isEditing && <button className="btn btn--ghost btn--sm" onClick={onShowAddCases} style={{ fontSize: 12 }}>+ 添加用例</button>}
      </div>

      {/* View content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {items.length === 0 ? (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', gap: 6 }}>
            <span style={{ fontSize: 13 }}>该计划暂无条目</span>
            {isEditing && <button className="btn btn--ghost btn--sm" onClick={onShowAddCases} style={{ fontSize: 12 }}>添加用例</button>}
          </div>
        ) : viewMode === 'statusBoard' ? (
          <StatusBoard items={items} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} onRerunItem={onRerunItem} onTerminateItem={onTerminateItem} onDeleteItem={onDeleteItem} onUpdateItemAssignee={onUpdateItemAssignee} />
        ) : (
          <DataTable items={items} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} onRerunItem={onRerunItem} onBatchAssign={onBatchAssign} onTerminateItem={onTerminateItem} onDeleteItem={onDeleteItem} onUpdateItemAssignee={onUpdateItemAssignee} />
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  StatusBoard
// ═══════════════════════════════════════════════════════════════════

interface ItemActions {
  isEditing?: boolean;
  onRemoveItem?: (itemId: string) => void;
  users: UserResponse[];
  onViewResult?: (item: PlanItemSummary) => void;
  onRerunItem?: (item: PlanItemSummary) => void;
  onTerminateItem?: (planId: string, itemId: string) => void;
  onDeleteItem?: (planId: string, itemId: string) => void;
  onUpdateItemAssignee?: (itemId: string, assigneeId: string) => void;
}

function StatusBoard({ items, ...actions }: { items: PlanItemSummary[] } & ItemActions) {
  const groups = useMemo(() => {
    const map = new Map<string, PlanItemSummary[]>();
    for (const s of STATUS) map.set(s, []);
    for (const item of items) {
      const key = STATUS.includes(item.status as ItemStatus) ? item.status : 'pending';
      map.get(key)!.push(item);
    }
    return Array.from(map.entries());
  }, [items]);

  return (
    <div style={{ height: '100%', display: 'flex', gap: 10, overflow: 'auto' }}>
      {groups.map(([status, caseItems]) => {
        const meta = STATUS_META[status as ItemStatus] || { label: status, color: 'var(--text-tertiary)', bg: 'var(--surface-tertiary)' };
        return (
          <div key={status} style={{ flex: 1, minWidth: 200, display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', marginBottom: 6, borderRadius: 6, background: meta.bg }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: meta.color }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: meta.color }}>{meta.label}</span>
              <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginLeft: 'auto' }}>{caseItems.length}</span>
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4, overflowY: 'auto' }}>
              {caseItems.length === 0 && <div style={{ padding: 12, textAlign: 'center', fontSize: 11, color: 'var(--text-tertiary)', border: '1px dashed var(--border-subtle)', borderRadius: 8 }}>-</div>}
              {caseItems.map(item => <StatusCard key={item.item_id} item={item} {...actions} />)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  StatusCard
// ═══════════════════════════════════════════════════════════════════

function StatusCard({ item, ...actions }: { item: PlanItemSummary } & ItemActions) {
  const { isEditing, onRemoveItem, users, onViewResult, onRerunItem, onUpdateItemAssignee } = actions;
  const meta = STATUS_META[item.status as ItemStatus] || STATUS_META.pending;
  const isAuto = item.ref_type === 'auto';
  const [showAssigneePicker, setShowAssigneePicker] = useState(false);

  return (
    <div style={{ padding: '8px 10px', borderRadius: 6, background: 'var(--surface-primary)', border: `1px solid ${meta.color}20`, borderLeft: `3px solid ${meta.color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
        <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{item.case_id}</span>
        {isEditing && onRemoveItem && <span onClick={(e) => { e.stopPropagation(); onRemoveItem(item.item_id); }} style={{ fontSize: 12, cursor: 'pointer', color: 'var(--text-tertiary)', opacity: 0.4 }}>x</span>}
      </div>
      <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, lineHeight: 1.4 }}>{item.case_title}</div>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
        <Badge variant={isAuto ? 'info' : 'secondary'}>{isAuto ? 'AUTO' : 'MANUAL'}</Badge>
        <span style={{ fontSize: 9, color: PRIORITY_COLORS[item.priority] || 'var(--text-tertiary)', fontWeight: 600 }}>{item.priority}</span>
        {isEditing && onUpdateItemAssignee ? (
          showAssigneePicker ? (
            <Select value={item.assignee_id || ''} onChange={e => { onUpdateItemAssignee(item.item_id, e.target.value); setShowAssigneePicker(false); }} className="w-[120px] text-[9px]" autoFocus>
              <option value="">未指派</option>
              {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
            </Select>
          ) : (
            <span onClick={() => setShowAssigneePicker(true)} style={{ fontSize: 9, color: 'var(--accent-primary)', cursor: 'pointer', textDecoration: 'underline dotted' }}>
              {item.assignee_id ? (users.find(u => u.user_id === item.assignee_id)?.username || item.assignee_id) : '+ 指派'}
            </span>
          )
        ) : item.assignee_id && <span style={{ fontSize: 9, color: 'var(--text-tertiary)' }}>{users.find(u => u.user_id === item.assignee_id)?.username || item.assignee_id}</span>}
        {item.result && <Badge variant={item.result.passed ? 'success' : 'destructive'}>{item.result.passed ? '通过' : '失败'}</Badge>}
        {(item.execution_task_id || item.result) && onViewResult && (
          <button type="button" onClick={(e) => { e.stopPropagation(); onViewResult(item); }} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)', color: 'var(--accent-primary)', cursor: 'pointer', marginLeft: 'auto' }}>结果</button>
        )}
        {RERUNNABLE_STATUSES.includes(item.status) && onRerunItem && (
          <button type="button" onClick={(e) => { e.stopPropagation(); onRerunItem(item); }} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, border: '1px solid rgba(220,38,38,0.25)', color: 'var(--status-error)', background: 'var(--status-error-bg)', cursor: 'pointer' }}>重新执行</button>
        )}
      </div>
      {item.updated_at && <div style={{ fontSize: 9, color: 'var(--text-tertiary)', marginTop: 4, opacity: 0.6 }}>更新: {new Date(item.updated_at).toLocaleString('zh-CN')}</div>}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  DataTable
// ═══════════════════════════════════════════════════════════════════

function DataTable({ items, ...actions }: { items: PlanItemSummary[] } & ItemActions & { onBatchAssign?: (itemIds: string[], assigneeId: string) => void }) {
  const { isEditing, onRemoveItem, users, onViewResult, onRerunItem, onBatchAssign, onUpdateItemAssignee } = actions;
  const [selectedItemIds, setSelectedItemIds] = useState<Set<string>>(new Set());
  const [batchAssigneeId, setBatchAssigneeId] = useState('');

  const handleSelectAll = () => setSelectedItemIds(selectedItemIds.size === items.length ? new Set() : new Set(items.map(i => i.item_id)));
  const handleSelectItem = (itemId: string) => { const s = new Set(selectedItemIds); s.has(itemId) ? s.delete(itemId) : s.add(itemId); setSelectedItemIds(s); };
  const handleBatchAssign = () => { if (onBatchAssign && selectedItemIds.size > 0 && batchAssigneeId) { onBatchAssign(Array.from(selectedItemIds), batchAssigneeId); setSelectedItemIds(new Set()); setBatchAssigneeId(''); } };

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      {isEditing && (
        <div className="flex items-center gap-2.5 px-3 py-2 mb-2 bg-[var(--surface-primary)] rounded-md border border-[var(--border-subtle)]">
          <span className="text-[11px] text-[var(--text-tertiary)]">已选 {selectedItemIds.size} 条</span>
          <button onClick={() => setSelectedItemIds(new Set(items.filter(i => !i.assignee_id).map(i => i.item_id)))} className="text-[11px] px-2 py-0.5 rounded border border-[var(--border-subtle)] bg-transparent text-[var(--text-secondary)] cursor-pointer">选中无执行人</button>
          <Select value={batchAssigneeId} onChange={e => setBatchAssigneeId(e.target.value)} className="w-[140px] text-[11px]">
            <option value="">选择执行人</option>
            {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
          </Select>
          <button onClick={handleBatchAssign} disabled={selectedItemIds.size === 0 || !batchAssigneeId} style={{ fontSize: 11, padding: '2px 12px', borderRadius: 4, border: 'none', background: selectedItemIds.size > 0 && batchAssigneeId ? 'var(--accent-primary)' : 'var(--surface-tertiary)', color: selectedItemIds.size > 0 && batchAssigneeId ? '#fff' : 'var(--text-tertiary)', cursor: selectedItemIds.size > 0 && batchAssigneeId ? 'pointer' : 'not-allowed' }}>指派</button>
          {selectedItemIds.size > 0 && <button onClick={() => setSelectedItemIds(new Set())} className="text-[11px] px-2 py-0.5 rounded border-none bg-transparent text-[var(--text-tertiary)] cursor-pointer">清除</button>}
        </div>
      )}
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: 'var(--surface-primary)', position: 'sticky', top: 0, zIndex: 1 }}>
            {isEditing && <th style={{ padding: '8px 12px', textAlign: 'center', width: 40, borderBottom: '1px solid var(--border-subtle)' }}><input type="checkbox" checked={items.length > 0 && selectedItemIds.size === items.length} onChange={handleSelectAll} style={{ cursor: 'pointer' }} /></th>}
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>用例</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>类型</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>优先级</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>执行人</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>状态</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>更新时间</th>
            <th style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>结果</th>
            {isEditing && <th style={{ padding: '8px 12px', textAlign: 'center', width: 30, borderBottom: '1px solid var(--border-subtle)' }}></th>}
          </tr>
        </thead>
        <tbody>
          {items.map(item => {
            const statusMeta = STATUS_META[item.status as ItemStatus] || STATUS_META.pending;
            const isSelected = selectedItemIds.has(item.item_id);
            return (
              <tr key={item.item_id} style={{ borderBottom: '1px solid var(--border-subtle)', background: isSelected ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'transparent' }}>
                {isEditing && <td style={{ padding: '7px 12px', textAlign: 'center' }}><input type="checkbox" checked={isSelected} onChange={() => handleSelectItem(item.item_id)} style={{ cursor: 'pointer' }} /></td>}
                <td style={{ padding: '7px 12px' }}>
                  <div style={{ fontWeight: 500 }}>{item.case_title}</div>
                  <div style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{item.case_id}</div>
                </td>
                <td style={{ padding: '7px 12px' }}><Badge variant={item.ref_type === 'auto' ? 'info' : 'secondary'}>{item.ref_type === 'auto' ? 'AUTO' : 'MANUAL'}</Badge></td>
                <td style={{ padding: '7px 12px', color: PRIORITY_COLORS[item.priority] || 'var(--text-tertiary)', fontWeight: 600 }}>{item.priority}</td>
                <td style={{ padding: '7px 12px', color: 'var(--text-secondary)' }}>
                  {isEditing && onUpdateItemAssignee ? (
                    <Select value={item.assignee_id || ''} onChange={e => onUpdateItemAssignee(item.item_id, e.target.value)} className="w-[110px] text-[11px]" >
                      <option value="">未指派</option>
                      {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                    </Select>
                  ) : item.assignee_id ? (users.find(u => u.user_id === item.assignee_id)?.username || item.assignee_id) : <span style={{ color: 'var(--status-warning)', fontSize: 10 }}>未指派</span>}
                </td>
                <td style={{ padding: '7px 12px' }}><span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: `${statusMeta.color}15`, color: statusMeta.color, fontWeight: 600 }}>{statusMeta.label}</span></td>
                <td style={{ padding: '7px 12px', fontSize: 10, color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>{item.updated_at ? new Date(item.updated_at).toLocaleString('zh-CN') : '-'}</td>
                <td style={{ padding: '7px 12px', textAlign: 'center' }}>
                  {item.result && <Badge variant={item.result.passed ? 'success' : 'destructive'}>{item.result.passed ? '通过' : '失败'}</Badge>}
                  {(item.execution_task_id || item.result) && onViewResult ? (
                    <button type="button" onClick={(e) => { e.stopPropagation(); onViewResult(item); }} style={{ fontSize: 10, padding: '2px 10px', borderRadius: 4, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)', color: 'var(--accent-primary)', cursor: 'pointer' }}>详情</button>
                  ) : <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>-</span>}
                  {RERUNNABLE_STATUSES.includes(item.status) && onRerunItem && (
                    <button type="button" onClick={(e) => { e.stopPropagation(); onRerunItem(item); }} style={{ fontSize: 10, padding: '2px 10px', borderRadius: 4, marginLeft: 4, border: '1px solid rgba(220,38,38,0.25)', color: 'var(--status-error)', background: 'var(--status-error-bg)', cursor: 'pointer' }}>重新执行</button>
                  )}
                </td>
                {isEditing && onRemoveItem && <td style={{ padding: '7px 12px', textAlign: 'center' }}><span onClick={() => onRemoveItem(item.item_id)} style={{ fontSize: 12, cursor: 'pointer', color: 'var(--text-tertiary)', opacity: 0.4 }}>x</span></td>}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
