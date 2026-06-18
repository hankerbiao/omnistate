/**
 * ComponentBoard - 按组件分栏视图
 */
import { useMemo, useState } from 'react';
import type { ComponentBoardProps, ItemStatus, PlanItemSummary } from './types';

const PRIORITY_COLORS: Record<string, string> = {
  P0: '#f85149', P1: '#d29922', P2: '#58a6ff', P3: '#8b949e',
};

const STATUS_META: Record<ItemStatus, { label: string; color: string; bg: string }> = {
  pending: { label: '待执行', color: '#8b949e', bg: 'rgba(139,148,158,0.08)' },
  running: { label: '执行中', color: '#58a6ff', bg: 'rgba(88,166,255,0.08)' },
  fail: { label: '失败', color: '#f85149', bg: 'rgba(248,81,73,0.08)' },
  done: { label: '已完成', color: '#3fb950', bg: 'rgba(63,185,80,0.08)' },
};

function ComponentStatusCard({
  item, isEditing, onRemoveItem, users, onViewResult
}: {
  item: PlanItemSummary;
  isEditing?: boolean;
  onRemoveItem?: (itemId: string) => void;
  users: { user_id: string; username: string }[];
  onViewResult?: (item: PlanItemSummary, taskData: unknown, timelineData: unknown) => void;
}) {
  const meta = STATUS_META[item.status as ItemStatus] || STATUS_META.pending;
  const isAuto = item.ref_type === 'auto';

  return (
    <div style={{ padding: '8px 10px', borderRadius: 6, background: 'var(--surface-primary)', border: `1px solid ${meta.color}20`, borderLeft: `3px solid ${meta.color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
        <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{item.case_id}</span>
        {isEditing && onRemoveItem && (
          <span onClick={(e) => { e.stopPropagation(); onRemoveItem(item.item_id); }} style={{ fontSize: 12, cursor: 'pointer', color: 'var(--text-tertiary)', opacity: 0.4 }}>x</span>
        )}
      </div>
      <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, lineHeight: 1.4 }}>{item.case_title}</div>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
        <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: isAuto ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)', color: isAuto ? '#39d0d6' : '#a371f7', fontWeight: 600 }}>
          {isAuto ? 'AUTO' : 'MANUAL'}
        </span>
        <span style={{ fontSize: 9, color: PRIORITY_COLORS[item.priority] || '#8b949e', fontWeight: 600 }}>{item.priority}</span>
        {item.assignee_id && <span style={{ fontSize: 9, color: 'var(--text-tertiary)' }}>{users.find((u) => u.user_id === item.assignee_id)?.username || item.assignee_id}</span>}
        {item.result && (
          <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, color: item.result.passed ? '#3fb950' : '#f85149', background: item.result.passed ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)', fontWeight: 600 }}>
            {item.result.passed ? '通过' : '失败'}
          </span>
        )}
        {(item.execution_task_id || item.result) && onViewResult && (
          <button type="button" onClick={(e) => { e.stopPropagation(); onViewResult(item, {}, {}); }} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)', color: 'var(--accent-primary)', cursor: 'pointer', marginLeft: 'auto' }}>
            结果
          </button>
        )}
      </div>
    </div>
  );
}

export default function ComponentBoard({ items, isEditing, onRemoveItem, users, onViewResult }: ComponentBoardProps) {
  const groups = useMemo(() => {
    const map = new Map<string, PlanItemSummary[]>();
    for (const item of items) {
      const comp = item.component || 'other';
      if (!map.has(comp)) map.set(comp, []);
      map.get(comp)!.push(item);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [items]);

  const compName = (id: string) => id;

  return (
    <div style={{ height: '100%', display: 'flex', gap: 10, overflow: 'auto' }}>
      {groups.map(([compId, caseItems]) => (
        <div key={compId} style={{ minWidth: 240, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', marginBottom: 6, fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
            <span>{compName(compId)}</span>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginLeft: 'auto' }}>{caseItems.length}</span>
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4, overflowY: 'auto' }}>
            {caseItems.map((item) => (
              <ComponentStatusCard key={item.item_id} item={item} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}