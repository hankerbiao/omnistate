import React, { useCallback } from 'react';
import type { PlanTask } from './myTasksTypes';
import { STATUS_COLORS, TH, TD } from './myTasksTypes';

interface PlanTaskTableProps {
  /** 当前展示的计划任务列表 */
  planTasks: PlanTask[];
  /** 是否有演示标记（mock fallback） */
  isDemo: boolean;
  /** 是否有可批量下发的自动化用例 */
  hasAutoCasesForDispatch: boolean;
  /** 更新任务状态 */
  onStatusUpdate: (taskId: string, planId: string, status: PlanTask['status']) => void;
  /** 打开结果回填弹窗 */
  onOpenResultModal: (task: PlanTask) => void;
  /** 打开发送弹窗（单个下发 - 自动化用例） */
  onOpenDispatchModal: (task: PlanTask) => void;
  /** 打开批量下发弹窗 */
  onBatchDispatch: () => void;
  /** 打开改派弹窗 */
  onReassign?: (task: PlanTask) => void;
}

/**
 * PlanTaskTable — 计划任务列表表格组件
 * 展示用例执行计划的任务清单，支持状态更新、结果回填、下发操作。
 */
const PlanTaskTable: React.FC<PlanTaskTableProps> = ({
  planTasks,
  isDemo,
  hasAutoCasesForDispatch,
  onStatusUpdate,
  onOpenResultModal,
  onOpenDispatchModal,
  onBatchDispatch,
  onReassign,
}) => {
  const handleRowClick = useCallback((task: PlanTask) => {
    if (task.type === 'manual') {
      onOpenResultModal(task);
    }
  }, [onOpenResultModal]);

  return (
    <div style={{ marginBottom: 16 }}>
      {/* 表头 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, padding: '0 4px' }}>
        <span style={{
          display: 'inline-block', padding: '2px 10px', borderRadius: 6,
          fontSize: 12, fontWeight: 600, backgroundColor: 'rgba(163,113,247,0.15)', color: '#a371f7',
        }}>
          执行计划
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{planTasks.length} 项</span>
        {isDemo && (
          <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontStyle: 'italic' }}>演示</span>
        )}
        <div style={{ flex: 1 }} />
        {hasAutoCasesForDispatch && (
          <button
            onClick={onBatchDispatch}
            style={{
              padding: '4px 14px', fontSize: 11, border: 'none', borderRadius: 6, cursor: 'pointer',
              background: 'linear-gradient(135deg, #39d0d6 0%, #2ea8ad 100%)', color: '#fff', fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: 4, boxShadow: '0 2px 8px rgba(57,208,214,0.3)',
            }}
          >
            ⚡ 一键下发全部
          </button>
        )}
      </div>

      {/* 表格 */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{ ...TH, width: 32 }}>状态</th>
              <th style={{ ...TH, width: 100 }}>ID</th>
              <th style={TH}>名称</th>
              <th style={{ ...TH, width: 120 }}>计划</th>
              <th style={{ ...TH, width: 56 }}>状态</th>
              <th style={{ ...TH, width: 160 }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {planTasks.map(task => {
              return (
                <tr
                  key={task.id}
                  onClick={() => handleRowClick(task)}
                  style={{ cursor: 'pointer', transition: 'background 0.1s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-hover)')}
                  onMouseLeave={e => (e.currentTarget.style.background = '')}
                >
                  {/* Status dot */}
                  <td style={TD}>
                    <span style={{
                      display: 'block', width: 6, height: 6, borderRadius: '50%',
                      background: STATUS_COLORS[task.status], margin: '0 auto',
                    }} />
                  </td>
                  {/* ID */}
                  <td style={{
                    ...TD, fontFamily: 'monospace', color: 'var(--text-tertiary)', fontSize: 11,
                    maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {task.caseId}
                  </td>
                  {/* Title */}
                  <td style={{
                    ...TD, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap', maxWidth: 220,
                  }}>
                    {task.caseTitle}
                  </td>
                  {/* Plan */}
                  <td style={{
                    ...TD, fontSize: 11, color: 'var(--text-tertiary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180,
                  }}>
                    {task.planTitle}
                  </td>
                  {/* Status */}
                  <td style={TD}>
                    <span style={{
                      fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 8,
                      color: STATUS_COLORS[task.status],
                      background: `${STATUS_COLORS[task.status]}15`, whiteSpace: 'nowrap',
                    }}>
                      {task.status === 'done' ? '✓' : task.status === 'running' ? '▶' : task.status === 'fail' ? '✗' : '○'}
                    </span>
                  </td>
                  {/* Actions */}
                  <td style={TD} onClick={e => e.stopPropagation()}>
                    <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                      {(['pending', 'running', 'done', 'fail'] as const).map(s => (
                        <button
                          key={s}
                          onClick={() => onStatusUpdate(task.id, task.planId, s)}
                          title={s}
                          style={{
                            padding: '2px 5px', fontSize: 9, border: 'none', borderRadius: 3, cursor: 'pointer',
                            background: task.status === s ? STATUS_COLORS[s] : 'transparent',
                            color: task.status === s ? '#fff' : 'var(--text-tertiary)',
                            fontWeight: task.status === s ? 600 : 400,
                          }}
                        >
                          {s === 'done' ? '✓' : s === 'running' ? '▶' : s === 'fail' ? '✗' : '○'}
                        </button>
                      ))}
                      {task.type === 'auto' ? (
                        <button
                          onClick={() => onOpenDispatchModal(task)}
                          style={{
                            padding: '2px 8px', fontSize: 9, border: 'none', borderRadius: 3, cursor: 'pointer',
                            background: '#39d0d6', color: '#fff', fontWeight: 600, marginLeft: 4,
                          }}
                        >
                          ⚡ 下发
                        </button>
                      ) : task.status !== 'done' && (
                        <button
                          onClick={() => onOpenResultModal(task)}
                          style={{
                            padding: '2px 8px', fontSize: 9, border: 'none', borderRadius: 3, cursor: 'pointer',
                            background: 'var(--accent-primary)', color: '#fff', fontWeight: 600, marginLeft: 4,
                          }}
                        >
                          回填
                        </button>
                      )}
                      {onReassign && (
                        <button
                          onClick={() => onReassign(task)}
                          style={{
                            padding: '2px 6px', fontSize: 9, border: '1px solid var(--border-subtle)',
                            borderRadius: 3, cursor: 'pointer', marginLeft: 4,
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
