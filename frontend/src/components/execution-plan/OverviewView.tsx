/**
 * OverviewView - 运行总览
 */
import type { OverviewViewProps } from './types';

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: '待执行', color: '#8b949e', bg: 'rgba(139,148,158,0.08)' },
  running: { label: '执行中', color: '#58a6ff', bg: 'rgba(88,166,255,0.08)' },
  fail: { label: '失败', color: '#f85149', bg: 'rgba(248,81,73,0.08)' },
  done: { label: '已完成', color: '#3fb950', bg: 'rgba(63,185,80,0.08)' },
};

const PLAN_STATUS_META: Record<string, { label: string; color: string }> = {
  active: { label: '进行中', color: '#3fb950' },
  done: { label: '已完成', color: '#8b949e' },
};

const PRIORITY_COLORS: Record<string, string> = {
  P0: '#f85149', P1: '#d29922', P2: '#58a6ff', P3: '#8b949e',
};

export default function OverviewView({ data, loading, onRefresh, onSelectPlan, users, onViewResult, onTerminateItem, onDeleteItem, onCancelExecution }: OverviewViewProps) {
  const plans = (data?.plans as { plan_id: string; title: string; status: string; progress_percent?: number; item_count?: number; running_count?: number; pending_count?: number; fail_count?: number }[]) || [];
  const runningItems = (data?.running_items as {
    item_id: string; plan_id: string; case_id: string; case_title: string; ref_type: string;
    assignee_id?: string; priority: string; plan_title?: string; status: string;
    execution_task_id?: string; result?: unknown;
  }[]) || [];

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '16px 20px', background: 'var(--surface-secondary)' }}>
      {/* 头部统计 */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexShrink: 0 }}>
        {[
          { label: '总计划', value: data?.total_plans ?? 0, color: '#58a6ff' },
          { label: '总条目', value: data?.total_items ?? 0, color: '#8b949e' },
          { label: '执行中', value: data?.running_count ?? 0, color: '#3fb950' },
          { label: '待执行', value: data?.pending_count ?? 0, color: '#d29922' },
          { label: '已完成', value: data?.done_count ?? 0, color: '#8b949e' },
          { label: '失败', value: data?.fail_count ?? 0, color: '#f85149' },
        ].map((s) => (
          <div key={s.label} style={{ padding: '10px 16px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--bg-elevated)', minWidth: 80, textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'flex-end', marginLeft: 'auto' }}>
          <button className="btn btn--ghost btn--sm" onClick={onRefresh} disabled={loading} style={{ fontSize: 12 }}>
            {loading ? '刷新中...' : '刷新'}
          </button>
        </div>
      </div>

      {/* 计划概览卡片 */}
      <div style={{ marginBottom: 16, flexShrink: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>执行计划列表</div>
        {loading && plans.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>加载中...</div>
        ) : plans.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>暂无计划</div>
        ) : (
          <div style={{ display: 'flex', gap: 8, overflow: 'auto', paddingBottom: 4 }}>
            {plans.map((p) => {
              const planStatusMeta = PLAN_STATUS_META[p.status] || { label: p.status, color: '#8b949e' };
              return (
                <div
                  key={p.plan_id}
                  onClick={() => onSelectPlan(p.plan_id)}
                  style={{ minWidth: 200, padding: '10px 14px', borderRadius: 8, cursor: 'pointer', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{p.title}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, fontWeight: 600, color: planStatusMeta.color, background: `${planStatusMeta.color}18` }}>
                      {planStatusMeta.label}
                    </span>
                  </div>
                  <div style={{ height: 3, background: 'var(--surface-tertiary)', borderRadius: 2, marginBottom: 6 }}>
                    <div style={{ width: `${p.progress_percent ?? 0}%`, height: '100%', background: 'var(--accent-primary)', borderRadius: 2 }} />
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 11, color: 'var(--text-tertiary)' }}>
                    <span>共 {p.item_count}</span>
                    <span style={{ color: '#3fb950' }}>运行 {p.running_count}</span>
                    <span style={{ color: '#d29922' }}>待执 {p.pending_count}</span>
                    <span style={{ color: '#f85149' }}>失败 {p.fail_count}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 运行中任务列表 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>运行中任务</div>
        {loading && runningItems.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>加载中...</div>
        ) : runningItems.length === 0 ? (
          <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>暂没有运行中的任务</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--surface-primary)', position: 'sticky', top: 0, zIndex: 1 }}>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>计划</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>用例ID</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>标题</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>类型</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>执行人</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>优先级</th>
                <th style={{ padding: '6px 10px', textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>结果</th>
                <th style={{ padding: '6px 10px', textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)', width: 100 }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {runningItems.map((item) => {
                const statusMeta = STATUS_META[item.status] || STATUS_META.pending;
                return (
                  <tr key={item.item_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '6px 10px', color: 'var(--accent-primary)', fontSize: 11, cursor: 'pointer' }} onClick={() => onSelectPlan(item.plan_id)}>
                      {item.plan_title || item.plan_id}
                    </td>
                    <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 10, color: 'var(--text-tertiary)' }}>{item.case_id}</td>
                    <td style={{ padding: '6px 10px', fontWeight: 500 }}>{item.case_title}</td>
                    <td style={{ padding: '6px 10px' }}>
                      <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: item.ref_type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)', color: item.ref_type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600 }}>
                        {item.ref_type === 'auto' ? 'AUTO' : 'MANUAL'}
                      </span>
                    </td>
                    <td style={{ padding: '6px 10px', color: 'var(--text-secondary)' }}>
                      {item.assignee_id ? (users.find((u) => u.user_id === item.assignee_id)?.username || item.assignee_id) : (
                        <span style={{ color: 'var(--status-warn)', fontSize: 10 }}>未指派</span>
                      )}
                    </td>
                    <td style={{ padding: '6px 10px', color: PRIORITY_COLORS[item.priority] || '#8b949e', fontWeight: 600 }}>{item.priority}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'center' }}>
                      {(item.execution_task_id || item.result) && onViewResult ? (
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); onViewResult(item as never, {}, {}); }}
                          style={{ fontSize: 10, padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)', color: 'var(--accent-primary)', cursor: 'pointer' }}
                        >
                          查看
                        </button>
                      ) : (
                        <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>-</span>
                      )}
                    </td>
                    <td style={{ padding: '6px 10px', textAlign: 'center' }}>
                      {onCancelExecution && (
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); onCancelExecution(item.item_id); }}
                          style={{ fontSize: 10, padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border-subtle)', background: 'transparent', color: '#d29922', cursor: 'pointer' }}
                        >
                          取消执行
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}