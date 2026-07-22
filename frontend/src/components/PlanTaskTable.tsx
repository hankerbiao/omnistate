import React, { useCallback } from 'react';
import type { PlanTask } from './myTasksTypes';
import { STATUS_COLORS, TH, TD } from './myTasksTypes';

interface PlanTaskTableProps {
  /** 当前展示的计划任务列表 */
  planTasks: PlanTask[];
  /** 打开结果回填弹窗 */
  onOpenResultModal: (task: PlanTask) => void;
  /** 打开发送弹窗（单个下发 - 自动化用例） */
  onOpenDispatchModal: (task: PlanTask) => void;
  /** 查看自动化执行结果 */
  onViewExecutionResult?: (executionTaskId: string) => void;
  /** 打开改派弹窗 */
  onReassign?: (task: PlanTask) => void;
}

/**
 * PlanTaskTable — 计划任务列表表格组件
 * 展示分配给当前用户的用例执行任务，状态只能由结果回填或自动化下发推进。
 */
const PlanTaskTable: React.FC<PlanTaskTableProps> = ({
  planTasks,
  onOpenResultModal,
  onOpenDispatchModal,
  onViewExecutionResult,
  onReassign,
}) => {
  const nowMs = new Date().getTime();
  const handleRowClick = useCallback((task: PlanTask) => {
    if (task.type === 'manual') {
      onOpenResultModal(task);
    }
  }, [onOpenResultModal]);

  const scaledFont = (px: number) => `calc(${px}px * var(--my-tasks-font-scale, 1))`;
  const formatShortDateTime = (value?: string) => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  };
  const getScheduleMeta = (task: PlanTask) => {
    const plannedAt = task.dispatchConfig?.planned_at;
    if (!plannedAt) {
      return task.type === 'auto'
        ? { label: '未设置下发时间', color: 'var(--text-tertiary)', bg: 'var(--surface-tertiary)' }
        : null;
    }
    const plannedDate = new Date(plannedAt);
    if (Number.isNaN(plannedDate.getTime())) {
      return { label: plannedAt, color: 'var(--text-secondary)', bg: 'var(--surface-tertiary)' };
    }
    const diff = plannedDate.getTime() - nowMs;
    const hours = Math.ceil(Math.abs(diff) / (60 * 60 * 1000));
    if (task.status !== 'done' && diff < 0) {
      return {
        label: hours <= 24 ? '下发已超时' : `超时 ${Math.ceil(hours / 24)} 天`,
        color: 'var(--status-error)',
        bg: 'var(--status-error-bg)',
      };
    }
    if (diff >= 0 && hours <= 24) {
      return { label: `距下发 ${hours} 小时`, color: 'var(--status-warning)', bg: 'var(--status-warning-bg)' };
    }
    if (diff >= 0) {
      return { label: `距下发 ${Math.ceil(hours / 24)} 天`, color: 'var(--status-success)', bg: 'var(--status-success-bg)' };
    }
    return { label: '已到计划时间', color: 'var(--text-secondary)', bg: 'var(--surface-tertiary)' };
  };
  const getStatusMeta = (task: PlanTask) => {
    if (task.status === 'done') return { label: '已完成', hint: task.resultSource === 'auto' ? '自动结果' : '已回填', color: STATUS_COLORS.done };
    if (task.status === 'running') return { label: '执行中', hint: '等待结果', color: STATUS_COLORS.running };
    if (task.status === 'fail') return { label: '失败', hint: '需确认', color: STATUS_COLORS.fail };
    return task.type === 'auto'
      ? { label: '待下发', hint: '自动化', color: STATUS_COLORS.pending }
      : { label: '待回填', hint: '手工执行', color: STATUS_COLORS.pending };
  };
  const severityLabel = (severity?: string) => {
    if (!severity || severity === 'normal') return '普通';
    if (severity === 'blocker') return '阻塞';
    if (severity === 'critical') return '严重';
    if (severity === 'major') return '主要';
    if (severity === 'minor') return '轻微';
    return severity;
  };
  const getResultSummary = (task: PlanTask) => {
    if (task.result) {
      if (task.result.passed) {
        return {
          tone: 'success' as const,
          title: '通过',
          detail: task.result.actualDuration ? `耗时 ${task.result.actualDuration} 分钟` : '结果已提交',
          meta: task.result.notes || '',
        };
      }
      return {
        tone: 'danger' as const,
        title: '不通过',
        detail: task.result.bugId ? `缺陷 ${task.result.bugId}` : severityLabel(task.result.severity),
        meta: task.result.notes || task.result.actual || '',
      };
    }
    if (task.status === 'running') {
      return { tone: 'info' as const, title: '执行中', detail: task.executionTaskId ? '可查看执行进度' : '等待执行结果', meta: '' };
    }
    if (task.status === 'fail') {
      return { tone: 'danger' as const, title: '执行失败', detail: task.executionTaskId ? '查看失败详情' : '需要确认', meta: '' };
    }
    if (task.status === 'done') {
      return { tone: 'success' as const, title: '已完成', detail: task.resultSource === 'auto' ? '自动化结果' : '结果已记录', meta: '' };
    }
    return task.type === 'auto'
      ? { tone: 'default' as const, title: '尚未下发', detail: task.dispatchConfig?.schedule_type ? `计划: ${task.dispatchConfig.schedule_type}` : '等待下发执行', meta: '' }
      : { tone: 'default' as const, title: '尚未回填', detail: '点击回填测试结果', meta: '' };
  };
  const resultToneStyle = (tone: 'default' | 'success' | 'danger' | 'info') => {
    if (tone === 'success') return { color: 'var(--status-success)', bg: 'var(--status-success-bg)' };
    if (tone === 'danger') return { color: 'var(--status-error)', bg: 'var(--status-error-bg)' };
    if (tone === 'info') return { color: 'var(--status-info)', bg: 'var(--status-info-bg)' };
    return { color: 'var(--text-secondary)', bg: 'var(--surface-tertiary)' };
  };
  const handlePrimaryAction = (task: PlanTask) => {
    if (task.type === 'manual') {
      onOpenResultModal(task);
      return;
    }
    if (task.executionTaskId && task.status !== 'pending' && onViewExecutionResult) {
      onViewExecutionResult(task.executionTaskId);
      return;
    }
    onOpenDispatchModal(task);
  };
  const getPrimaryActionLabel = (task: PlanTask) => {
    if (task.type === 'manual') return task.status === 'done' ? '查看结果' : '回填结果';
    return task.executionTaskId && task.status !== 'pending' ? '查看结果' : '下发执行';
  };

  return (
    <div style={{ marginBottom: 16 }}>
      {/* 表格 */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', minWidth: 960, tableLayout: 'fixed', borderCollapse: 'collapse', fontSize: scaledFont(12), lineHeight: 'var(--my-tasks-line-height, 1.65)' }}>
          <thead>
            <tr>
              <th style={{ ...TH, width: 128 }}>状态</th>
              <th style={{ ...TH, width: 300 }}>用例</th>
              <th style={{ ...TH, width: 210 }}>结果摘要</th>
              <th style={{ ...TH, width: 150 }}>计划信息</th>
              <th style={{ ...TH, width: 170 }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {planTasks.map(task => {
              const statusMeta = getStatusMeta(task);
              const resultSummary = getResultSummary(task);
              const resultStyle = resultToneStyle(resultSummary.tone);
              const scheduleMeta = getScheduleMeta(task);
              return (
                <tr
                  key={task.id}
                  onClick={() => handleRowClick(task)}
                  style={{ cursor: task.type === 'manual' ? 'pointer' : 'default', transition: 'background 0.1s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-hover)')}
                  onMouseLeave={e => (e.currentTarget.style.background = '')}
                >
                  <td style={TD}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6, minWidth: 82,
                      padding: '4px 10px', borderRadius: 999, fontSize: scaledFont(11), fontWeight: 700,
                      color: statusMeta.color, background: `${statusMeta.color}14`, whiteSpace: 'nowrap',
                    }}>
                      <span style={{ width: 7, height: 7, borderRadius: '50%', background: statusMeta.color, flexShrink: 0 }} />
                      {statusMeta.label}
                    </span>
                    <div style={{ marginTop: 2, fontSize: scaledFont(10), color: 'var(--text-tertiary)' }}>
                      {statusMeta.hint}
                    </div>
                  </td>
                  <td style={{
                    ...TD, fontWeight: 600, color: 'var(--text-primary)',
                  }}>
                    <div style={{
                      fontFamily: 'monospace', color: 'var(--accent-primary)', fontSize: scaledFont(11), fontWeight: 700,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 3,
                    }}>
                      {task.caseId}
                    </div>
                    <div style={{
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>
                      {task.caseTitle}
                    </div>
                  </td>
                  <td style={{
                    ...TD, fontSize: scaledFont(11), color: 'var(--text-secondary)',
                  }}>
                    <div style={{
                      display: 'inline-flex', alignItems: 'center', padding: '3px 8px', borderRadius: 999,
                      color: resultStyle.color, background: resultStyle.bg, fontWeight: 700, marginBottom: 3,
                    }}>
                      {resultSummary.title}
                    </div>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>
                      {resultSummary.detail}
                    </div>
                    {resultSummary.meta && (
                      <div style={{ marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-tertiary)' }}>
                        {resultSummary.meta}
                      </div>
                    )}
                  </td>
                  <td style={{
                    ...TD, fontSize: scaledFont(11), color: 'var(--text-secondary)',
                  }}>
                    <div style={{ display: 'flex', gap: 5, alignItems: 'center', marginBottom: 3, minWidth: 0 }}>
                      <span style={{ fontWeight: 700, color: task.type === 'auto' ? '#0891b2' : 'var(--accent-primary)' }}>
                        {task.type === 'auto' ? '自动化' : '手工'}
                      </span>
                      <span style={{ color: 'var(--text-tertiary)' }}>·</span>
                      <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {task.assignee || '未指派'}
                      </span>
                    </div>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }}>
                      {task.planTitle}
                    </div>
                    <div style={{ marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-tertiary)' }}>
                      {task.component || '未设置模块'}
                    </div>
                    {scheduleMeta && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, minWidth: 0 }}>
                        <span style={{
                          padding: '1px 7px', borderRadius: 999, color: scheduleMeta.color, background: scheduleMeta.bg,
                          fontSize: scaledFont(10), fontWeight: 700, whiteSpace: 'nowrap',
                        }}>
                          {scheduleMeta.label}
                        </span>
                        {task.dispatchConfig?.planned_at && (
                          <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-tertiary)' }}>
                            {formatShortDateTime(task.dispatchConfig.planned_at)}
                          </span>
                        )}
                      </div>
                    )}
                  </td>
                  <td style={TD} onClick={e => e.stopPropagation()}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        onClick={() => handlePrimaryAction(task)}
                        style={{
                          minHeight: 30, padding: '5px 12px', fontSize: scaledFont(11), border: 'none', borderRadius: 6, cursor: 'pointer',
                          background: task.type === 'auto' ? '#0891b2' : 'var(--accent-primary)', color: '#fff', fontWeight: 700,
                        }}
                      >
                        {getPrimaryActionLabel(task)}
                      </button>
                      {onReassign && (
                        <button
                          type="button"
                          onClick={() => onReassign(task)}
                          style={{
                            minHeight: 30, padding: '5px 10px', fontSize: scaledFont(11), border: '1px solid var(--border-subtle)',
                            borderRadius: 6, cursor: 'pointer',
                            background: 'var(--surface-secondary)', color: 'var(--text-secondary)',
                          }}
                        >
                          改派
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PlanTaskTable;
