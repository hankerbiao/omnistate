/**
 * DataTable - 表格视图（支持批量指派执行人）
 */
import { useState } from 'react';
import type { DataTableProps, ItemStatus, PlanItemSummary } from './types';

const STATUS_META: Record<ItemStatus, { label: string; color: string; bg: string }> = {
  pending: { label: '待执行', color: '#8b949e', bg: 'rgba(139,148,158,0.08)' },
  running: { label: '执行中', color: '#58a6ff', bg: 'rgba(88,166,255,0.08)' },
  fail: { label: '失败', color: '#f85149', bg: 'rgba(248,81,73,0.08)' },
  done: { label: '已完成', color: '#3fb950', bg: 'rgba(63,185,80,0.08)' },
};

const RERUNNABLE_STATUSES = ['fail', 'done'];

const PRIORITY_COLORS: Record<string, string> = {
  P0: '#f85149', P1: '#d29922', P2: '#58a6ff', P3: '#8b949e',
};

export default function DataTable({
  items, isEditing, onRemoveItem, users, onViewResult, onRerunItem, onBatchAssign, onTerminateItem, onDeleteItem, onUpdateItemAssignee,
}: DataTableProps) {
  const [selectedItemIds, setSelectedItemIds] = useState<Set<string>>(new Set());
  const [batchAssigneeId, setBatchAssigneeId] = useState<string>('');

  const handleSelectAll = () => {
    if (selectedItemIds.size === items.length) {
      setSelectedItemIds(new Set());
    } else {
      setSelectedItemIds(new Set(items.map((i) => i.item_id)));
    }
  };

  const handleSelectItem = (itemId: string) => {
    const newSet = new Set(selectedItemIds);
    if (newSet.has(itemId)) {
      newSet.delete(itemId);
    } else {
      newSet.add(itemId);
    }
    setSelectedItemIds(newSet);
  };

  const handleBatchAssign = () => {
    if (onBatchAssign && selectedItemIds.size > 0 && batchAssigneeId) {
      onBatchAssign(Array.from(selectedItemIds), batchAssigneeId);
      setSelectedItemIds(new Set());
      setBatchAssigneeId('');
    }
  };

  const selectUnassigned = () => {
    const unassignedIds = items.filter((i) => !i.assignee_id).map((i) => i.item_id);
    setSelectedItemIds(new Set(unassignedIds));
  };

  const compName = (id: string) => id;

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      {/* 批量操作栏 */}
      {isEditing && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', marginBottom: 8, background: 'var(--surface-primary)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>已选 {selectedItemIds.size} 条</span>
          <button onClick={selectUnassigned} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border-subtle)', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer' }}>选中无执行人</button>
          <select className="form-input form-select" value={batchAssigneeId} onChange={(e) => setBatchAssigneeId(e.target.value)} style={{ width: 140, fontSize: 11 }}>
            <option value="">选择执行人</option>
            {users.map((u) => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
          </select>
          <button onClick={handleBatchAssign} disabled={selectedItemIds.size === 0 || !batchAssigneeId} style={{ fontSize: 11, padding: '2px 12px', borderRadius: 4, border: 'none', background: selectedItemIds.size > 0 && batchAssigneeId ? 'var(--accent-primary)' : 'var(--surface-tertiary)', color: selectedItemIds.size > 0 && batchAssigneeId ? '#fff' : 'var(--text-tertiary)', cursor: selectedItemIds.size > 0 && batchAssigneeId ? 'pointer' : 'not-allowed' }}>
            指派
          </button>
          {selectedItemIds.size > 0 && (
            <button onClick={() => setSelectedItemIds(new Set())} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, border: 'none', background: 'transparent', color: 'var(--text-tertiary)', cursor: 'pointer' }}>
              清除选择
            </button>
          )}
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: 'var(--surface-primary)', position: 'sticky', top: 0, zIndex: 1 }}>
            {isEditing && (
              <th style={{ padding: '8px 12px', textAlign: 'center', width: 40, borderBottom: '1px solid var(--border-subtle)' }}>
                <input type="checkbox" checked={items.length > 0 && selectedItemIds.size === items.length} onChange={handleSelectAll} style={{ cursor: 'pointer' }} />
              </th>
            )}
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>用例</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>类型</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>组件</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>优先级</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>执行人</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>状态</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>更新时间</th>
            <th style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>结果</th>
            {isEditing && <th style={{ padding: '8px 12px', textAlign: 'center', width: 30, borderBottom: '1px solid var(--border-subtle)' }}></th>}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const statusMeta = STATUS_META[item.status as ItemStatus] || STATUS_META.pending;
            const isSelected = selectedItemIds.has(item.item_id);
            return (
              <tr key={item.item_id} style={{ borderBottom: '1px solid var(--border-subtle)', background: isSelected ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'transparent' }}>
                {isEditing && (
                  <td style={{ padding: '7px 12px', textAlign: 'center' }}>
                    <input type="checkbox" checked={isSelected} onChange={() => handleSelectItem(item.item_id)} style={{ cursor: 'pointer' }} />
                  </td>
                )}
                <td style={{ padding: '7px 12px' }}>
                  <div style={{ fontWeight: 500 }}>{item.case_title}</div>
                  <div style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{item.case_id}</div>
                </td>
                <td style={{ padding: '7px 12px' }}>
                  <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: item.ref_type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)', color: item.ref_type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600 }}>
                    {item.ref_type === 'auto' ? 'AUTO' : 'MANUAL'}
                  </span>
                </td>
                <td style={{ padding: '7px 12px', color: 'var(--text-secondary)' }}>{compName(item.component)}</td>
                <td style={{ padding: '7px 12px', color: PRIORITY_COLORS[item.priority] || '#8b949e', fontWeight: 600 }}>{item.priority}</td>
                <td style={{ padding: '7px 12px', color: 'var(--text-secondary)' }}>
                  {isEditing && onUpdateItemAssignee ? (
                    <select className="form-input form-select" value={item.assignee_id || ''} onChange={(e) => onUpdateItemAssignee(item.item_id, e.target.value)} style={{ fontSize: 11, width: 110 }} onClick={(e) => e.stopPropagation()}>
                      <option value="">未指派</option>
                      {users.map((u) => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                    </select>
                  ) : item.assignee_id ? (
                    users.find((u) => u.user_id === item.assignee_id)?.username || item.assignee_id
                  ) : (
                    <span style={{ color: 'var(--status-warn)', fontSize: 10 }}>未指派</span>
                  )}
                </td>
                <td style={{ padding: '7px 12px' }}>
                  <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: `${statusMeta.color}15`, color: statusMeta.color, fontWeight: 600 }}>
                    {statusMeta.label}
                  </span>
                </td>
                <td style={{ padding: '7px 12px', fontSize: 10, color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>{item.updated_at ? new Date(item.updated_at).toLocaleString('zh-CN') : '-'}</td>
                <td style={{ padding: '7px 12px', textAlign: 'center' }}>
                  {item.result && (
                    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, color: item.result.passed ? '#3fb950' : '#f85149', background: item.result.passed ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)', fontWeight: 600, marginRight: 6 }}>
                      {item.result.passed ? '通过' : '失败'}
                    </span>
                  )}
                  {(item.execution_task_id || item.result) && onViewResult ? (
                    <button type="button" onClick={(e) => { e.stopPropagation(); onViewResult(item, {}, {}); }} style={{ fontSize: 10, padding: '2px 10px', borderRadius: 4, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)', color: 'var(--accent-primary)', cursor: 'pointer' }}>
                      详情
                    </button>
                  ) : (
                    <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>-</span>
                  )}
                  {RERUNNABLE_STATUSES.includes(item.status) && onRerunItem && (
                    <button type="button" onClick={(e) => { e.stopPropagation(); onRerunItem(item); }} style={{ fontSize: 10, padding: '2px 10px', borderRadius: 4, marginLeft: 4, border: '1px solid #f8514940', color: '#f85149', background: 'rgba(248,81,73,0.06)', cursor: 'pointer' }}>
                      重新执行
                    </button>
                  )}
                </td>
                {isEditing && onRemoveItem && (
                  <td style={{ padding: '7px 12px', textAlign: 'center' }}>
                    <span onClick={() => onRemoveItem(item.item_id)} style={{ fontSize: 12, cursor: 'pointer', color: 'var(--text-tertiary)', opacity: 0.4 }}>x</span>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}