import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { ExecutionTask, TaskStatus, AutomationTestCaseResponse, ExecutionAgent, DispatchCaseItem } from '../types';

interface TaskListProps {
  onLogout?: () => void;
}

interface DispatchModalState {
  isOpen: boolean;
  framework: string;
  agentId: string;
  scheduleType: 'IMMEDIATE' | 'SCHEDULED';
  plannedAt: string;
  selectedCases: string[];
  loading: boolean;
  submitting: boolean;
  error: string | null;
}

const FRAMEWORKS = ['pytest', 'robot', 'playwright', 'cypress', 'jest'];
const DEFAULT_FRAMEWORK = 'pytest';

const TaskList: React.FC<TaskListProps> = () => {
  const [tasks, setTasks] = useState<ExecutionTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskStatus | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [dispatchModal, setDispatchModal] = useState<DispatchModalState>({
    isOpen: false,
    framework: DEFAULT_FRAMEWORK,
    agentId: '',
    scheduleType: 'IMMEDIATE',
    plannedAt: '',
    selectedCases: [],
    loading: false,
    submitting: false,
    error: null,
  });
  const [autoCases, setAutoCases] = useState<AutomationTestCaseResponse[]>([]);
  const [agents, setAgents] = useState<ExecutionAgent[]>([]);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.listTasks({ limit: 50 });
      setTasks(response.data || []);
    } catch (err) {
      setError('获取任务列表失败');
      console.error('Fetch tasks error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const openDispatchModal = async () => {
    setDispatchModal(prev => ({ ...prev, isOpen: true, loading: true, error: null }));
    try {
      const [casesRes, agentsRes] = await Promise.all([
        api.listAutomationTestCases({ limit: 100 }),
        api.listAgents({ online_only: true }),
      ]);
      setAutoCases(casesRes.data || []);
      setAgents(agentsRes.data || []);
    } catch (err) {
      console.error('Fetch dispatch data error:', err);
      setDispatchModal(prev => ({ ...prev, error: '获取用例和代理失败' }));
    } finally {
      setDispatchModal(prev => ({ ...prev, loading: false }));
    }
  };

  const closeDispatchModal = () => {
    setDispatchModal({
      isOpen: false,
      framework: DEFAULT_FRAMEWORK,
      agentId: '',
      scheduleType: 'IMMEDIATE',
      plannedAt: '',
      selectedCases: [],
      loading: false,
      submitting: false,
      error: null,
    });
  };

  const handleDispatchSubmit = async () => {
    const { framework, agentId, scheduleType, plannedAt, selectedCases } = dispatchModal;
    if (selectedCases.length === 0) {
      setDispatchModal(prev => ({ ...prev, error: '请选择至少一个用例' }));
      return;
    }
    if (scheduleType === 'SCHEDULED' && !plannedAt) {
      setDispatchModal(prev => ({ ...prev, error: '请选择计划执行时间' }));
      return;
    }

    setDispatchModal(prev => ({ ...prev, submitting: true, error: null }));
    try {
      const cases: DispatchCaseItem[] = selectedCases.map(id => ({ auto_case_id: id }));
      const requestData = {
        framework,
        agent_id: agentId || undefined,
        trigger_source: 'web_ui',
        schedule_type: scheduleType,
        planned_at: scheduleType === 'SCHEDULED' ? plannedAt : undefined,
        cases,
      };
      await api.dispatchTask(requestData);
      closeDispatchModal();
      fetchTasks();
    } catch (err) {
      console.error('Dispatch task error:', err);
      setDispatchModal(prev => ({ ...prev, error: '下发任务失败' }));
    } finally {
      setDispatchModal(prev => ({ ...prev, submitting: false }));
    }
  };

  const toggleCaseSelection = (caseId: string) => {
    setDispatchModal(prev => ({
      ...prev,
      selectedCases: prev.selectedCases.includes(caseId)
        ? prev.selectedCases.filter(id => id !== caseId)
        : [...prev.selectedCases, caseId],
    }));
  };

  const handleTaskClick = async (taskId: string) => {
    setModalLoading(true);
    try {
      const response = await api.getTaskStatus(taskId);
      setSelectedTask(response.data);
    } catch (err) {
      console.error('Fetch task status error:', err);
      alert('获取任务详情失败');
    } finally {
      setModalLoading(false);
    }
  };

  const getStatusStyle = (status: string) => {
    const statusMap: Record<string, { bg: string; color: string; label: string }> = {
      PENDING: { bg: 'var(--status-warning-bg)', color: 'var(--accent-yellow)', label: '待处理' },
      RUNNING: { bg: 'var(--status-info-bg)', color: 'var(--accent-blue)', label: '运行中' },
      SUCCESS: { bg: 'var(--status-success-bg)', color: 'var(--accent-green)', label: '成功' },
      FAILED: { bg: 'var(--status-error-bg)', color: 'var(--accent-red)', label: '失败' },
      CANCELLED: { bg: 'var(--bg-tertiary)', color: 'var(--text-muted)', label: '已取消' },
      SCHEDULED: { bg: 'rgba(163, 113, 247, 0.15)', color: 'var(--accent-purple)', label: '已调度' },
      DISPATCHED: { bg: 'rgba(57, 208, 214, 0.15)', color: 'var(--accent-cyan)', label: '已下发' },
      CONSUMED: { bg: 'var(--status-success-bg)', color: 'var(--accent-green)', label: '已消费' },
      NOT_CONSUMED: { bg: 'var(--bg-tertiary)', color: 'var(--text-muted)', label: '未消费' },
    };
    return statusMap[status] || { bg: 'var(--bg-tertiary)', color: 'var(--text-secondary)', label: status };
  };

  const statusCounts = tasks.reduce((acc, task) => {
    acc[task.overall_status] = (acc[task.overall_status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>执行任务</h1>
          <div style={styles.statsRow}>
            {Object.entries(statusCounts).slice(0, 4).map(([status, count]) => {
              const s = getStatusStyle(status);
              return (
                <span
                  key={status}
                  style={{
                    ...styles.statBadge,
                    backgroundColor: s.bg,
                    color: s.color,
                  }}
                >
                  {s.label} {count}
                </span>
              );
            })}
          </div>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.dispatchBtn} onClick={openDispatchModal}>
            <span style={styles.btnIcon}>▶</span>
            下发任务
          </button>
          <button style={styles.refreshBtn} onClick={fetchTasks} disabled={loading}>
            <span style={styles.btnIcon}>↻</span>
            {loading ? '加载中' : '刷新'}
          </button>
        </div>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          <span>⚠</span> {error}
        </div>
      )}

      <div style={styles.tableWrapper}>
        {loading ? (
          <div style={styles.loadingState}>
            <div style={styles.spinner} />
            <span>加载任务列表...</span>
          </div>
        ) : tasks.length === 0 ? (
          <div style={styles.emptyState}>
            <span style={styles.emptyIcon}>▸</span>
            <p>暂无执行任务</p>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeader}>
                <th style={styles.th}>任务ID</th>
                <th style={styles.th}>框架</th>
                <th style={styles.th}>调度类型</th>
                <th style={styles.th}>状态</th>
                <th style={styles.th}>用例数</th>
                <th style={styles.th}>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => {
                const statusStyle = getStatusStyle(task.overall_status);
                const scheduleStyle = getStatusStyle(task.schedule_type);
                return (
                  <tr
                    key={task.task_id}
                    style={styles.tr}
                    onClick={() => handleTaskClick(task.task_id)}
                    className="task-row"
                  >
                    <td style={styles.td}>
                      <span style={styles.taskId}>{task.task_id}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.frameworkBadge}>{task.framework}</span>
                    </td>
                    <td style={styles.td}>
                      <span
                        style={{
                          ...styles.statusBadge,
                          backgroundColor: scheduleStyle.bg,
                          color: scheduleStyle.color,
                        }}
                      >
                        {task.schedule_type}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <span
                        style={{
                          ...styles.statusBadgeLarge,
                          backgroundColor: statusStyle.bg,
                          color: statusStyle.color,
                        }}
                      >
                        <span
                          style={{
                            ...styles.statusDot,
                            backgroundColor: statusStyle.color,
                          }}
                          className={task.overall_status === 'RUNNING' ? 'pulse' : ''}
                        />
                        {statusStyle.label}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.caseCount}>{task.case_count}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.timeText}>
                        {new Date(task.created_at).toLocaleString('zh-CN')}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal */}
      {selectedTask && (
        <div style={styles.modalOverlay} onClick={() => setSelectedTask(null)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>
                <span style={styles.modalIcon}>◈</span>
                任务详情
              </h2>
              <button style={styles.closeBtn} onClick={() => setSelectedTask(null)}>×</button>
            </div>

            {modalLoading ? (
              <div style={styles.modalLoading}>
                <div style={styles.spinner} />
              </div>
            ) : (
              <div style={styles.modalBody}>
                <div style={styles.detailGrid}>
                  <div style={styles.detailItem}>
                    <span style={styles.detailLabel}>任务ID</span>
                    <span style={styles.detailValue}>{selectedTask.task_id}</span>
                  </div>
                  <div style={styles.detailItem}>
                    <span style={styles.detailLabel}>外部ID</span>
                    <span style={styles.detailValue}>{selectedTask.external_task_id || '-'}</span>
                  </div>
                  <div style={styles.detailItem}>
                    <span style={styles.detailLabel}>执行框架</span>
                    <span style={styles.detailValue}>{selectedTask.framework}</span>
                  </div>
                  <div style={styles.detailItem}>
                    <span style={styles.detailLabel}>代理ID</span>
                    <span style={styles.detailValue}>{selectedTask.agent_id || '-'}</span>
                  </div>
                  <div style={styles.detailItem}>
                    <span style={styles.detailLabel}>下发通道</span>
                    <span style={styles.detailValue}>{selectedTask.dispatch_channel}</span>
                  </div>
                  <div style={styles.detailItem}>
                    <span style={styles.detailLabel}>用例数量</span>
                    <span style={styles.detailValue}>{selectedTask.case_count}</span>
                  </div>
                </div>

                <div style={styles.statusSection}>
                  <h3 style={styles.sectionTitle}>状态信息</h3>
                  <div style={styles.statusGrid}>
                    <div style={styles.statusItem}>
                      <span style={styles.statusLabel}>调度状态</span>
                      <span
                        style={{
                          ...styles.statusBadge,
                          ...getStatusStyleStyle(selectedTask.schedule_status),
                        }}
                      >
                        {selectedTask.schedule_status}
                      </span>
                    </div>
                    <div style={styles.statusItem}>
                      <span style={styles.statusLabel}>下发状态</span>
                      <span
                        style={{
                          ...styles.statusBadge,
                          ...getStatusStyleStyle(selectedTask.dispatch_status),
                        }}
                      >
                        {selectedTask.dispatch_status}
                      </span>
                    </div>
                    <div style={styles.statusItem}>
                      <span style={styles.statusLabel}>消费状态</span>
                      <span
                        style={{
                          ...styles.statusBadge,
                          ...getStatusStyleStyle(selectedTask.consume_status),
                        }}
                      >
                        {selectedTask.consume_status}
                      </span>
                    </div>
                    <div style={styles.statusItem}>
                      <span style={styles.statusLabel}>整体状态</span>
                      <span
                        style={{
                          ...styles.statusBadge,
                          ...getStatusStyleStyle(selectedTask.overall_status),
                        }}
                      >
                        {selectedTask.overall_status}
                      </span>
                    </div>
                  </div>
                </div>

                <div style={styles.timeSection}>
                  <h3 style={styles.sectionTitle}>时间信息</h3>
                  <div style={styles.timeGrid}>
                    <div>
                      <span style={styles.timeLabel}>计划执行</span>
                      <span style={styles.timeValue}>
                        {selectedTask.planned_at ? new Date(selectedTask.planned_at).toLocaleString('zh-CN') : '-'}
                      </span>
                    </div>
                    <div>
                      <span style={styles.timeLabel}>实际触发</span>
                      <span style={styles.timeValue}>
                        {selectedTask.triggered_at ? new Date(selectedTask.triggered_at).toLocaleString('zh-CN') : '-'}
                      </span>
                    </div>
                    <div>
                      <span style={styles.timeLabel}>创建时间</span>
                      <span style={styles.timeValue}>
                        {new Date(selectedTask.created_at).toLocaleString('zh-CN')}
                      </span>
                    </div>
                    <div>
                      <span style={styles.timeLabel}>更新时间</span>
                      <span style={styles.timeValue}>
                        {new Date(selectedTask.updated_at).toLocaleString('zh-CN')}
                      </span>
                    </div>
                  </div>
                </div>

                {selectedTask.error_message && (
                  <div style={styles.errorSection}>
                    <h3 style={styles.sectionTitle}>错误信息</h3>
                    <pre style={styles.errorMessage}>{selectedTask.error_message}</pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Dispatch Task Modal */}
      {dispatchModal.isOpen && (
        <div style={styles.modalOverlay} onClick={closeDispatchModal}>
          <div style={styles.dispatchModal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>
                <span style={styles.modalIcon}>▶</span>
                下发任务
              </h2>
              <button style={styles.closeBtn} onClick={closeDispatchModal}>×</button>
            </div>

            <div style={styles.dispatchModalBody}>
              {dispatchModal.loading ? (
                <div style={styles.modalLoading}>
                  <div style={styles.spinner} />
                </div>
              ) : (
                <>
                  <div style={styles.formSection}>
                    <label style={styles.formLabel}>执行框架</label>
                    <select
                      style={styles.select}
                      value={dispatchModal.framework}
                      onChange={(e) => setDispatchModal(prev => ({ ...prev, framework: e.target.value }))}
                    >
                      {FRAMEWORKS.map(fw => (
                        <option key={fw} value={fw}>{fw.toUpperCase()}</option>
                      ))}
                    </select>
                  </div>

                  <div style={styles.formSection}>
                    <label style={styles.formLabel}>目标代理 (可选)</label>
                    <select
                      style={styles.select}
                      value={dispatchModal.agentId}
                      onChange={(e) => setDispatchModal(prev => ({ ...prev, agentId: e.target.value }))}
                    >
                      <option value="">自动分配</option>
                      {agents.map(agent => (
                        <option key={agent.agent_id} value={agent.agent_id}>
                          {agent.agent_id} ({agent.hostname})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div style={styles.formSection}>
                    <label style={styles.formLabel}>下发方式</label>
                    <div style={styles.radioGroup}>
                      <label style={styles.radioLabel}>
                        <input
                          type="radio"
                          name="scheduleType"
                          checked={dispatchModal.scheduleType === 'IMMEDIATE'}
                          onChange={() => setDispatchModal(prev => ({ ...prev, scheduleType: 'IMMEDIATE', plannedAt: '' }))}
                        />
                        <span>立即下发</span>
                      </label>
                      <label style={styles.radioLabel}>
                        <input
                          type="radio"
                          name="scheduleType"
                          checked={dispatchModal.scheduleType === 'SCHEDULED'}
                          onChange={() => setDispatchModal(prev => ({ ...prev, scheduleType: 'SCHEDULED' }))}
                        />
                        <span>定时下发</span>
                      </label>
                    </div>
                  </div>

                  {dispatchModal.scheduleType === 'SCHEDULED' && (
                    <div style={styles.formSection}>
                      <label style={styles.formLabel}>计划执行时间</label>
                      <input
                        type="datetime-local"
                        style={styles.input}
                        value={dispatchModal.plannedAt}
                        onChange={(e) => setDispatchModal(prev => ({ ...prev, plannedAt: e.target.value }))}
                      />
                    </div>
                  )}

                  <div style={styles.formSection}>
                    <label style={styles.formLabel}>
                      选择用例 ({dispatchModal.selectedCases.length} 已选)
                    </label>
                    <div style={styles.caseList}>
                      {autoCases.length === 0 ? (
                        <div style={styles.emptyCases}>暂无可用用例</div>
                      ) : (
                        autoCases.map(caseItem => (
                          <label key={caseItem.auto_case_id} style={styles.caseItem}>
                            <input
                              type="checkbox"
                              checked={dispatchModal.selectedCases.includes(caseItem.auto_case_id)}
                              onChange={() => toggleCaseSelection(caseItem.auto_case_id)}
                            />
                            <span style={styles.caseName}>{caseItem.auto_case_id}</span>
                            <span style={styles.caseFramework}>{caseItem.framework}</span>
                          </label>
                        ))
                      )}
                    </div>
                  </div>

                  {dispatchModal.error && (
                    <div style={styles.errorBanner}>{dispatchModal.error}</div>
                  )}

                  <div style={styles.modalActions}>
                    <button style={styles.cancelBtn} onClick={closeDispatchModal}>
                      取消
                    </button>
                    <button
                      style={styles.submitBtn}
                      onClick={handleDispatchSubmit}
                      disabled={dispatchModal.submitting}
                    >
                      {dispatchModal.submitting ? '下发中...' : '确认下发'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .task-row { cursor: pointer; }
        .task-row:hover { background-color: var(--bg-tertiary) !important; }
        .task-row:hover td { color: var(--accent-cyan); }
      `}</style>
    </div>
  );
};

function getStatusStyleStyle(status: string) {
  const s = {
    PENDING: { bg: 'var(--status-warning-bg)', color: 'var(--accent-yellow)' },
    RUNNING: { bg: 'var(--status-info-bg)', color: 'var(--accent-blue)' },
    SUCCESS: { bg: 'var(--status-success-bg)', color: 'var(--accent-green)' },
    FAILED: { bg: 'var(--status-error-bg)', color: 'var(--accent-red)' },
    CANCELLED: { bg: 'var(--bg-tertiary)', color: 'var(--text-muted)' },
    SCHEDULED: { bg: 'rgba(163, 113, 247, 0.15)', color: 'var(--accent-purple)' },
    DISPATCHED: { bg: 'rgba(57, 208, 214, 0.15)', color: 'var(--accent-cyan)' },
    CONSUMED: { bg: 'var(--status-success-bg)', color: 'var(--accent-green)' },
    NOT_CONSUMED: { bg: 'var(--bg-tertiary)', color: 'var(--text-muted)' },
  }[status] || { bg: 'var(--bg-tertiary)', color: 'var(--text-secondary)' };
  return { backgroundColor: s.bg, color: s.color };
}

const styles = {
  container: {
    padding: '32px',
    maxWidth: '1400px',
    margin: '0 auto',
    animation: 'fadeIn 0.4s ease',
  } as const,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '28px',
  } as const,
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
  } as const,
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    letterSpacing: '-0.5px',
    margin: 0,
  } as const,
  statsRow: {
    display: 'flex',
    gap: '10px',
  } as const,
  statBadge: {
    padding: '5px 12px',
    fontSize: '12px',
    fontWeight: 500,
    borderRadius: '12px',
  } as const,
  headerActions: {
    display: 'flex',
    gap: '10px',
  } as const,
  dispatchBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: '#fff',
    backgroundColor: 'var(--accent-cyan)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  refreshBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  btnIcon: {
    fontSize: '14px',
  } as const,
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 18px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--accent-red)',
    fontSize: '14px',
    marginBottom: '20px',
  } as const,
  dispatchModal: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    width: '90%',
    maxWidth: '520px',
    maxHeight: '85vh',
    overflow: 'auto',
    boxShadow: 'var(--shadow-lg)',
    animation: 'scaleIn 0.3s ease',
  } as const,
  dispatchModalBody: {
    padding: '24px',
  } as const,
  formSection: {
    marginBottom: '20px',
  } as const,
  formLabel: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: '8px',
  } as const,
  select: {
    width: '100%',
    padding: '10px 14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    outline: 'none',
  } as const,
  input: {
    width: '100%',
    padding: '10px 14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
  } as const,
  radioGroup: {
    display: 'flex',
    gap: '20px',
  } as const,
  radioLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    cursor: 'pointer',
  } as const,
  caseList: {
    maxHeight: '200px',
    overflowY: 'auto',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--bg-primary)',
  } as const,
  emptyCases: {
    padding: '20px',
    textAlign: 'center',
    color: 'var(--text-muted)',
    fontSize: '14px',
  } as const,
  caseItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 14px',
    borderBottom: '1px solid var(--border-muted)',
    cursor: 'pointer',
    fontSize: '13px',
    color: 'var(--text-primary)',
  } as const,
  caseName: {
    flex: 1,
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  caseFramework: {
    fontSize: '11px',
    color: 'var(--accent-purple)',
    backgroundColor: 'rgba(163, 113, 247, 0.15)',
    padding: '2px 8px',
    borderRadius: '4px',
  } as const,
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '24px',
  } as const,
  cancelBtn: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  submitBtn: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    color: '#fff',
    backgroundColor: 'var(--accent-cyan)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  tableWrapper: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
  } as const,
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  } as const,
  tableHeader: {
    backgroundColor: 'var(--bg-tertiary)',
  } as const,
  th: {
    padding: '14px 20px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textAlign: 'left' as const,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    borderBottom: '1px solid var(--border-default)',
  } as const,
  tr: {
    borderBottom: '1px solid var(--border-muted)',
    transition: 'all var(--transition-fast)',
  } as const,
  td: {
    padding: '16px 20px',
    fontSize: '14px',
    color: 'var(--text-primary)',
  } as const,
  taskId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--accent-cyan)',
  } as const,
  frameworkBadge: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    color: 'var(--accent-purple)',
    backgroundColor: 'rgba(163, 113, 247, 0.15)',
    padding: '4px 10px',
    borderRadius: '6px',
  } as const,
  statusBadge: {
    display: 'inline-flex',
    padding: '4px 10px',
    fontSize: '11px',
    fontWeight: 600,
    borderRadius: '10px',
    textTransform: 'uppercase' as const,
  } as const,
  statusBadgeLarge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 14px',
    fontSize: '12px',
    fontWeight: 600,
    borderRadius: '14px',
  } as const,
  statusDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
  } as const,
  caseCount: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--accent-orange)',
  } as const,
  timeText: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  loadingState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    padding: '60px',
    color: 'var(--text-secondary)',
  } as const,
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid var(--border-default)',
    borderTopColor: 'var(--accent-cyan)',
    borderRadius: '50%',
  } as const,
  emptyState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '60px',
    color: 'var(--text-muted)',
  } as const,
  emptyIcon: {
    fontSize: '48px',
    opacity: 0.3,
  } as const,
  // Modal
  modalOverlay: {
    position: 'fixed' as const,
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
    animation: 'fadeIn 0.2s ease',
  } as const,
  modal: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    width: '90%',
    maxWidth: '640px',
    maxHeight: '85vh',
    overflow: 'auto',
    boxShadow: 'var(--shadow-lg)',
    animation: 'scaleIn 0.3s ease',
  } as const,
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-tertiary)',
  } as const,
  modalTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  } as const,
  modalIcon: {
    color: 'var(--accent-cyan)',
    fontSize: '20px',
  } as const,
  closeBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    fontSize: '28px',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    lineHeight: 1,
    padding: '0',
  } as const,
  modalLoading: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '60px',
  } as const,
  modalBody: {
    padding: '24px',
  } as const,
  detailGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '16px',
    marginBottom: '24px',
  } as const,
  detailItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  } as const,
  detailLabel: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as const,
  detailValue: {
    fontSize: '14px',
    color: 'var(--text-primary)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  statusSection: {
    marginBottom: '24px',
  } as const,
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    marginBottom: '14px',
  } as const,
  statusGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '12px',
  } as const,
  statusItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
    alignItems: 'center',
    textAlign: 'center' as const,
  } as const,
  statusLabel: {
    fontSize: '11px',
    color: 'var(--text-muted)',
  } as const,
  timeSection: {
    marginBottom: '24px',
  } as const,
  timeGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '16px',
  } as const,
  timeLabel: {
    display: 'block',
    fontSize: '12px',
    color: 'var(--text-muted)',
    marginBottom: '4px',
  } as const,
  timeValue: {
    fontSize: '13px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-secondary)',
  } as const,
  errorSection: {
    marginTop: '8px',
  } as const,
  errorMessage: {
    margin: 0,
    padding: '14px',
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-red)',
    backgroundColor: 'var(--status-error-bg)',
    borderRadius: 'var(--radius-md)',
    overflow: 'auto',
    maxHeight: '150px',
    whiteSpace: 'pre-wrap' as const,
  } as const,
};

export default TaskList;