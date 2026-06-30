/**
 * ResultModal — Execution result viewer with timeline.
 * Refactored to use shadcn Dialog. Preserves all timeline building logic.
 */
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import TimelineView from '../../TimelineView';
import type { TimelineItem } from '../../TimelineView';
import type { PlanItemSummary, ItemStatus } from '../types';
import { STATUS_META } from '../types';

interface ResultModalProps {
  item: PlanItemSummary;
  taskData: any;
  timelineData: any;
  loading: boolean;
  error?: string;
  onClose: () => void;
}

const FINAL_STATUSES = ['PASSED', 'FAILED', 'SKIPPED', 'CANCELLED', 'TIMEOUT'];

export function ResultModal({ item, taskData, timelineData, loading, error, onClose }: ResultModalProps) {
  const caseSummary = taskData?.cases?.find((c: any) => c.auto_case_id === item.case_id);
  const r = caseSummary?.result_data;
  const isManual = !item.execution_task_id;

  const buildTaskTimelineItems = (): TimelineItem[] => {
    const items: TimelineItem[] = [];
    const t = taskData;
    if (!t) return items;
    if (t.triggered_at) items.push({ time: t.triggered_at, title: '任务下发', status: 'info' });
    if (t.consumed_at) items.push({ time: t.consumed_at, title: '任务被消费', status: 'info' });
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

  const buildCaseTimelineItems = (): TimelineItem[] => {
    const items: TimelineItem[] = [];
    if (!caseSummary) return items;
    const c = caseSummary;
    if (c.dispatch_status) {
      items.push({ time: c.dispatched_at || c.started_at || c.created_at, title: '用例下发状态', description: c.dispatch_status, badge: c.dispatch_status, status: c.dispatch_status === 'COMPLETED' ? 'success' : c.dispatch_status === 'DISPATCH_FAILED' ? 'failed' : 'running' });
    }
    if (c.dispatched_at) items.push({ time: c.dispatched_at, title: '用例下发时间', status: 'info' });
    if (c.started_at) items.push({ time: c.started_at, title: '用例开始执行', status: 'running' });
    if (c.finished_at) items.push({ time: c.finished_at, title: '用例执行结束', status: c.status === 'PASSED' ? 'success' : c.status === 'FAILED' ? 'failed' : 'info' });
    if (c.status) {
      items.push({ time: c.finished_at || c.last_event_at || c.started_at || c.created_at, title: '用例执行状态', description: c.status, badge: c.status, status: c.status === 'PASSED' ? 'success' : c.status === 'FAILED' ? 'failed' : c.status === 'RUNNING' ? 'running' : 'info' });
    }
    if (c.last_event_at) items.push({ time: c.last_event_at, title: '用例最近事件', status: 'info' });
    return items;
  };

  const buildBizLogTimelineItems = (): TimelineItem[] => {
    if (!timelineData?.biz_logs) return [];
    return timelineData.biz_logs.map((log: any) => ({
      time: log.created_at, title: log.action,
      description: `${log.node}${log.outcome ? ` — ${log.outcome}` : ''}`,
      status: log.outcome === 'success' || log.outcome === 'completed' ? 'success' as const : log.outcome === 'failed' ? 'failed' as const : log.level === 'WARNING' ? 'warning' as const : 'info' as const,
      badge: log.outcome || log.level,
      expandable: log.detail && Object.keys(log.detail).length > 0 ? <pre style={{ fontSize: 10, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(log.detail, null, 2)}</pre> : undefined,
    }));
  };

  const buildEventTimelineItems = (): TimelineItem[] => {
    if (!timelineData?.events) return [];
    return timelineData.events.map((evt: any) => ({
      time: evt.event_timestamp, title: evt.event_type,
      description: `phase: ${evt.phase || '-'}${evt.event_status ? ` | status: ${evt.event_status}` : ''}`,
      status: 'info' as const, badge: evt.phase || undefined,
      expandable: evt.payload && Object.keys(evt.payload).length > 0 ? <pre style={{ fontSize: 10, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(evt.payload, null, 2)}</pre> : undefined,
    }));
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[680px] max-h-[85vh] flex flex-col">
        <DialogHeader className="pb-2">
          <DialogTitle className="mb-1 flex items-center gap-2">
            <span className="font-mono text-[10px] text-[var(--text-tertiary)] bg-[var(--surface-tertiary)] px-2 py-0.5 rounded">{item.case_id}</span>
            执行结果
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {error ? (
            <p className="py-10 text-center text-sm text-[var(--text-secondary)]">{error}</p>
          ) : loading ? (
            <p className="py-10 text-center text-sm text-[var(--text-tertiary)]">加载执行结果...</p>
          ) : taskData?.error ? (
            <p className="py-8 text-center text-sm text-[var(--status-error)]">获取结果失败</p>
          ) : isManual ? (
            <div className="flex flex-col gap-4">
              <div className="flex gap-3 flex-wrap">
                {[
                  { label: '结果', value: taskData?.manualResult?.passed ? '通过' : '失败', color: taskData?.manualResult?.passed ? 'var(--status-success)' : 'var(--status-error)' },
                  { label: '严重程度', value: taskData?.manualResult?.severity || '-' },
                  { label: '备注', value: taskData?.manualResult?.notes || '-' },
                  { label: '执行人', value: taskData?.manualResult?.executed_by || '-' },
                ].map(kv => (
                  <div key={kv.label} className="px-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-secondary)] min-w-[80px]">
                    <div className="text-[10px] text-[var(--text-tertiary)] mb-0.5">{kv.label}</div>
                    <div className="text-sm font-semibold" style={{ color: kv.color || 'var(--text-primary)' }}>{kv.value ?? '-'}</div>
                  </div>
                ))}
              </div>
              {taskData?.manualResult?.executed_at && (
                <div className="text-xs text-[var(--text-tertiary)]">
                  执行时间: {new Date(taskData.manualResult.executed_at).toLocaleString('zh-CN')}
                </div>
              )}
            </div>
          ) : !caseSummary ? (
            <p className="py-8 text-center text-sm text-[var(--text-tertiary)]">暂未获取到执行结果</p>
          ) : (
            <div className="flex flex-col gap-4">
              {/* Summary cards */}
              <div className="flex gap-3 flex-wrap">
                {[
                  { label: '执行状态', value: caseSummary.status, color: STATUS_META[caseSummary.status as ItemStatus]?.color || 'var(--text-tertiary)' },
                  { label: '分派状态', value: caseSummary.dispatch_status },
                  { label: '进度', value: `${caseSummary.progress_percent ?? 0}%` },
                  { label: '尝试次数', value: caseSummary.dispatch_attempts ?? 0 },
                  { label: '事件数', value: caseSummary.event_count ?? 0 },
                ].map(kv => (
                  <div key={kv.label} className="px-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-secondary)] min-w-[80px]">
                    <div className="text-[10px] text-[var(--text-tertiary)] mb-0.5">{kv.label}</div>
                    <div className="text-sm font-semibold" style={{ color: kv.color || 'var(--text-primary)' }}>{kv.value ?? '-'}</div>
                  </div>
                ))}
              </div>

              {/* Step stats */}
              {caseSummary.step_total > 0 && (
                <div className="flex gap-3 flex-wrap">
                  {[
                    { label: '步骤总数', value: caseSummary.step_total, color: 'var(--text-primary)', bg: 'var(--surface-secondary)' },
                    { label: '通过', value: caseSummary.step_passed ?? 0, color: 'var(--status-success)', bg: 'var(--status-success-bg)' },
                    { label: '失败', value: caseSummary.step_failed ?? 0, color: 'var(--status-error)', bg: 'var(--status-error-bg)' },
                    { label: '跳过', value: caseSummary.step_skipped ?? 0, color: 'var(--text-tertiary)', bg: 'var(--surface-tertiary)' },
                  ].map(kv => (
                    <div key={kv.label} className="px-3 py-2 rounded-lg" style={{ border: `1px solid ${kv.color}30`, background: kv.bg }}>
                      <div className="text-[10px] mb-0.5" style={{ color: kv.color }}>{kv.label}</div>
                      <div className="text-sm font-semibold" style={{ color: kv.color }}>{kv.value}</div>
                    </div>
                  ))}
                </div>
              )}

              <TimelineView items={buildTaskTimelineItems()} title="任务状态时间线" />
              <TimelineView items={buildCaseTimelineItems()} title="用例状态时间线" />

              {/* Assertions */}
              {r?.assertions?.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-[var(--text-secondary)] mb-2">断言 ({r.assertions.length})</div>
                  {r.assertions.map((a: any, i: number) => (
                    <div key={i} className="px-2.5 py-2 rounded-md border border-[var(--border-subtle)] text-xs mb-1">
                      <div className="flex justify-between mb-1">
                        <span className="font-medium">#{a.seq ?? i + 1} {a.name || '-'}</span>
                        <Badge variant={a.status === 'PASSED' ? 'success' : a.status === 'FAILED' ? 'destructive' : 'info'}>{a.status || '-'}</Badge>
                      </div>
                      {a.error && <div className="text-[var(--status-error)] text-[11px] whitespace-pre-wrap break-all">{JSON.stringify(a.error)}</div>}
                      {a.timestamp && <div className="text-[var(--text-tertiary)] text-[10px] mt-1">{new Date(a.timestamp).toLocaleString('zh-CN')}</div>}
                    </div>
                  ))}
                </div>
              )}

              {/* Return data */}
              {r?.data && Object.keys(r.data).length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-[var(--text-secondary)] mb-1.5">返回数据</div>
                  <pre className="text-[11px] bg-[var(--surface-secondary)] p-2.5 rounded-md overflow-auto max-h-[200px] m-0 whitespace-pre-wrap break-all">{JSON.stringify(r.data, null, 2)}</pre>
                </div>
              )}

              {timelineData?.biz_logs?.length > 0 && <TimelineView items={buildBizLogTimelineItems()} title="操作日志" />}
              {timelineData?.events?.length > 0 && <TimelineView items={buildEventTimelineItems()} title="事件时间线" defaultCollapsed />}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
