/**
 * ResultModal - 执行结果弹窗
 */
import TimelineView from '../TimelineView';
import type { ResultModalProps } from './types';

export default function ResultModal({ item, taskData, timelineData, loading, error, onClose }: ResultModalProps) {
  const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
    pending: { label: '待执行', color: '#8b949e', bg: 'rgba(139,148,158,0.08)' },
    running: { label: '执行中', color: '#58a6ff', bg: 'rgba(88,166,255,0.08)' },
    fail: { label: '失败', color: '#f85149', bg: 'rgba(248,81,73,0.08)' },
    done: { label: '已完成', color: '#3fb950', bg: 'rgba(63,185,80,0.08)' },
  };

  if (error) {
    return (
      <div style={{ position: 'fixed', inset: 0, background: 'var(--overlay-bg)', backdropFilter: 'blur(2px)', zIndex: 2000, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ background: 'var(--surface-primary)', borderRadius: 12, width: 400, maxWidth: '90vw', overflow: 'hidden', boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>执行结果</span>
            <button type="button" onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: 'var(--text-tertiary)' }}>×</button>
          </div>
          <div style={{ padding: '40px 20px', textAlign: 'center' }}>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const caseSummary = taskData?.cases?.find((c: { auto_case_id: string }) => c.auto_case_id === item.case_id);
  const r = caseSummary?.result_data;
  const isManual = !item.execution_task_id;

  // 构建任务状态时间线（4个关键阶段：下发 → 消费 → 进度 → 完成）
  const buildTaskTimelineItems = () => {
    const items: { time: string; title: string; status: string; description?: string; badge?: string }[] = [];
    const t = taskData;
    if (!t) return items;

    const FINAL_STATUSES = ['PASSED', 'FAILED', 'SKIPPED', 'CANCELLED', 'TIMEOUT'];

    if (t.triggered_at) {
      items.push({ time: t.triggered_at, title: '任务下发', status: 'info' });
    }
    if (t.consumed_at) {
      items.push({ time: t.consumed_at, title: '任务被消费', status: 'success' });
    }
    const hasProgress = (t.progress_percent ?? 0) > 0;
    const isFinished = t.finished_at || (t.overall_status && FINAL_STATUSES.includes(t.overall_status));
    const progressTime = t.last_event_at || t.started_at || t.consumed_at || t.triggered_at;
    if (hasProgress && !isFinished && progressTime) {
      items.push({
        time: progressTime,
        title: `执行进度 ${t.progress_percent}%`,
        description: t.reported_case_count != null && t.case_count != null ? `已完成 ${t.reported_case_count} / ${t.case_count} 个用例` : undefined,
        status: 'running',
      });
    }
    if (t.finished_at) {
      const isPassed = t.overall_status === 'PASSED';
      items.push({
        time: t.finished_at,
        title: isPassed ? '执行通过' : '执行失败',
        description: t.overall_status ? `最终状态: ${t.overall_status}${t.passed_case_count != null && t.case_count != null ? ` | 通过 ${t.passed_case_count} / ${t.case_count}` : ''}` : undefined,
        badge: t.overall_status,
        status: isPassed ? 'success' : 'failed',
      });
    }
    return items;
  };

  // 构建 Case 级状态时间线
  const buildCaseTimelineItems = () => {
    const items: { time?: string; title: string; status: string; description?: string; badge?: string }[] = [];
    if (!caseSummary) return items;
    const c = caseSummary;

    if (c.dispatch_status) {
      items.push({
        time: c.dispatched_at || c.started_at || c.created_at,
        title: '用例下发状态',
        description: c.dispatch_status,
        badge: c.dispatch_status,
        status: c.dispatch_status === 'COMPLETED' ? 'success' : c.dispatch_status === 'DISPATCH_FAILED' ? 'failed' : 'running',
      });
    }
    if (c.dispatched_at) {
      items.push({ time: c.dispatched_at, title: '用例下发时间', status: 'info' });
    }
    if (c.started_at) {
      items.push({ time: c.started_at, title: '用例开始执行', status: 'running' });
    }
    if (c.finished_at) {
      items.push({
        time: c.finished_at,
        title: '用例执行结束',
        status: c.status === 'PASSED' ? 'success' : c.status === 'FAILED' ? 'failed' : 'info',
      });
    }
    if (c.status) {
      items.push({
        time: c.finished_at || c.last_event_at || c.started_at || c.created_at,
        title: '用例执行状态',
        description: c.status,
        badge: c.status,
        status: c.status === 'PASSED' ? 'success' : c.status === 'FAILED' ? 'failed' : c.status === 'RUNNING' ? 'running' : 'info',
      });
    }
    if (c.last_event_at) {
      items.push({ time: c.last_event_at, title: '用例最近事件', status: 'info' });
    }
    return items;
  };

  // 构建业务日志时间线
  const buildBizLogTimelineItems = () => {
    if (!timelineData?.biz_logs) return [];
    return timelineData.biz_logs.map((log: { created_at: string; action: string; node: string; outcome?: string; level?: string; detail?: Record<string, unknown> }) => ({
      time: log.created_at,
      title: log.action,
      description: `${log.node}${log.outcome ? ` — ${log.outcome}` : ''}`,
      status: (log.outcome === 'success' || log.outcome === 'completed' ? 'success' : log.outcome === 'failed' ? 'failed' : log.level === 'WARNING' ? 'warning' : 'info') as 'success' | 'failed' | 'warning' | 'info',
      badge: log.outcome || log.level,
      badgeColor: log.outcome === 'success' ? '#3fb950' : log.outcome === 'failed' ? '#f85149' : log.level === 'WARNING' ? '#d29922' : '#8b949e',
      expandable: log.detail && Object.keys(log.detail).length > 0 ? (
        <pre style={{ fontSize: 10, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {JSON.stringify(log.detail, null, 2)}
        </pre>
      ) : undefined,
    }));
  };

  // 构建事件时间线
  const buildEventTimelineItems = () => {
    if (!timelineData?.events) return [];
    return timelineData.events.map((evt: { event_timestamp: string; event_type: string; phase?: string; event_status?: string; payload?: Record<string, unknown> }) => ({
      time: evt.event_timestamp,
      title: evt.event_type,
      description: `phase: ${evt.phase || '-'}${evt.event_status ? ` | status: ${evt.event_status}` : ''}`,
      status: 'info' as const,
      badge: evt.phase || undefined,
      expandable: evt.payload && Object.keys(evt.payload).length > 0 ? (
        <pre style={{ fontSize: 10, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {JSON.stringify(evt.payload, null, 2)}
        </pre>
      ) : undefined,
    }));
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--overlay-bg)', backdropFilter: 'blur(2px)', zIndex: 2000, display: 'flex', justifyContent: 'center', alignItems: 'center' }}
      onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{
        background: 'var(--surface-primary)', borderRadius: 12, width: 680, maxWidth: '94vw',
        maxHeight: '85vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 25px 80px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)',
      }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', background: 'var(--surface-tertiary)', padding: '1px 8px', borderRadius: 4 }}>{item.case_id}</span>
              <span style={{ fontSize: 13, fontWeight: 600 }}>执行结果</span>
            </span>
          </div>
          <button onClick={onClose} style={{ fontSize: 18, color: 'var(--text-tertiary)', background: 'none', border: 'none', cursor: 'pointer' }}>x</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>加载执行结果...</div>
          ) : taskData?.error ? (
            <div style={{ padding: 30, textAlign: 'center', color: 'var(--status-error)', fontSize: 13 }}>获取结果失败</div>
          ) : isManual ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {[
                  { label: '结果', value: taskData?.manualResult?.passed ? '通过' : '失败', color: taskData?.manualResult?.passed ? '#3fb950' : '#f85149' },
                  { label: '严重程度', value: taskData?.manualResult?.severity || '-' },
                  { label: '备注', value: taskData?.manualResult?.notes || '-' },
                  { label: '执行人', value: taskData?.manualResult?.executed_by || '-' },
                ].map((kv) => (
                  <div key={kv.label} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)', minWidth: 80 }}>
                    <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 2 }}>{kv.label}</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: kv.color || 'var(--text-primary)' }}>{kv.value ?? '-'}</div>
                  </div>
                ))}
              </div>
              {taskData?.manualResult?.executed_at && (
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                  执行时间: {new Date(taskData.manualResult.executed_at).toLocaleString('zh-CN')}
                </div>
              )}
            </div>
          ) : !caseSummary ? (
            <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>暂未获取到执行结果</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* 摘要卡片 */}
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {[
                  { label: '执行状态', value: caseSummary.status, color: STATUS_META[caseSummary.status]?.color || '#8b949e' },
                  { label: '分派状态', value: caseSummary.dispatch_status },
                  { label: '进度', value: `${caseSummary.progress_percent ?? 0}%` },
                  { label: '尝试次数', value: caseSummary.dispatch_attempts ?? 0 },
                  { label: '事件数', value: caseSummary.event_count ?? 0 },
                ].map((kv) => (
                  <div key={kv.label} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)', minWidth: 80 }}>
                    <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 2 }}>{kv.label}</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: kv.color || 'var(--text-primary)' }}>{kv.value ?? '-'}</div>
                  </div>
                ))}
              </div>

              {/* 步骤统计 */}
              {caseSummary.step_total > 0 && (
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)' }}>
                    <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 2 }}>步骤总数</div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{caseSummary.step_total}</div>
                  </div>
                  <div style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(63,185,80,0.3)', background: 'rgba(63,185,80,0.05)' }}>
                    <div style={{ fontSize: 10, color: '#3fb950', marginBottom: 2 }}>通过</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#3fb950' }}>{caseSummary.step_passed ?? 0}</div>
                  </div>
                  <div style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(248,81,73,0.3)', background: 'rgba(248,81,73,0.05)' }}>
                    <div style={{ fontSize: 10, color: '#f85149', marginBottom: 2 }}>失败</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#f85149' }}>{caseSummary.step_failed ?? 0}</div>
                  </div>
                  <div style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(139,148,158,0.3)', background: 'rgba(139,148,158,0.05)' }}>
                    <div style={{ fontSize: 10, color: '#8b949e', marginBottom: 2 }}>跳过</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#8b949e' }}>{caseSummary.step_skipped ?? 0}</div>
                  </div>
                </div>
              )}

              {/* 任务状态时间线 */}
              <TimelineView items={buildTaskTimelineItems()} title="任务状态时间线" />

              {/* 用例状态时间线 */}
              <TimelineView items={buildCaseTimelineItems()} title="用例状态时间线" />

              {/* 断言 */}
              {r?.assertions?.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>断言 ({r.assertions.length})</div>
                  {r.assertions.map((a: { seq?: number; name?: string; status?: string; error?: unknown; timestamp?: string }, i: number) => (
                    <div key={i} style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border-subtle)', fontSize: 12, marginBottom: 4 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 500 }}>#{a.seq ?? i + 1} {a.name || '-'}</span>
                        <span style={{ padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 600, color: a.status === 'PASSED' ? '#3fb950' : a.status === 'FAILED' ? '#f85149' : '#58a6ff', background: a.status === 'PASSED' ? 'rgba(63,185,80,0.1)' : a.status === 'FAILED' ? 'rgba(248,81,73,0.1)' : 'rgba(88,166,255,0.1)' }}>{a.status || '-'}</span>
                      </div>
                      {a.error && <div style={{ color: 'var(--status-error)', fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(a.error)}</div>}
                      {a.timestamp && <div style={{ color: 'var(--text-tertiary)', fontSize: 10, marginTop: 2 }}>{new Date(a.timestamp).toLocaleString('zh-CN')}</div>}
                    </div>
                  ))}
                </div>
              )}

              {/* 返回数据 */}
              {r?.data && Object.keys(r.data).length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>返回数据</div>
                  <pre style={{ fontSize: 11, background: 'var(--surface-secondary)', padding: 10, borderRadius: 6, overflow: 'auto', maxHeight: 200, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(r.data, null, 2)}</pre>
                </div>
              )}

              {/* 业务轨迹日志 */}
              {timelineData?.biz_logs?.length > 0 && (
                <TimelineView items={buildBizLogTimelineItems()} title="操作日志" />
              )}

              {/* 事件时间线 */}
              {timelineData?.events?.length > 0 && (
                <TimelineView items={buildEventTimelineItems()} title="事件时间线" defaultCollapsed />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}