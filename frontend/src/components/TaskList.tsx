import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type {
  ExecutionTask,
  TaskStatus,
  AutomationTestCaseResponse,
  ExecutionAgent,
  DispatchCaseItem,
  ExecutionTaskCaseSummary,
  ExecutionAssertionItem,
} from '../types';

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
const TASK_TABLE_COLUMNS = 7;
type StatusAppearance = {
  bg: string;
  color: string;
  label: string;
  border?: string;
  glow?: string;
};

const formatJsonPreview = (value: Record<string, unknown> | undefined) => {
  if (!value || Object.keys(value).length === 0) {
    return '';
  }
  return JSON.stringify(value, null, 2);
};

const getAssertionStatusText = (status?: string) => {
  if (!status) {
    return '未上报';
  }
  return getStatusAppearance(status).label;
};

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
  const [expandedCaseKeys, setExpandedCaseKeys] = useState<string[]>([]);

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

  const handleDeleteTask = async (taskId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`确定要删除任务 ${taskId} 吗？`)) {
      return;
    }
    try {
      await api.deleteTask(taskId);
      fetchTasks();
    } catch (err) {
      console.error('Delete task error:', err);
      alert('删除任务失败');
    }
  };

  const toggleCaseDetails = (caseKey: string) => {
    setExpandedCaseKeys(prev => (
      prev.includes(caseKey)
        ? prev.filter(key => key !== caseKey)
        : [...prev, caseKey]
    ));
  };

  const renderTaskCases = (cases: ExecutionTaskCaseSummary[] | undefined) => {
    if (!cases || cases.length === 0) {
      return <div style={styles.caseSummaryEmpty}>暂无用例执行信息</div>;
    }

    return (
      <div style={styles.caseSummaryList}>
        {cases.map((caseItem) => {
          const caseKey = `${caseItem.task_id}-${caseItem.case_id}`;
          const caseStatusStyle = getStatusAppearance(caseItem.status);
          const dispatchStatusStyle = getStatusAppearance(caseItem.dispatch_status);
          const latestEventStyle = getStatusAppearance(caseItem.result_data?.status || caseItem.status);
          const assertions = caseItem.result_data?.assertions || [];
          const isExpanded = expandedCaseKeys.includes(caseKey);
          const resultDataPreview = formatJsonPreview(caseItem.result_data?.data);
          const resultErrorPreview = formatJsonPreview(caseItem.result_data?.error);
          const hasDetail =
            Boolean(caseItem.result_data?.event_type) ||
            Boolean(caseItem.result_data?.phase) ||
            assertions.length > 0 ||
            Boolean(caseItem.result_data?.error && Object.keys(caseItem.result_data.error).length > 0) ||
            Boolean(caseItem.result_data?.data && Object.keys(caseItem.result_data.data).length > 0);
          const progressText = typeof caseItem.progress_percent === 'number'
            ? `${Math.round(caseItem.progress_percent)}%`
            : '-';

          return (
            <div key={caseKey} style={styles.caseSummaryCard}>
              <div style={styles.caseSummaryHeader}>
                <div style={styles.caseSummaryTitleBlock}>
                  <span style={styles.caseSummaryTitle}>{caseItem.title || caseItem.case_id}</span>
                  <span style={styles.caseSummaryMeta}>
                    {caseItem.auto_case_id || caseItem.case_id}
                  </span>
                </div>
                <span
                  style={{
                    ...styles.caseStatusBadge,
                    backgroundColor: caseStatusStyle.bg,
                    color: caseStatusStyle.color,
                    border: caseStatusStyle.border,
                    boxShadow: caseStatusStyle.glow,
                  }}
                >
                  {caseStatusStyle.label}
                </span>
              </div>
              <div style={styles.caseSummaryMetrics}>
                <div style={styles.caseMetricPill}>
                  <span style={styles.caseMetricLabel}>进度</span>
                  <span style={styles.caseMetricValue}>{progressText}</span>
                </div>
                <div style={styles.caseMetricPill}>
                  <span style={styles.caseMetricLabel}>下发次数</span>
                  <span style={styles.caseMetricValue}>{caseItem.dispatch_attempts}</span>
                </div>
                <div style={styles.caseMetricPill}>
                  <span style={styles.caseMetricLabel}>事件数</span>
                  <span style={styles.caseMetricValue}>{caseItem.event_count}</span>
                </div>
                <div style={styles.caseMetricPill}>
                  <span style={styles.caseMetricLabel}>断言数</span>
                  <span style={styles.caseMetricValue}>{assertions.length}</span>
                </div>
              </div>
              <div style={styles.caseSummaryInfoRow}>
                <span
                  style={{
                    ...styles.inlineStatusBadge,
                    backgroundColor: dispatchStatusStyle.bg,
                    color: dispatchStatusStyle.color,
                    border: dispatchStatusStyle.border,
                    boxShadow: dispatchStatusStyle.glow,
                  }}
                >
                  下发 {dispatchStatusStyle.label}
                </span>
                {caseItem.last_event_at && (
                  <span style={styles.caseMetricItem}>
                    最近回报 {new Date(caseItem.last_event_at).toLocaleString('zh-CN')}
                  </span>
                )}
              </div>
              {caseItem.failure_message && (
                <div style={styles.caseFailureText}>{caseItem.failure_message}</div>
              )}
              {hasDetail && (
                <div style={styles.caseDetailSection}>
                  <button
                    type="button"
                    style={styles.caseDetailToggle}
                    onClick={() => toggleCaseDetails(caseKey)}
                  >
                    <span style={styles.caseDetailTitle}>当前执行细节</span>
                    <span style={styles.caseDetailToggleText}>{isExpanded ? '收起' : '展开'}</span>
                  </button>
                  {isExpanded && (
                    <>
                      <div style={styles.caseDetailGrid}>
                        <div style={styles.caseDetailBlock}>
                          <span style={styles.caseDetailBlockLabel}>开始时间</span>
                          <span style={styles.caseDetailBlockValue}>
                            {caseItem.started_at ? new Date(caseItem.started_at).toLocaleString('zh-CN') : '-'}
                          </span>
                        </div>
                        <div style={styles.caseDetailBlock}>
                          <span style={styles.caseDetailBlockLabel}>结束时间</span>
                          <span style={styles.caseDetailBlockValue}>
                            {caseItem.finished_at ? new Date(caseItem.finished_at).toLocaleString('zh-CN') : '-'}
                          </span>
                        </div>
                        <div style={styles.caseDetailBlock}>
                          <span style={styles.caseDetailBlockLabel}>最近事件ID</span>
                          <span style={styles.caseDetailBlockValueMono}>{caseItem.last_event_id || '-'}</span>
                        </div>
                        <div style={styles.caseDetailBlock}>
                          <span style={styles.caseDetailBlockLabel}>最近事件时间</span>
                          <span style={styles.caseDetailBlockValue}>
                            {caseItem.last_event_at ? new Date(caseItem.last_event_at).toLocaleString('zh-CN') : '-'}
                          </span>
                        </div>
                      </div>
                      <div style={styles.caseDetailMetaRow}>
                        {caseItem.result_data?.event_type && (
                          <span style={styles.caseDetailText}>
                            事件 {caseItem.result_data.event_type}
                          </span>
                        )}
                        {caseItem.result_data?.phase && (
                          <span style={styles.caseDetailText}>
                            阶段 {caseItem.result_data.phase}
                          </span>
                        )}
                        {caseItem.result_data?.status && (
                          <span
                            style={{
                              ...styles.inlineStatusBadge,
                              backgroundColor: latestEventStyle.bg,
                              color: latestEventStyle.color,
                              border: latestEventStyle.border,
                              boxShadow: latestEventStyle.glow,
                            }}
                          >
                            回报 {latestEventStyle.label}
                          </span>
                        )}
                      </div>

                      {assertions.length > 0 && (
                        <div style={styles.caseSectionGroup}>
                          <div style={styles.caseSectionTitle}>断言步骤</div>
                          <div style={styles.assertionList}>
                            {assertions.map((assertion: ExecutionAssertionItem, index) => {
                              const assertionStyle = getStatusAppearance(assertion.status || '');
                              const assertionMessage = typeof assertion.error?.message === 'string'
                                ? assertion.error.message
                                : '';
                              const assertionDataPreview = formatJsonPreview(assertion.data);
                              const assertionErrorPreview = formatJsonPreview(assertion.error);
                              return (
                                <div key={`${caseItem.case_id}-assert-${index}`} style={styles.assertionItem}>
                                  <div style={styles.assertionHeader}>
                                    <span style={styles.assertionName}>
                                      {assertion.seq ? `#${assertion.seq} ` : ''}{assertion.name || '未命名断言'}
                                    </span>
                                    <span
                                      style={{
                                        ...styles.inlineStatusBadge,
                                        backgroundColor: assertionStyle.bg,
                                        color: assertionStyle.color,
                                        border: assertionStyle.border,
                                      }}
                                    >
                                      {getAssertionStatusText(assertion.status)}
                                    </span>
                                  </div>
                                  {assertion.timestamp && (
                                    <div style={styles.assertionMeta}>
                                      {new Date(assertion.timestamp).toLocaleString('zh-CN')}
                                    </div>
                                  )}
                                  {assertionMessage && (
                                    <div style={styles.assertionError}>{assertionMessage}</div>
                                  )}
                                  {assertionDataPreview && (
                                    <pre style={styles.caseDetailCode}>{assertionDataPreview}</pre>
                                  )}
                                  {!assertionDataPreview && assertionErrorPreview && (
                                    <pre style={styles.caseDetailCode}>{assertionErrorPreview}</pre>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {resultDataPreview && (
                        <div style={styles.caseSectionGroup}>
                          <div style={styles.caseSectionTitle}>最近结果数据</div>
                          <pre style={styles.caseDetailCode}>{resultDataPreview}</pre>
                        </div>
                      )}

                      {!resultDataPreview && resultErrorPreview && (
                        <div style={styles.caseSectionGroup}>
                          <div style={styles.caseSectionTitle}>最近错误数据</div>
                          <pre style={styles.caseDetailCode}>{resultErrorPreview}</pre>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
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
              const s = getStatusAppearance(status);
              return (
                <span
                  key={status}
                  style={{
                    ...styles.statBadge,
                    backgroundColor: s.bg,
                    color: s.color,
                    border: s.border,
                    boxShadow: s.glow,
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
                <th style={styles.th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => {
                const statusStyle = getStatusAppearance(task.overall_status);
                const scheduleStyle = getStatusAppearance(task.schedule_type);
                return (
                  <>
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
                            border: scheduleStyle.border,
                          }}
                        >
                          {scheduleStyle.label}
                        </span>
                      </td>
                      <td style={styles.td}>
                        <span
                          style={{
                            ...styles.statusBadgeLarge,
                            backgroundColor: statusStyle.bg,
                            color: statusStyle.color,
                            border: statusStyle.border,
                            boxShadow: statusStyle.glow,
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
                      <td style={styles.td}>
                        <button
                          style={styles.deleteBtn}
                          className="delete-btn"
                          onClick={(e) => handleDeleteTask(task.task_id, e)}
                          title="删除任务"
                        >
                          🗑
                        </button>
                      </td>
                    </tr>
                    <tr style={styles.caseSummaryRow}>
                      <td style={styles.caseSummaryCell} colSpan={TASK_TABLE_COLUMNS}>
                        <div style={styles.caseSummaryWrap}>
                          <div style={styles.caseSummaryHeading}>
                            用例执行情况
                            <span style={styles.caseSummaryCount}>
                              {(task.cases || []).length}/{task.case_count}
                            </span>
                          </div>
                          {renderTaskCases(task.cases)}
                        </div>
                      </td>
                    </tr>
                  </>
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
        .delete-btn:hover { background-color: var(--status-error-bg) !important; border-color: var(--accent-red) !important; color: var(--accent-red) !important; }
      `}</style>
    </div>
  );
};

function getStatusStyleStyle(status: string) {
  const s = getStatusAppearance(status);
  return {
    backgroundColor: s.bg,
    color: s.color,
    border: s.border,
    boxShadow: s.glow,
  };
}

function getStatusAppearance(status: string): StatusAppearance {
  const normalizedStatus = (status || '').toUpperCase();
  const statusMap: Record<string, StatusAppearance> = {
    PENDING: {
      bg: 'rgba(250, 204, 21, 0.12)',
      color: '#facc15',
      label: '待处理',
      border: '1px solid rgba(250, 204, 21, 0.28)',
    },
    QUEUED: {
      bg: 'rgba(245, 158, 11, 0.14)',
      color: '#f59e0b',
      label: '排队中',
      border: '1px solid rgba(245, 158, 11, 0.28)',
    },
    READY: {
      bg: 'rgba(59, 130, 246, 0.12)',
      color: '#60a5fa',
      label: '就绪',
      border: '1px solid rgba(96, 165, 250, 0.24)',
    },
    RUNNING: {
      bg: 'rgba(59, 130, 246, 0.14)',
      color: '#38bdf8',
      label: '运行中',
      border: '1px solid rgba(56, 189, 248, 0.28)',
      glow: '0 0 0 1px rgba(56, 189, 248, 0.08) inset',
    },
    SUCCESS: {
      bg: 'rgba(34, 197, 94, 0.12)',
      color: '#22c55e',
      label: '成功',
      border: '1px solid rgba(34, 197, 94, 0.24)',
    },
    PASSED: {
      bg: 'rgba(34, 197, 94, 0.14)',
      color: '#22c55e',
      label: '已通过',
      border: '1px solid rgba(34, 197, 94, 0.28)',
      glow: '0 0 0 1px rgba(34, 197, 94, 0.08) inset',
    },
    FAILED: {
      bg: 'rgba(239, 68, 68, 0.14)',
      color: '#f87171',
      label: '失败',
      border: '1px solid rgba(248, 113, 113, 0.28)',
    },
    DISPATCH_FAILED: {
      bg: 'rgba(239, 68, 68, 0.14)',
      color: '#f87171',
      label: '下发失败',
      border: '1px solid rgba(248, 113, 113, 0.28)',
    },
    STOPPED: {
      bg: 'rgba(148, 163, 184, 0.16)',
      color: '#cbd5e1',
      label: '已停止',
      border: '1px solid rgba(148, 163, 184, 0.28)',
    },
    CANCELLED: {
      bg: 'rgba(100, 116, 139, 0.16)',
      color: '#94a3b8',
      label: '已取消',
      border: '1px solid rgba(148, 163, 184, 0.2)',
    },
    SCHEDULED: {
      bg: 'rgba(163, 113, 247, 0.15)',
      color: 'var(--accent-purple)',
      label: '定时',
      border: '1px solid rgba(163, 113, 247, 0.26)',
    },
    IMMEDIATE: {
      bg: 'rgba(57, 208, 214, 0.12)',
      color: 'var(--accent-cyan)',
      label: '立即',
      border: '1px solid rgba(57, 208, 214, 0.22)',
    },
    DISPATCHED: {
      bg: 'rgba(57, 208, 214, 0.15)',
      color: 'var(--accent-cyan)',
      label: '已下发',
      border: '1px solid rgba(57, 208, 214, 0.24)',
    },
    COMPLETED: {
      bg: 'rgba(34, 197, 94, 0.12)',
      color: '#22c55e',
      label: '已完成',
      border: '1px solid rgba(34, 197, 94, 0.24)',
    },
    CONSUMED: {
      bg: 'rgba(16, 185, 129, 0.12)',
      color: '#34d399',
      label: '已消费',
      border: '1px solid rgba(52, 211, 153, 0.24)',
    },
    NOT_CONSUMED: {
      bg: 'rgba(100, 116, 139, 0.16)',
      color: '#94a3b8',
      label: '未消费',
      border: '1px solid rgba(148, 163, 184, 0.2)',
    },
  };
  return statusMap[normalizedStatus] || {
    bg: 'rgba(100, 116, 139, 0.16)',
    color: 'var(--text-secondary)',
    label: status || '-',
    border: '1px solid rgba(148, 163, 184, 0.2)',
  };
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
    border: '1px solid transparent',
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
  caseSummaryRow: {
    borderBottom: '1px solid var(--border-muted)',
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
  } as const,
  td: {
    padding: '16px 20px',
    fontSize: '14px',
    color: 'var(--text-primary)',
  } as const,
  caseSummaryCell: {
    padding: '0 20px 18px',
  } as const,
  caseSummaryWrap: {
    borderRadius: '14px',
    border: '1px solid var(--border-muted)',
    backgroundColor: 'var(--bg-primary)',
    padding: '14px',
  } as const,
  caseSummaryHeading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '12px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    letterSpacing: '0.4px',
  } as const,
  caseSummaryCount: {
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-muted)',
  } as const,
  caseSummaryList: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '10px',
  } as const,
  caseSummaryCard: {
    padding: '12px',
    borderRadius: '12px',
    border: '1px solid var(--border-muted)',
    backgroundColor: 'var(--bg-secondary)',
  } as const,
  caseSummaryHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '10px',
    marginBottom: '8px',
  } as const,
  caseSummaryTitleBlock: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
    minWidth: 0,
  } as const,
  caseSummaryTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    lineHeight: 1.4,
  } as const,
  caseSummaryMeta: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  caseStatusBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    flexShrink: 0,
    padding: '4px 8px',
    borderRadius: '999px',
    fontSize: '11px',
    fontWeight: 600,
    border: '1px solid transparent',
  } as const,
  caseSummaryInfoRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '10px',
    fontSize: '11px',
    color: 'var(--text-secondary)',
  } as const,
  caseSummaryMetrics: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
    gap: '8px',
    marginBottom: '10px',
  } as const,
  caseMetricPill: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '3px',
    padding: '8px 10px',
    borderRadius: '10px',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid var(--border-muted)',
  } as const,
  caseMetricLabel: {
    fontSize: '10px',
    color: 'var(--text-muted)',
    letterSpacing: '0.2px',
  } as const,
  caseMetricValue: {
    fontSize: '12px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  inlineStatusBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '3px 8px',
    borderRadius: '999px',
    fontSize: '11px',
    fontWeight: 600,
    border: '1px solid transparent',
  } as const,
  caseMetricItem: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '3px 0',
  } as const,
  caseFailureText: {
    marginTop: '8px',
    fontSize: '11px',
    lineHeight: 1.5,
    color: 'var(--accent-red)',
  } as const,
  caseDetailSection: {
    marginTop: '10px',
    paddingTop: '10px',
    borderTop: '1px dashed var(--border-muted)',
  } as const,
  caseDetailToggle: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 0,
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    marginBottom: '8px',
  } as const,
  caseDetailTitle: {
    fontSize: '11px',
    fontWeight: 700,
    color: 'var(--text-secondary)',
    letterSpacing: '0.3px',
  } as const,
  caseDetailToggleText: {
    fontSize: '11px',
    color: 'var(--accent-cyan)',
    fontWeight: 600,
  } as const,
  caseDetailGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: '8px',
    marginBottom: '10px',
  } as const,
  caseDetailBlock: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '3px',
    padding: '8px 10px',
    borderRadius: '10px',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid var(--border-muted)',
  } as const,
  caseDetailBlockLabel: {
    fontSize: '10px',
    color: 'var(--text-muted)',
  } as const,
  caseDetailBlockValue: {
    fontSize: '11px',
    color: 'var(--text-primary)',
    lineHeight: 1.4,
  } as const,
  caseDetailBlockValueMono: {
    fontSize: '11px',
    color: 'var(--text-primary)',
    lineHeight: 1.4,
    fontFamily: "'JetBrains Mono', monospace",
    wordBreak: 'break-all' as const,
  } as const,
  caseDetailMetaRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
    marginBottom: '8px',
  } as const,
  caseSectionGroup: {
    marginTop: '10px',
  } as const,
  caseSectionTitle: {
    marginBottom: '6px',
    fontSize: '11px',
    color: 'var(--text-secondary)',
    fontWeight: 600,
  } as const,
  caseDetailText: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
  } as const,
  assertionList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  } as const,
  assertionItem: {
    padding: '8px 10px',
    borderRadius: '10px',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid var(--border-muted)',
  } as const,
  assertionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '8px',
  } as const,
  assertionName: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    lineHeight: 1.4,
  } as const,
  assertionError: {
    marginTop: '6px',
    fontSize: '11px',
    lineHeight: 1.5,
    color: 'var(--accent-red)',
  } as const,
  assertionMeta: {
    marginTop: '4px',
    fontSize: '10px',
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  caseDetailCode: {
    marginTop: '8px',
    marginBottom: 0,
    padding: '10px',
    borderRadius: '10px',
    backgroundColor: 'rgba(15, 23, 42, 0.55)',
    color: '#dbeafe',
    fontSize: '11px',
    lineHeight: 1.5,
    fontFamily: "'JetBrains Mono', monospace",
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
  } as const,
  caseSummaryEmpty: {
    padding: '12px',
    borderRadius: '10px',
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-muted)',
    fontSize: '12px',
    textAlign: 'center' as const,
  } as const,
  deleteBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    fontSize: '14px',
    backgroundColor: 'transparent',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    color: 'var(--text-muted)',
    transition: 'all var(--transition-fast)',
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
    border: '1px solid transparent',
  } as const,
  statusBadgeLarge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 14px',
    fontSize: '12px',
    fontWeight: 600,
    borderRadius: '14px',
    border: '1px solid transparent',
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
